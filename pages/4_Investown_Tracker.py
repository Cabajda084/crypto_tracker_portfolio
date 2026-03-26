import streamlit as st
import pandas as pd
from datetime import date

from investown_service import (
    init_investown_tables,
    add_investown_project,
    update_investown_project,
    update_investown_paid_through_date,
    delete_investown_project,
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


def month_label(month_value: str) -> str:
    dt = pd.to_datetime(month_value + "-01", errors="coerce")
    if pd.isna(dt):
        return month_value

    month_names = {
        1: "leden",
        2: "únor",
        3: "březen",
        4: "duben",
        5: "květen",
        6: "červen",
        7: "červenec",
        8: "srpen",
        9: "září",
        10: "říjen",
        11: "listopad",
        12: "prosinec",
    }
    return f"{month_names.get(dt.month, str(dt.month))} {dt.year}"


def parse_project_row(row):
    return {
        "project_id": int(row[0]),
        "project_name": row[1],
        "invested_amount": float(row[2] or 0),
        "investment_date": row[3],
        "first_payout_date": row[4],
        "duration_months": int(row[5] or 0),
        "expected_yield_pa": float(row[6] or 0),
        "status": row[7] or "active",
        "created_at": row[8] if len(row) > 8 else None,
        "paid_through_date": row[9] if len(row) > 9 else None,
    }


def parse_schedule_row(row):
    return {
        "schedule_id": int(row[0]),
        "project_id": int(row[1]),
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
                "paid_through_date",
            ]
        )

    df = pd.DataFrame(projects)
    df["investment_date_dt"] = pd.to_datetime(df["investment_date"], errors="coerce")
    df["first_payout_date_dt"] = pd.to_datetime(df["first_payout_date"], errors="coerce")
    df["paid_through_date_dt"] = pd.to_datetime(df["paid_through_date"], errors="coerce")
    return df


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
                "due_date_dt",
            ]
        )

    df = pd.DataFrame(schedule)
    df["due_date_dt"] = pd.to_datetime(df["due_date"], errors="coerce")
    return df.sort_values(["due_date_dt", "installment_no"], ascending=[True, True]).reset_index(drop=True)


def enrich_schedule_df(schedule_df: pd.DataFrame, paid_through_date) -> pd.DataFrame:
    if schedule_df.empty:
        return schedule_df.copy()

    out = schedule_df.copy()
    today = pd.Timestamp.today().normalize()

    if paid_through_date:
        paid_dt = pd.to_datetime(paid_through_date, errors="coerce")
        if pd.isna(paid_dt):
            paid_dt = today
    else:
        paid_dt = today

    out["is_estimated_paid"] = out["due_date_dt"] <= paid_dt

    def estimate_status(row):
        if row["is_estimated_paid"]:
            return "Vyplaceno"
        if pd.notna(row["due_date_dt"]) and row["due_date_dt"] < today:
            return "Po termínu"
        return "Plánováno"

    out["estimated_status"] = out.apply(estimate_status, axis=1)
    out["month"] = out["due_date_dt"].dt.to_period("M").astype(str)

    return out


