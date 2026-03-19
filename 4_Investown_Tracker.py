import streamlit as st
import pandas as pd
from datetime import date, datetime

from investown_service import (
    init_investown_tables,
    add_investown_project,
    get_investown_projects,
    get_investown_schedule,
    get_investown_summary,
)


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(page_title="Investown Tracker", page_icon="🏠", layout="wide")


# =========================================================
# HELPERS
# =========================================================

def fmt_czk(value) -> str:
    try:
        return f"{float(value):,.2f} Kč".replace(",", " ")
    except Exception:
        return "0.00 Kč"


def fmt_pct(value) -> str:
    try:
        return f"{float(value):.2f} %"
    except Exception:
        return "0.00 %"


def parse_project_row(row):
    """
    Compatible with current investown_service.py tuple order:
    0 project_id
    1 project_name
    2 invested_amount
    3 investment_date
    4 first_payout_date
    5 duration_months
    6 expected_yield_pa
    7 status
    8 created_at
    """
    return {
        "project_id": row[0],
        "project_name": row[1],
        "invested_amount": float(row[2] or 0),
        "investment_date": row[3],
        "first_payout_date": row[4],
        "duration_months": int(row[5] or 0),
        "expected_yield_pa": float(row[6] or 0),
        "status": row[7] or "active",
        "created_at": row[8] if len(row) > 8 else None,
    }


def parse_schedule_row(row):
    """
    Compatible with current investown_service.py tuple order:
    0 schedule_id
    1 project_id
    2 installment_no
    3 due_date
    4 payment_type
    5 interest_amount
    6 principal_amount
    7 total_amount
    8 status
    9 paid_date
    """
    return {
        "schedule_id": row[0],
        "project_id": row[1],
        "installment_no": int(row[2] or 0),
        "due_date": row[3],
        "payment_type": row[4] or "interest",
        "interest_amount": float(row[5] or 0),
        "principal_amount": float(row[6] or 0),
        "total_amount": float(row[7] or 0),
        "status": row[8] or "planned",
        "paid_date": row[9],
    }


def load_projects_df() -> pd.DataFrame:
    rows = get_investown_projects()
    projects = [parse_project_row(r) for r in rows]
    if not projects:
        return pd.DataFrame(
            columns=[
                "project_id",
                "project_name",
                "invested_amount",
                "investment_date",
                "first_payout_date",
                "duration_months",
                "expected_yield_pa",
                "status",
                "created_at",
            ]
        )
    return pd.DataFrame(projects)


def load_schedule_df(project_id: int) -> pd.DataFrame:
    rows = get_investown_schedule(project_id)
    schedule = [parse_schedule_row(r) for r in rows]
    if not schedule:
        return pd.DataFrame(
            columns=[
                "schedule_id",
                "project_id",
                "installment_no",
                "due_date",
                "payment_type",
                "interest_amount",
                "principal_amount",
                "total_amount",
                "status",
                "paid_date",
            ]
        )
    df = pd.DataFrame(schedule)
    df["due_date_dt"] = pd.to_datetime(df["due_date"], errors="coerce")
    return df.sort_values(["installment_no", "due_date_dt"], ascending=[True, True]).reset_index(drop=True)


def get_project_metrics(project_row: pd.Series) -> dict:
    project_id = int(project_row["project_id"])
    schedule_df = load_schedule_df(project_id)

    invested_amount = float(project_row["invested_amount"])
    expected_yield_pa = float(project_row["expected_yield_pa"])
    duration_months = int(project_row["duration_months"])

    monthly_interest = invested_amount * (expected_yield_pa / 100) / 12 if invested_amount > 0 else 0.0
    total_expected_interest = monthly_interest * duration_months

    if schedule_df.empty:
        paid_total = 0.0
        paid_interest = 0.0
        paid_principal = 0.0
        next_payout_date = None
        next_payout_amount = 0.0
        remaining_planned = 0.0
        completed_pct = 0.0
    else:
        paid_df = schedule_df[schedule_df["status"] == "paid"].copy()
        planned_df = schedule_df[schedule_df["status"] != "paid"].copy()

        paid_total = float(paid_df["total_amount"].sum()) if not paid_df.empty else 0.0
        paid_interest = float(paid_df["interest_amount"].sum()) if not paid_df.empty else 0.0
        paid_principal = float(paid_df["principal_amount"].sum()) if not paid_df.empty else 0.0
        remaining_planned = float(planned_df["total_amount"].sum()) if not planned_df.empty else 0.0

        if not planned_df.empty:
            next_row = planned_df.sort_values("due_date_dt", ascending=True).iloc[0]
            next_payout_date = next_row["due_date"]
            next_payout_amount = float(next_row["total_amount"] or 0)
        else:
            next_payout_date = None
            next_payout_amount = 0.0

        total_schedule = float(schedule_df["total_amount"].sum()) if not schedule_df.empty else 0.0
        completed_pct = (paid_total / total_schedule * 100) if total_schedule > 0 else 0.0

    return {
        "project_id": project_id,
        "project_name": project_row["project_name"],
        "invested_amount": invested_amount,
        "expected_yield_pa": expected_yield_pa,
        "duration_months": duration_months,
        "monthly_interest": monthly_interest,
        "total_expected_interest": total_expected_interest,
        "paid_total": paid_total,
        "paid_interest": paid_interest,
        "paid_principal": paid_principal,
        "remaining_planned": remaining_planned,
        "next_payout_date": next_payout_date,
        "next_payout_amount": next_payout_amount,
        "completed_pct": completed_pct,
        "status": project_row["status"],
    }


