import streamlit as st

st.set_page_config(
    page_title="Portfolio Dashboard",
    page_icon="📊",
    layout="centered",
)

# --- Header ---
st.title("📊 Portfolio Dashboard by Lucy")

# --- Placeholder data (bezpečné, zatím napevno) ---
total_czk = 700000
total_usd = total_czk / 23  # orientační kurz
profit = 50000

# --- Main metrics ---
st.metric("Celková hodnota (CZK)", f"{total_czk:,.0f} Kč")
st.metric("Celková hodnota (USD)", f"{total_usd:,.0f} $")
st.metric("Zisk / Ztráta", f"{profit:,.0f} Kč")

# --- Footer ---
st.write("📌 Data se budou automaticky aktualizovat z jednotlivých sekcí.")