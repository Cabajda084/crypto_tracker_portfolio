import sqlite3
from datetime import datetime
from typing import Optional

from dateutil.relativedelta import relativedelta

DB_PATH = "data/portfolio.db"


# =========================================================
# DB HELPERS
# =========================================================
def _get_connection():
    return sqlite3.connect(DB_PATH)


def _column_exists(cur, table_name: str, column_name: str) -> bool:
    cur.execute(f"PRAGMA table_info({table_name})")
    columns = cur.fetchall()
    return any(col[1] == column_name for col in columns)


def _ensure_column(cur, table_name: str, column_name: str, column_type_sql: str):
    if not _column_exists(cur, table_name, column_name):
        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type_sql}")


# =========================================================
# INIT TABLES
# =========================================================
def init_investown_tables():
    conn = _get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS investown_tracker (
        project_id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name TEXT,
        invested_amount REAL,
        investment_date TEXT,
        first_payout_date TEXT,
        duration_months INTEGER,
        expected_yield_pa REAL,
        status TEXT DEFAULT 'active',
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS investown_kalendar (
        schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        installment_no INTEGER,
        due_date TEXT,
        payment_type TEXT,
        interest_amount REAL,
        principal_amount REAL,
        total_amount REAL,
        status TEXT DEFAULT 'planned',
        paid_date TEXT,
        FOREIGN KEY(project_id) REFERENCES investown_tracker(project_id)
    )
    """)

    # bezpečná aditivní migrace
    _ensure_column(cur, "investown_tracker", "paid_through_date", "TEXT")

    conn.commit()
    conn.close()


# =========================================================
# CALC HELPERS
# =========================================================
def _safe_days_between(start_iso: str, end_iso: str) -> int:
    """
    Počet dnů mezi investicí a první výplatou.
    Minimálně 1 den, aby první splátka nebyla nulová.
    """
    start_dt = datetime.fromisoformat(start_iso).date()
    end_dt = datetime.fromisoformat(end_iso).date()
    diff = (end_dt - start_dt).days
    return max(diff, 1)


def _generate_schedule(
    cur,
    project_id: int,
    invested_amount: float,
    investment_date: str,
    first_payout_date: str,
    duration_months: int,
    expected_yield_pa: float,
):
    """
    Investown model:
    - 1. splátka = poměrný úrok dle dnů mezi investment_date a first_payout_date
    - 2..(n-1) = plný měsíční úrok
    - poslední splátka = plný měsíční úrok + jistina
    """
    first_date = datetime.fromisoformat(first_payout_date)
    first_days = _safe_days_between(investment_date, first_payout_date)

    annual_interest_amount = invested_amount * (expected_yield_pa / 100.0)
    monthly_interest = annual_interest_amount / 12.0
    daily_interest = annual_interest_amount / 365.0

    for i in range(duration_months):
        due_date = first_date + relativedelta(months=i)

        if i == 0:
            interest = daily_interest * first_days
        else:
            interest = monthly_interest

        principal = 0.0
        payment_type = "interest"

        if i == duration_months - 1:
            principal = invested_amount
            payment_type = "interest_principal"

        total = float(interest + principal)

        cur.execute("""
        INSERT INTO investown_kalendar (
            project_id,
            installment_no,
            due_date,
            payment_type,
            interest_amount,
            principal_amount,
            total_amount,
            status,
            paid_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project_id,
            i + 1,
            due_date.date().isoformat(),
            payment_type,
            float(interest),
            float(principal),
            total,
            "planned",
            None,
        ))


def _delete_project_schedule(cur, project_id: int):
    cur.execute("DELETE FROM investown_kalendar WHERE project_id = ?", (project_id,))