def get_project_metrics(project_row: pd.Series) -> dict:
    project_id = int(project_row["project_id"])
    schedule_df = enrich_schedule_df(
        load_schedule_df(project_id),
        project_row.get("paid_through_date"),
    )

    invested_amount = float(project_row["invested_amount"] or 0)
    expected_yield_pa = float(project_row["expected_yield_pa"] or 0)
    duration_months = int(project_row["duration_months"] or 0)

    if schedule_df.empty:
        paid_interest = 0.0
        paid_principal = 0.0
        remaining_interest = 0.0
        remaining_principal = 0.0
        next_payout_date = None
        next_payout_amount = 0.0
        completed_pct = 0.0
        total_interest = 0.0
        monthly_interest_regular = 0.0
        first_interest = 0.0
        final_principal = 0.0
    else:
        paid_df = schedule_df[schedule_df["is_estimated_paid"]].copy()
        future_df = schedule_df[~schedule_df["is_estimated_paid"]].copy()

        paid_interest = float(paid_df["interest_amount"].sum()) if not paid_df.empty else 0.0
        paid_principal = float(paid_df["principal_amount"].sum()) if not paid_df.empty else 0.0

        remaining_interest = float(future_df["interest_amount"].sum()) if not future_df.empty else 0.0
        remaining_principal = float(future_df["principal_amount"].sum()) if not future_df.empty else 0.0

        total_interest = float(schedule_df["interest_amount"].sum()) if not schedule_df.empty else 0.0

        future_sorted = future_df.sort_values("due_date_dt", ascending=True)
        if not future_sorted.empty:
            next_row = future_sorted.iloc[0]
            next_payout_date = next_row["due_date"]
            next_payout_amount = float(next_row["total_amount"] or 0)
        else:
            next_payout_date = None
            next_payout_amount = 0.0

        completed_pct = (paid_interest / total_interest * 100) if total_interest > 0 else 0.0

        first_row = schedule_df.sort_values("installment_no").iloc[0]
        last_row = schedule_df.sort_values("installment_no").iloc[-1]

        first_interest = float(first_row["interest_amount"] or 0)
        final_principal = float(last_row["principal_amount"] or 0)

        regular_interest_rows = schedule_df[
            (schedule_df["installment_no"] > 1) &
            (schedule_df["payment_type"] == "interest")
        ]
        if not regular_interest_rows.empty:
            monthly_interest_regular = float(regular_interest_rows.iloc[0]["interest_amount"] or 0)
        else:
            monthly_interest_regular = float(last_row["interest_amount"] or 0)

    principal_outstanding = max(invested_amount - paid_principal, 0.0)

    return {
        "project_id": project_id,
        "project_name": project_row["project_name"],
        "invested_amount": invested_amount,
        "expected_yield_pa": expected_yield_pa,
        "duration_months": duration_months,
        "paid_interest": paid_interest,
        "paid_principal": paid_principal,
        "remaining_interest": remaining_interest,
        "remaining_principal": remaining_principal,
        "next_payout_date": next_payout_date,
        "next_payout_amount": next_payout_amount,
        "completed_pct": completed_pct,
        "status": project_row["status"],
        "paid_through_date": project_row.get("paid_through_date"),
        "total_expected_interest": total_interest,
        "monthly_interest_regular": monthly_interest_regular,
        "first_interest": first_interest,
        "final_principal": final_principal,
        "principal_outstanding": principal_outstanding,
    }


