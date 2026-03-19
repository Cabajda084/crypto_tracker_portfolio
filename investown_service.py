import sqlite3
from datetime import datetime
from dateutil.relativedelta import relativedelta

DB_PATH = "data/portfolio.db"


# =========================================================
# INIT TABLES (SAFE - CREATE ONLY)
# =========================================================
def init_investown_tables():
    conn = sqlite3.connect(DB_PATH)
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

    conn.commit()
    conn.close()


# =========================================================
# ADD PROJECT + AUTO GENERATE SCHEDULE
# =========================================================
def add_investown_project(
    project_name: str,
    invested_amount: float,
    investment_date: str,
    first_payout_date: str,
    duration_months: int,
    expected_yield_pa: float
):
    conn = sqlite3.connect(DB_PATH)
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
        created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        project_name,
        invested_amount,
        investment_date,
        first_payout_date,
        duration_months,
        expected_yield_pa,
        now
    ))

    project_id = cur.lastrowid

    # generate schedule
    _generate_schedule(
        cur,
        project_id,
        invested_amount,
        first_payout_date,
        duration_months,
        expected_yield_pa
    )

    conn.commit()
    conn.close()


# =========================================================
# SCHEDULE GENERATOR
# =========================================================
def _generate_schedule(
    cur,
    project_id,
    invested_amount,
    first_payout_date,
    duration_months,
    expected_yield_pa
):
    first_date = datetime.fromisoformat(first_payout_date)

    monthly_interest = invested_amount * (expected_yield_pa / 100) / 12

    for i in range(duration_months):
        due_date = first_date + relativedelta(months=i)

        interest = monthly_interest
        principal = 0.0

        # LAST PAYMENT → ADD PRINCIPAL
        if i == duration_months - 1:
            principal = invested_amount

        total = interest + principal

        cur.execute("""
        INSERT INTO investown_kalendar (
            project_id,
            installment_no,
            due_date,
            payment_type,
            interest_amount,
            principal_amount,
            total_amount
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            project_id,
            i + 1,
            due_date.date().isoformat(),
            "interest_principal" if principal > 0 else "interest",
            interest,
            principal,
            total
        ))


# =========================================================
# GET DATA
# =========================================================
def get_investown_projects():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT * FROM investown_tracker")
    rows = cur.fetchall()

    conn.close()
    return rows


def get_investown_schedule(project_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM investown_kalendar
        WHERE project_id = ?
        ORDER BY installment_no
    """, (project_id,))

    rows = cur.fetchall()
    conn.close()
    return rows


# =========================================================
# SUMMARY
# =========================================================
def get_investown_summary():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            SUM(invested_amount)
        FROM investown_tracker
    """)
    invested = cur.fetchone()[0] or 0

    cur.execute("""
        SELECT 
            SUM(total_amount)
        FROM investown_kalendar
        WHERE status = 'paid'
    """)
    paid = cur.fetchone()[0] or 0

    conn.close()

    return {
        "invested": invested,
        "paid_out": paid,
        "profit": paid - invested
    }