# =========================================================
# CRUD PROJECTS
# =========================================================
def add_investown_project(
    project_name: str,
    invested_amount: float,
    investment_date: str,
    first_payout_date: str,
    duration_months: int,
    expected_yield_pa: float,
    paid_through_date: Optional[str] = None,
    status: str = "active",
):
    conn = _get_connection()
    cur = conn.cursor()

    now = datetime.now().isoformat()

    cur.execute("""
    INSERT INTO investown_tracker (
        project_name,
        invested_amount,
        investment_date,
        first_payout_date,
        duration_months,
        expected_yield_pa,
        status,
        created_at,
        paid_through_date
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        project_name,
        float(invested_amount),
        investment_date,
        first_payout_date,
        int(duration_months),
        float(expected_yield_pa),
        status,
        now,
        paid_through_date,
    ))

    project_id = cur.lastrowid

    _generate_schedule(
        cur=cur,
        project_id=project_id,
        invested_amount=float(invested_amount),
        investment_date=investment_date,
        first_payout_date=first_payout_date,
        duration_months=int(duration_months),
        expected_yield_pa=float(expected_yield_pa),
    )

    conn.commit()
    conn.close()


def update_investown_project(
    project_id: int,
    project_name: str,
    invested_amount: float,
    investment_date: str,
    first_payout_date: str,
    duration_months: int,
    expected_yield_pa: float,
    status: str = "active",
    paid_through_date: Optional[str] = None,
):
    """
    Bezpečný update:
    - aktualizuje projekt
    - znovu přegeneruje splátkový kalendář podle nových parametrů
    """
    conn = _get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE investown_tracker
        SET
            project_name = ?,
            invested_amount = ?,
            investment_date = ?,
            first_payout_date = ?,
            duration_months = ?,
            expected_yield_pa = ?,
            status = ?,
            paid_through_date = ?
        WHERE project_id = ?
    """, (
        project_name,
        float(invested_amount),
        investment_date,
        first_payout_date,
        int(duration_months),
        float(expected_yield_pa),
        status,
        paid_through_date,
        int(project_id),
    ))

    _delete_project_schedule(cur, int(project_id))

    _generate_schedule(
        cur=cur,
        project_id=int(project_id),
        invested_amount=float(invested_amount),
        investment_date=investment_date,
        first_payout_date=first_payout_date,
        duration_months=int(duration_months),
        expected_yield_pa=float(expected_yield_pa),
    )

    conn.commit()
    conn.close()


def update_investown_paid_through_date(project_id: int, paid_through_date: Optional[str]):
    conn = _get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE investown_tracker
        SET paid_through_date = ?
        WHERE project_id = ?
    """, (paid_through_date, int(project_id)))

    conn.commit()
    conn.close()


def delete_investown_project(project_id: int):
    conn = _get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM investown_kalendar WHERE project_id = ?", (int(project_id),))
    cur.execute("DELETE FROM investown_tracker WHERE project_id = ?", (int(project_id),))

    conn.commit()
    conn.close()


# =========================================================
# GETTERS
# =========================================================
def get_investown_projects():
    conn = _get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            project_id,
            project_name,
            invested_amount,
            investment_date,
            first_payout_date,
            duration_months,
            expected_yield_pa,
            status,
            created_at,
            paid_through_date
        FROM investown_tracker
        ORDER BY project_id DESC
    """)
    rows = cur.fetchall()

    conn.close()
    return rows


def get_investown_project(project_id: int):
    conn = _get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            project_id,
            project_name,
            invested_amount,
            investment_date,
            first_payout_date,
            duration_months,
            expected_yield_pa,
            status,
            created_at,
            paid_through_date
        FROM investown_tracker
        WHERE project_id = ?
    """, (int(project_id),))
    row = cur.fetchone()

    conn.close()
    return row


def get_investown_schedule(project_id: int):
    conn = _get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            schedule_id,
            project_id,
            installment_no,
            due_date,
            payment_type,
            interest_amount,
            principal_amount,
            total_amount,
            status,
            paid_date
        FROM investown_kalendar
        WHERE project_id = ?
        ORDER BY installment_no
    """, (int(project_id),))

    rows = cur.fetchall()
    conn.close()
    return rows


def get_investown_summary():
    """
    Compatibility summary.
    Hlavní výpočty si dělá tracker sám.
    """
    conn = _get_connection()
    cur = conn.cursor()

    cur.execute("SELECT SUM(invested_amount) FROM investown_tracker")
    invested = cur.fetchone()[0] or 0.0

    cur.execute("""
        SELECT SUM(total_amount)
        FROM investown_kalendar
        WHERE status = 'paid'
    """)
    paid = cur.fetchone()[0] or 0.0

    conn.close()

    return {
        "invested": float(invested),
        "paid_out": float(paid),
        "profit": float(paid) - float(invested),
    }