def build_monthly_cashflow_details(projects_df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    if projects_df.empty:
        return pd.DataFrame(
            columns=[
                "month",
                "project_id",
                "project_name",
                "due_date",
                "due_date_dt",
                "payment_type",
                "interest_amount",
                "principal_amount",
                "total_amount",
                "estimated_status",
                "is_estimated_paid",
                "installment_no",
            ]
        )

    for _, project_row in projects_df.iterrows():
        schedule_df = enrich_schedule_df(
            load_schedule_df(int(project_row["project_id"])),
            project_row.get("paid_through_date"),
        )

        if schedule_df.empty:
            continue

        for _, row in schedule_df.iterrows():
            rows.append({
                "month": row["month"],
                "project_id": int(project_row["project_id"]),
                "project_name": project_row["project_name"],
                "due_date": row["due_date"],
                "due_date_dt": row["due_date_dt"],
                "payment_type": row["payment_type"],
                "interest_amount": float(row["interest_amount"] or 0),
                "principal_amount": float(row["principal_amount"] or 0),
                "total_amount": float(row["total_amount"] or 0),
                "estimated_status": row["estimated_status"],
                "is_estimated_paid": bool(row["is_estimated_paid"]),
                "installment_no": int(row["installment_no"] or 0),
            })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    return df.sort_values(
        ["due_date_dt", "project_name", "installment_no"],
        ascending=[True, True, True]
    ).reset_index(drop=True)


def build_monthly_cashflow_summary(monthly_details_df: pd.DataFrame) -> pd.DataFrame:
    if monthly_details_df.empty:
        return pd.DataFrame(
            columns=[
                "month",
                "paid_interest_total",
                "expected_interest_total",
                "total_interest",
                "month_dt",
            ]
        )

    paid_df = (
        monthly_details_df[monthly_details_df["is_estimated_paid"]]
        .groupby("month", as_index=False)["interest_amount"]
        .sum()
        .rename(columns={"interest_amount": "paid_interest_total"})
    )

    expected_df = (
        monthly_details_df[~monthly_details_df["is_estimated_paid"]]
        .groupby("month", as_index=False)["interest_amount"]
        .sum()
        .rename(columns={"interest_amount": "expected_interest_total"})
    )

    merged = pd.merge(paid_df, expected_df, on="month", how="outer").fillna(0.0)
    merged["total_interest"] = merged["paid_interest_total"] + merged["expected_interest_total"]
    merged["month_dt"] = pd.to_datetime(merged["month"] + "-01", errors="coerce")
    merged = merged.sort_values("month_dt", ascending=True).reset_index(drop=True)

    return merged


def build_overall_metrics(projects_df: pd.DataFrame, monthly_df: pd.DataFrame) -> dict:
    if projects_df.empty:
        return {
            "portfolio_value": 0.0,
            "invested_total": 0.0,
            "paid_out_total": 0.0,
            "projects_count": 0,
            "active_count": 0,
            "avg_yield_pa": 0.0,
            "this_month_expected": 0.0,
            "next_month_expected": 0.0,
            "remaining_expected": 0.0,
            "estimated_profit_total": 0.0,
        }

    metrics = [get_project_metrics(row) for _, row in projects_df.iterrows()]

    invested_total = sum(m["invested_amount"] for m in metrics)
    portfolio_value = invested_total
    paid_out_total = sum(m["paid_interest"] for m in metrics)
    remaining_expected = sum(m["remaining_interest"] for m in metrics)
    estimated_profit_total = sum(m["total_expected_interest"] for m in metrics)

    active_count = sum(1 for m in metrics if str(m["status"]).lower() == "active")

    avg_yield_pa = (
        sum(m["expected_yield_pa"] * m["invested_amount"] for m in metrics) / invested_total
        if invested_total > 0 else 0.0
    )

    this_month_key = pd.Timestamp.today().strftime("%Y-%m")
    next_month_key = (pd.Timestamp.today() + pd.DateOffset(months=1)).strftime("%Y-%m")

    this_month_expected = 0.0
    next_month_expected = 0.0

    if not monthly_df.empty:
        current_row = monthly_df[monthly_df["month"] == this_month_key]
        next_row = monthly_df[monthly_df["month"] == next_month_key]

        if not current_row.empty:
            this_month_expected = float(current_row["expected_interest_total"].sum())

        if not next_row.empty:
            next_month_expected = float(next_row["expected_interest_total"].sum())

    return {
        "portfolio_value": portfolio_value,
        "invested_total": invested_total,
        "paid_out_total": paid_out_total,
        "projects_count": len(metrics),
        "active_count": active_count,
        "avg_yield_pa": avg_yield_pa,
        "this_month_expected": this_month_expected,
        "next_month_expected": next_month_expected,
        "remaining_expected": remaining_expected,
        "estimated_profit_total": estimated_profit_total,
    }


def monthly_project_summary_df(month_df: pd.DataFrame) -> pd.DataFrame:
    if month_df.empty:
        return pd.DataFrame(
            columns=["Projekt", "Počet plateb", "Vyplacený výnos", "Očekávaný výnos", "Celkový výnos"]
        )

    rows = []
    for project_name, group in month_df.groupby("project_name"):
        paid_interest = float(group.loc[group["is_estimated_paid"], "interest_amount"].sum())
        expected_interest = float(group.loc[~group["is_estimated_paid"], "interest_amount"].sum())
        total_interest = float(group["interest_amount"].sum())

        rows.append({
            "Projekt": project_name,
            "Počet plateb": int(len(group)),
            "Vyplacený výnos": round(paid_interest, 2),
            "Očekávaný výnos": round(expected_interest, 2),
            "Celkový výnos": round(total_interest, 2),
        })

    out = pd.DataFrame(rows)
    return out.sort_values(["Celkový výnos", "Projekt"], ascending=[False, True]).reset_index(drop=True)


def monthly_payment_details_df(month_df: pd.DataFrame) -> pd.DataFrame:
    if month_df.empty:
        return pd.DataFrame(
            columns=["Datum", "Projekt", "Typ splátky", "Výnos", "Jistina", "Celkem", "Odhad stavu"]
        )

    type_map = {
        "interest": "Úroky",
        "interest_principal": "Úroky + jistina",
    }

    out = month_df.copy()
    out["Datum"] = out["due_date"]
    out["Projekt"] = out["project_name"]
    out["Typ splátky"] = out["payment_type"].map(type_map).fillna(out["payment_type"])
    out["Výnos"] = out["interest_amount"].round(2)
    out["Jistina"] = out["principal_amount"].round(2)
    out["Celkem"] = out["total_amount"].round(2)
    out["Odhad stavu"] = out["estimated_status"]

    return out[["Datum", "Projekt", "Typ splátky", "Výnos", "Jistina", "Celkem", "Odhad stavu"]]


def schedule_display_df(schedule_df: pd.DataFrame) -> pd.DataFrame:
    if schedule_df.empty:
        return schedule_df

    type_map = {
        "interest": "Úroky",
        "interest_principal": "Úroky + jistina",
    }

    out = schedule_df.copy()
    out["Číslo"] = out["installment_no"]
    out["Datum splátky"] = out["due_date"]
    out["Typ splátky"] = out["payment_type"].map(type_map).fillna(out["payment_type"])
    out["Výnos"] = out["interest_amount"].round(2)
    out["Jistina"] = out["principal_amount"].round(2)
    out["Celkem"] = out["total_amount"].round(2)
    out["Odhad stavu"] = out["estimated_status"]

    return out[["Číslo", "Datum splátky", "Typ splátky", "Výnos", "Jistina", "Celkem", "Odhad stavu"]]


# =========================================================
# INIT
# =========================================================
init_investown_tables()

st.title("🏠 Investown Tracker")
st.caption("Přehled Investown projektů a očekávaných výnosů po měsících.")

_ = get_investown_summary()


# =========================================================
# LOAD DATA
# =========================================================
projects_df = load_projects_df()
monthly_details_df = build_monthly_cashflow_details(projects_df)
monthly_summary_df = build_monthly_cashflow_summary(monthly_details_df)
overall = build_overall_metrics(projects_df, monthly_summary_df)


# =========================================================
# TOP SUMMARY
# =========================================================
top1, top2, top3, top4 = st.columns(4)
with top1:
    st.metric("Hodnota portfolia", fmt_czk(overall["portfolio_value"]))
with top2:
    st.metric("Celkem vloženo", fmt_czk(overall["invested_total"]))
with top3:
    st.metric("Vyplacený výnos", fmt_czk(overall["paid_out_total"]))
with top4:
    st.metric("Orientační průměrný výnos p.a.", fmt_pct(overall["avg_yield_pa"]))

top5, top6, top7, top8 = st.columns(4)
with top5:
    st.metric("Počet investic", overall["projects_count"])
with top6:
    st.metric("Aktivní projekty", overall["active_count"])
with top7:
    st.metric("Očekávaný výnos tento měsíc", fmt_czk(overall["this_month_expected"]))
with top8:
    st.metric("Očekávaný výnos příští měsíc", fmt_czk(overall["next_month_expected"]))

top9, top10 = st.columns(2)
with top9:
    st.metric("Zbývá očekávaný výnos", fmt_czk(overall["remaining_expected"]))
with top10:
    st.metric("Odhad celkového úroku", fmt_czk(overall["estimated_profit_total"]))

st.divider()


# =========================================================
# ADD PROJECT
# =========================================================
st.subheader("Přidat Investown projekt")

with st.form("investown_add_project", clear_on_submit=True):
    c1, c2 = st.columns(2)

    with c1:
        project_name = st.text_input("Název projektu")
        invested_amount = st.number_input(
            "Moje investice (Kč)",
            min_value=0.0,
            value=50000.0,
            step=1000.0,
        )
        investment_date = st.date_input("Datum investice", value=date.today())
        running_project = st.checkbox("Projekt už běží / něco už bylo vyplaceno")

    with c2:
        first_payout_date = st.date_input("Datum první výplaty", value=date.today())
        duration_months = st.number_input(
            "Délka investice (měsíce)",
            min_value=1,
            value=30,
            step=1,
        )
        expected_yield_pa = st.number_input(
            "Očekávaný výnos p.a. (%)",
            min_value=0.0,
            value=8.7,
            step=0.1,
        )

        paid_through_input = None
        if running_project:
            paid_through_input = st.date_input(
                "Vyplaceno do data",
                value=first_payout_date,
                help="Pokud nevyplníš, minulost se automaticky počítá jako vyplacená podle dneška.",
            )

    submit_project = st.form_submit_button(
        "Uložit projekt a vygenerovat kalendář",
        use_container_width=True
    )

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
                paid_through_date=paid_through_input.isoformat() if running_project and paid_through_input else None,
            )
            st.success("Projekt uložen a splátkový kalendář vygenerován.")
            st.rerun()
        except Exception as e:
            st.error(f"Uložení projektu selhalo: {e}")