def build_overall_metrics(projects_df: pd.DataFrame) -> dict:
    if projects_df.empty:
        return {
            "portfolio_value": 0.0,
            "invested_total": 0.0,
            "paid_out_total": 0.0,
            "projects_count": 0,
            "active_count": 0,
            "avg_yield_pa": 0.0,
            "next_payout_date": None,
            "next_payout_amount": 0.0,
        }

    metrics = [get_project_metrics(row) for _, row in projects_df.iterrows()]

    invested_total = sum(m["invested_amount"] for m in metrics)
    paid_out_total = sum(m["paid_total"] for m in metrics)
    active_count = sum(1 for m in metrics if str(m["status"]).lower() == "active")

    avg_yield_pa = (
        sum(m["expected_yield_pa"] * m["invested_amount"] for m in metrics) / invested_total
        if invested_total > 0 else 0.0
    )

    # konzervativní portfolio value pro první verzi:
    # vložená jistina aktivních projektů
    portfolio_value = invested_total

    next_candidates = [
        (m["next_payout_date"], m["next_payout_amount"])
        for m in metrics
        if m["next_payout_date"]
    ]
    next_candidates_sorted = sorted(next_candidates, key=lambda x: x[0]) if next_candidates else []

    next_payout_date = next_candidates_sorted[0][0] if next_candidates_sorted else None
    next_payout_amount = next_candidates_sorted[0][1] if next_candidates_sorted else 0.0

    return {
        "portfolio_value": portfolio_value,
        "invested_total": invested_total,
        "paid_out_total": paid_out_total,
        "projects_count": len(metrics),
        "active_count": active_count,
        "avg_yield_pa": avg_yield_pa,
        "next_payout_date": next_payout_date,
        "next_payout_amount": next_payout_amount,
    }


def schedule_display_df(schedule_df: pd.DataFrame) -> pd.DataFrame:
    if schedule_df.empty:
        return schedule_df

    out = schedule_df.copy()
    type_map = {
        "interest": "Úroky",
        "interest_principal": "Úroky + jistina",
    }
    status_map = {
        "planned": "Plánovaná",
        "paid": "Vyplacená",
        "late": "Po splatnosti",
    }

    out["Typ splátky"] = out["payment_type"].map(type_map).fillna(out["payment_type"])
    out["Stav"] = out["status"].map(status_map).fillna(out["status"])
    out["Číslo"] = out["installment_no"]
    out["Datum splátky"] = out["due_date"]
    out["Úrok"] = out["interest_amount"].round(2)
    out["Jistina"] = out["principal_amount"].round(2)
    out["Celkem"] = out["total_amount"].round(2)
    out["Datum vyplacení"] = out["paid_date"]

    return out[["Číslo", "Datum splátky", "Typ splátky", "Úrok", "Jistina", "Celkem", "Stav", "Datum vyplacení"]]


# =========================================================
# INIT
# =========================================================

init_investown_tables()

st.title("🏠 Investown Tracker")
st.caption("Samostatný tracker pro Investown projekty. Stávající části appky zůstávají beze změny.")


# =========================================================
# LOAD DATA
# =========================================================

projects_df = load_projects_df()
overall = build_overall_metrics(projects_df)

# service summary necháváme k dispozici do budoucna, ale UI nyní stavíme na bezpečnějších výpočtech
_ = get_investown_summary()


# =========================================================
# TOP SUMMARY
# =========================================================

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Hodnota portfolia", fmt_czk(overall["portfolio_value"]))
with c2:
    st.metric("Celkem vloženo", fmt_czk(overall["invested_total"]))
with c3:
    st.metric("Vyplaceno", fmt_czk(overall["paid_out_total"]))
with c4:
    st.metric("Průměrný výnos p.a.", fmt_pct(overall["avg_yield_pa"]))