st.divider()


# =========================================================
# MONTHLY OVERVIEW (MOBILE FRIENDLY)
# =========================================================
st.subheader("Přehled výplat po měsících")

if monthly_summary_df.empty:
    st.info("Zatím tu nejsou žádná data pro měsíční přehled.")
else:
    summary_to_show = monthly_summary_df.copy()
    summary_to_show["month_label"] = summary_to_show["month"].apply(month_label)

    months = summary_to_show["month"].tolist()
    current_month = pd.Timestamp.today().strftime("%Y-%m")

    if "investown_month_index" not in st.session_state:
        if current_month in months:
            st.session_state.investown_month_index = months.index(current_month)
        else:
            st.session_state.investown_month_index = 0

    index = st.session_state.investown_month_index
    index = max(0, min(index, len(months) - 1))
    st.session_state.investown_month_index = index

    nav1, nav2, nav3 = st.columns([1, 3, 1])

    with nav1:
        if st.button("◀", key="month_prev", use_container_width=True):
            st.session_state.investown_month_index = max(0, index - 1)
            st.rerun()

    with nav2:
        month_row = summary_to_show.iloc[st.session_state.investown_month_index]
        st.markdown(f"### {month_row['month_label']}")

    with nav3:
        if st.button("▶", key="month_next", use_container_width=True):
            st.session_state.investown_month_index = min(len(months) - 1, index + 1)
            st.rerun()

    month_key = month_row["month"]
    paid_total = float(month_row["paid_interest_total"] or 0)
    expected_total = float(month_row["expected_interest_total"] or 0)
    month_total = float(month_row["total_interest"] or 0)

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Vyplacený výnos", fmt_czk(paid_total))
    with m2:
        st.metric("Očekávaný výnos", fmt_czk(expected_total))
    with m3:
        st.metric("Celkový výnos", fmt_czk(month_total))

    month_df = monthly_details_df[monthly_details_df["month"] == month_key].copy()

    with st.expander("Detail měsíce"):
        st.markdown("#### Součet podle projektů")
        project_summary = monthly_project_summary_df(month_df)
        st.dataframe(project_summary, use_container_width=True, hide_index=True)

        st.markdown("#### Detail plateb")
        payment_details = monthly_payment_details_df(month_df)
        st.dataframe(payment_details, use_container_width=True, hide_index=True)

st.divider()


# =========================================================
# PROJECT LIST
# =========================================================
st.subheader("Moje investice")

if projects_df.empty:
    st.info("Zatím tu nejsou žádné Investown projekty.")
else:
    projects_df = projects_df.sort_values("investment_date_dt", ascending=False).reset_index(drop=True)

    for _, row in projects_df.iterrows():
        metrics = get_project_metrics(row)
        schedule_df = enrich_schedule_df(load_schedule_df(int(row["project_id"])), row.get("paid_through_date"))

        with st.container(border=True):
            head1, head2 = st.columns([2, 1])

            with head1:
                st.markdown(f"### {metrics['project_name']}")
                st.caption(
                    f"Výnos p.a.: {fmt_pct(metrics['expected_yield_pa'])} · "
                    f"Délka: {metrics['duration_months']} měsíců · "
                    f"Stav: {metrics['status']}"
                )

            with head2:
                st.markdown(f"### {fmt_czk(metrics['invested_amount'])}")
                if metrics["next_payout_date"]:
                    st.caption(f"Další výplata: {metrics['next_payout_date']}")
                else:
                    st.caption("Bez další plánované výplaty")

            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Moje investice", fmt_czk(metrics["invested_amount"]))
            with m2:
                st.metric("Vyplacený výnos", fmt_czk(metrics["paid_interest"]))
            with m3:
                st.metric("Zbývá očekávaný výnos", fmt_czk(metrics["remaining_interest"]))
            with m4:
                st.metric("Další splátka", fmt_czk(metrics["next_payout_amount"]))

            st.progress(int(max(0, min(metrics["completed_pct"], 100))))
            st.caption(f"Odhad průběhu vyplácení výnosu: {metrics['completed_pct']:.1f} %")

            with st.expander("Upravit projekt"):
                e1, e2 = st.columns(2)

                with e1:
                    edit_name = st.text_input(
                        "Název projektu",
                        value=row["project_name"],
                        key=f"edit_name_{row['project_id']}",
                    )
                    edit_invested = st.number_input(
                        "Moje investice (Kč)",
                        min_value=0.0,
                        value=float(row["invested_amount"]),
                        step=1000.0,
                        key=f"edit_invested_{row['project_id']}",
                    )
                    edit_investment_date = st.date_input(
                        "Datum investice",
                        value=pd.to_datetime(row["investment_date"]).date() if pd.notna(row["investment_date_dt"]) else date.today(),
                        key=f"edit_investment_date_{row['project_id']}",
                    )
                    edit_status = st.selectbox(
                        "Stav projektu",
                        options=["active", "finished", "paused"],
                        index=["active", "finished", "paused"].index(row["status"]) if row["status"] in ["active", "finished", "paused"] else 0,
                        key=f"edit_status_{row['project_id']}",
                    )

                with e2:
                    edit_first_payout = st.date_input(
                        "Datum první výplaty",
                        value=pd.to_datetime(row["first_payout_date"]).date() if pd.notna(row["first_payout_date_dt"]) else date.today(),
                        key=f"edit_first_payout_{row['project_id']}",
                    )
                    edit_duration = st.number_input(
                        "Délka investice (měsíce)",
                        min_value=1,
                        value=int(row["duration_months"]),
                        step=1,
                        key=f"edit_duration_{row['project_id']}",
                    )
                    edit_yield = st.number_input(
                        "Očekávaný výnos p.a. (%)",
                        min_value=0.0,
                        value=float(row["expected_yield_pa"]),
                        step=0.1,
                        key=f"edit_yield_{row['project_id']}",
                    )

                    has_paid_through = st.checkbox(
                        "Použít vyplaceno do data",
                        value=pd.notna(row["paid_through_date_dt"]),
                        key=f"has_paid_through_{row['project_id']}",
                    )

                    default_paid_date = (
                        row["paid_through_date_dt"].date()
                        if pd.notna(row["paid_through_date_dt"])
                        else pd.to_datetime(row["first_payout_date"]).date()
                    )

                    edit_paid_through = st.date_input(
                        "Vyplaceno do data",
                        value=default_paid_date,
                        key=f"edit_paid_through_{row['project_id']}",
                    )

                save_cols = st.columns([1, 1, 1, 3])

                with save_cols[0]:
                    save_btn = st.button("💾 Uložit", key=f"save_{row['project_id']}")

                with save_cols[1]:
                    clear_btn = st.button("🧹 Vynulovat vyplaceno", key=f"clear_paid_{row['project_id']}")

                with save_cols[2]:
                    delete_btn = st.button("🗑 Smazat", key=f"delete_{row['project_id']}")

                if save_btn:
                    try:
                        update_investown_project(
                            project_id=int(row["project_id"]),
                            project_name=edit_name.strip(),
                            invested_amount=float(edit_invested),
                            investment_date=edit_investment_date.isoformat(),
                            first_payout_date=edit_first_payout.isoformat(),
                            duration_months=int(edit_duration),
                            expected_yield_pa=float(edit_yield),
                            status=edit_status,
                            paid_through_date=edit_paid_through.isoformat() if has_paid_through else None,
                        )
                        st.success("Projekt byl upraven.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Úprava projektu selhala: {e}")

                if clear_btn:
                    try:
                        update_investown_paid_through_date(int(row["project_id"]), None)
                        st.success("Pole 'vyplaceno do data' bylo vynulováno.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Nepodařilo se vymazat 'vyplaceno do data': {e}")

                if delete_btn:
                    try:
                        delete_investown_project(int(row["project_id"]))
                        st.success("Projekt byl smazán.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Smazání projektu selhalo: {e}")

            with st.expander("Detail projektu a splátkový kalendář"):
                d1, d2 = st.columns(2)
                with d1:
                    st.write(f"**Datum investice:** {row['investment_date']}")
                    st.write(f"**První výplata:** {row['first_payout_date']}")
                    st.write(f"**Vyplaceno do data:** {row['paid_through_date'] if row['paid_through_date'] else 'automaticky dle dneška'}")
                    st.write(f"**První splátka úroku:** {fmt_czk(metrics['first_interest'])}")
                with d2:
                    st.write(f"**Standardní měsíční úrok:** {fmt_czk(metrics['monthly_interest_regular'])}")
                    st.write(f"**Vrácená jistina v závěru:** {fmt_czk(metrics['final_principal'])}")
                    st.write(f"**Zbývá očekávaný výnos:** {fmt_czk(metrics['remaining_interest'])}")
                    st.write(f"**Odhad celkového úroku:** {fmt_czk(metrics['total_expected_interest'])}")

                st.markdown("#### Splátkový kalendář")
                if schedule_df.empty:
                    st.info("Pro tento projekt zatím není vygenerovaný žádný kalendář.")
                else:
                    display_df = schedule_display_df(schedule_df)
                    st.dataframe(display_df, use_container_width=True, hide_index=True)