c5, c6, c7 = st.columns(3)
with c5:
    st.metric("Počet investic", overall["projects_count"])
with c6:
    st.metric("Aktivní projekty", overall["active_count"])
with c7:
    next_text = (
        f"{overall['next_payout_date']} · {fmt_czk(overall['next_payout_amount'])}"
        if overall["next_payout_date"] else "Žádná plánovaná splátka"
    )
    st.metric("Další výplata", next_text)

st.divider()


# =========================================================
# ADD PROJECT FORM
# =========================================================

st.subheader("Přidat Investown projekt")

with st.form("investown_add_project", clear_on_submit=True):
    a1, a2 = st.columns(2)

    with a1:
        project_name = st.text_input("Název projektu")
        invested_amount = st.number_input("Moje investice (Kč)", min_value=0.0, value=50000.0, step=1000.0)
        investment_date = st.date_input("Datum investice", value=date.today())

    with a2:
        first_payout_date = st.date_input("Datum první výplaty", value=date.today())
        duration_months = st.number_input("Délka investice (měsíce)", min_value=1, value=30, step=1)
        expected_yield_pa = st.number_input("Očekávaný výnos p.a. (%)", min_value=0.0, value=8.7, step=0.1)

    submit_project = st.form_submit_button("Uložit projekt a vygenerovat kalendář", use_container_width=True)

if submit_project:
    if not project_name.strip():
        st.error("Vyplň prosím název projektu.")
    else:
        try:
            add_investown_project(
                project_name=project_name.strip(),
                invested_amount=float(invested_amount),
                investment_date=investment_date.isoformat(),
                first_payout_date=first_payout_date.isoformat(),
                duration_months=int(duration_months),
                expected_yield_pa=float(expected_yield_pa),
            )
            st.success("Projekt uložen a splátkový kalendář vygenerován.")
            st.rerun()
        except Exception as e:
            st.error(f"Uložení projektu selhalo: {e}")

st.divider()


# =========================================================
# PROJECT LIST
# =========================================================

st.subheader("Moje investice")

if projects_df.empty:
    st.info("Zatím tu nejsou žádné Investown projekty.")
else:
    # řazení od nejnovějších
    projects_df["investment_date_dt"] = pd.to_datetime(projects_df["investment_date"], errors="coerce")
    projects_df = projects_df.sort_values("investment_date_dt", ascending=False).reset_index(drop=True)

    for _, row in projects_df.iterrows():
        metrics = get_project_metrics(row)
        schedule_df = load_schedule_df(int(row["project_id"]))

        with st.container(border=True):
            h1, h2 = st.columns([2, 1])

            with h1:
                st.markdown(f"### {metrics['project_name']}")
                st.caption(
                    f"Výnos p.a.: {fmt_pct(metrics['expected_yield_pa'])} · "
                    f"Délka: {metrics['duration_months']} měsíců · "
                    f"Stav: {metrics['status']}"
                )

            with h2:
                st.markdown(f"### {fmt_czk(metrics['invested_amount'])}")
                if metrics["next_payout_date"]:
                    st.caption(f"Další výplata: {metrics['next_payout_date']}")
                else:
                    st.caption("Bez další plánované výplaty")

            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Moje investice", fmt_czk(metrics["invested_amount"]))
            with m2:
                st.metric("Měsíční úrok", fmt_czk(metrics["monthly_interest"]))
            with m3:
                st.metric("Vyplaceno", fmt_czk(metrics["paid_total"]))
            with m4:
                st.metric("Další splátka", fmt_czk(metrics["next_payout_amount"]))

            st.progress(int(max(0, min(metrics["completed_pct"], 100))))
            st.caption(f"Průběh vyplácení: {metrics['completed_pct']:.1f} %")

            with st.expander("Detail projektu a splátkový kalendář"):
                d1, d2 = st.columns(2)
                with d1:
                    st.write(f"**Datum investice:** {row['investment_date']}")
                    st.write(f"**První výplata:** {row['first_payout_date']}")
                    st.write(f"**Očekávaný úrok celkem:** {fmt_czk(metrics['total_expected_interest'])}")
                with d2:
                    st.write(f"**Vyplacený úrok:** {fmt_czk(metrics['paid_interest'])}")
                    st.write(f"**Vyplacená jistina:** {fmt_czk(metrics['paid_principal'])}")
                    st.write(f"**Zbývá vyplatit:** {fmt_czk(metrics['remaining_planned'])}")

                st.markdown("#### Splátkový kalendář")
                if schedule_df.empty:
                    st.info("Pro tento projekt zatím není vygenerovaný žádný kalendář.")
                else:
                    display_df = schedule_display_df(schedule_df)
                    st.dataframe(display_df, use_container_width=True, hide_index=True)