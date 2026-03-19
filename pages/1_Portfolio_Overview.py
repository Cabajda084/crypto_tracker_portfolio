import streamlit as st
import pandas as pd
import requests

from invest_service import get_portfolio_overview_payload, fmt_czk

# =========================================================
# SAFE INVESTOWN IMPORT (ADDITIVE ONLY)
# =========================================================
try:
    from investown_service import get_investown_projects, get_investown_summary

    INVESTOWN_AVAILABLE = True
except Exception:
    INVESTOWN_AVAILABLE = False

    def get_investown_projects():
        return []

    def get_investown_summary():
        return {
            "invested": 0.0,
            "paid_out": 0.0,
            "profit": 0.0,
        }


DATA_FILE = "transactions.csv"
TRACKED_COINS = ["bitcoin", "ethereum", "solana"]


def load_data() -> pd.DataFrame:
    try:
        df = pd.read_csv(DATA_FILE)
        for col in ["date", "coin", "amount", "price"]:
            if col not in df.columns:
                df[col] = None
        return df[["date", "coin", "amount", "price"]]
    except Exception:
        return pd.DataFrame(columns=["date", "coin", "amount", "price"])


def normalize_coin(coin: str) -> str:
    c = (coin or "").strip().lower()
    mapping = {
        "btc": "bitcoin",
        "bitcoin": "bitcoin",
        "eth": "ethereum",
        "ether": "ethereum",
        "ethereum": "ethereum",
        "sol": "solana",
        "solana": "solana",
    }
    return mapping.get(c, c)


def pretty_coin_name(coin: str) -> str:
    mapping = {
        "bitcoin": "Bitcoin",
        "ethereum": "Ethereum",
        "solana": "Solana",
    }
    return mapping.get(coin, coin.title())


def pretty_coin_ticker(coin: str) -> str:
    mapping = {
        "bitcoin": "BTC",
        "ethereum": "ETH",
        "solana": "SOL",
    }
    return mapping.get(coin, coin.upper())


def prepare_transactions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["date", "coin", "amount", "price"]:
        if col not in df.columns:
            df[col] = None

    df = df[["date", "coin", "amount", "price"]]
    df["coin"] = df["coin"].astype(str).apply(normalize_coin)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0.0)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


@st.cache_data(ttl=60)
def get_crypto_price(coin: str):
    coin_id = normalize_coin(coin)

    # =========================================================
    # 1) COINGECKO (PRIMARY)
    # =========================================================
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": coin_id, "vs_currencies": "usd"}

        r = requests.get(url, params=params, timeout=10)

        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and coin_id in data and "usd" in data[coin_id]:
                return float(data[coin_id]["usd"])

        if r.status_code == 429:
            pass

    except Exception:
        pass

    # =========================================================
    # 2) BINANCE (FALLBACK)
    # =========================================================
    try:
        symbol_map = {
            "bitcoin": "BTCUSDT",
            "ethereum": "ETHUSDT",
            "solana": "SOLUSDT",
        }

        symbol = symbol_map.get(coin_id)

        if symbol:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            r = requests.get(url, timeout=10)

            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict) and "price" in data:
                    return float(data["price"])

    except Exception:
        pass

    return None


@st.cache_data(ttl=3600)
def get_usdczk():
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=15)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and "rates" in data and "CZK" in data["rates"]:
            return float(data["rates"]["CZK"])
    except Exception:
        pass

    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=15)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and "rates" in data and "CZK" in data["rates"]:
            return float(data["rates"]["CZK"])
    except Exception:
        pass

    return 23.0


def build_portfolio(df: pd.DataFrame) -> dict:
    portfolio = {}
    if df.empty:
        return portfolio

    df_sorted = df.sort_values("date", na_position="last").copy()

    for _, row in df_sorted.iterrows():
        coin = normalize_coin(str(row["coin"]))
        amount = float(row["amount"]) if pd.notna(row["amount"]) else 0.0
        price = float(row["price"]) if pd.notna(row["price"]) else 0.0

        if not coin:
            continue

        if coin not in portfolio:
            portfolio[coin] = {"amount": 0.0, "cost": 0.0}

        current_amount = portfolio[coin]["amount"]
        current_cost = portfolio[coin]["cost"]

        if amount > 0:
            portfolio[coin]["amount"] = current_amount + amount
            portfolio[coin]["cost"] = current_cost + (amount * price)

        elif amount < 0:
            sell_amount = abs(amount)
            if current_amount <= 0:
                continue

            avg_buy_price = current_cost / current_amount if current_amount > 0 else 0.0
            actual_sell_amount = min(sell_amount, current_amount)

            portfolio[coin]["amount"] = current_amount - actual_sell_amount
            portfolio[coin]["cost"] = current_cost - (actual_sell_amount * avg_buy_price)

        if portfolio[coin]["amount"] < 1e-12:
            portfolio[coin]["amount"] = 0.0
            portfolio[coin]["cost"] = 0.0

    for coin in portfolio:
        amount = portfolio[coin]["amount"]
        cost = portfolio[coin]["cost"]
        portfolio[coin]["avg_buy_price"] = (cost / amount) if amount > 0 else 0.0

    return portfolio


def get_coin_metrics(portfolio: dict, usdczk: float):
    metrics = {}
    unavailable_prices = []

    for coin in TRACKED_COINS:
        data = portfolio.get(coin, {"amount": 0.0, "cost": 0.0, "avg_buy_price": 0.0})
        amount = float(data["amount"])
        cost_usd = float(data["cost"])
        avg_buy_price = float(data["avg_buy_price"])

        price_now = get_crypto_price(coin)

        if amount > 0 and price_now is not None:
            value_usd = amount * price_now
            pnl_usd = value_usd - cost_usd
            pnl_pct = (pnl_usd / cost_usd) * 100 if cost_usd > 0 else 0.0
        else:
            value_usd = None
            pnl_usd = None
            pnl_pct = None
            if amount > 0 and price_now is None:
                unavailable_prices.append(pretty_coin_ticker(coin))

        metrics[coin] = {
            "amount": amount,
            "cost_usd": cost_usd,
            "cost_czk": cost_usd * usdczk,
            "avg_buy_price": avg_buy_price,
            "price_now": price_now,
            "value_usd": value_usd,
            "value_czk": value_usd * usdczk if value_usd is not None else None,
            "pnl_usd": pnl_usd,
            "pnl_czk": pnl_usd * usdczk if pnl_usd is not None else None,
            "pnl_pct": pnl_pct,
        }

    return metrics, unavailable_prices


def get_investown_overview_payload():
    """
    Safe, additive summary for Investown.
    Portfolio value for first version = invested amount of active projects.
    """
    try:
        summary = get_investown_summary() or {}
        projects = get_investown_projects() or []

        invested_total = float(summary.get("invested", 0.0) or 0.0)
        paid_out_total = float(summary.get("paid_out", 0.0) or 0.0)
        profit_total = float(summary.get("profit", 0.0) or 0.0)

        # první konzervativní verze:
        # portfolio value = stále alokovaná investovaná částka
        portfolio_value = invested_total
        projects_count = len(projects)

        return {
            "portfolio_value_czk": portfolio_value,
            "invested_amount_czk": invested_total,
            "paid_out_czk": paid_out_total,
            "profit_czk": profit_total,
            "projects_count": projects_count,
        }
    except Exception:
        return {
            "portfolio_value_czk": 0.0,
            "invested_amount_czk": 0.0,
            "paid_out_czk": 0.0,
            "profit_czk": 0.0,
            "projects_count": 0,
        }


def format_usd(value):
    return "N/A" if value is None else f"${value:,.2f}"


def format_czk_crypto(value):
    return "N/A" if value is None else f"{value:,.0f} CZK"


def format_amount(value):
    if value is None:
        return "0"
    return f"{value:.8f}".rstrip("0").rstrip(".")


st.title("Portfolio Overview")
st.write("Celkový přehled portfolia")

# =========================================================
# CRYPTO SUMMARY
# =========================================================
usdczk = get_usdczk()
df = load_data()
df_clean = prepare_transactions(df)
portfolio = build_portfolio(df_clean)
coin_metrics, unavailable_prices = get_coin_metrics(portfolio, usdczk)

total_cost_usd = sum(m["cost_usd"] for m in coin_metrics.values())
total_value_usd = sum(m["value_usd"] for m in coin_metrics.values() if m["value_usd"] is not None)
total_pnl_usd = total_value_usd - total_cost_usd
total_pnl_pct = (total_pnl_usd / total_cost_usd) * 100 if total_cost_usd > 0 else 0.0

crypto_total_value_czk = total_value_usd * usdczk
crypto_total_cost_czk = total_cost_usd * usdczk
crypto_total_pnl_czk = total_pnl_usd * usdczk

# =========================================================
# INVEST SUMMARY
# =========================================================
invest_summary = get_portfolio_overview_payload()
invest_total_value_czk = invest_summary["total_value_czk"]
invest_positions_value_czk = invest_summary["positions_value_czk"]
invest_cash_balance_czk = invest_summary["cash_balance_czk"]
invest_total_cost_czk = invest_summary["invested_amount_czk"]
invest_total_pnl_czk = invest_summary["profit_loss_czk"]
invest_total_pnl_pct = invest_summary["profit_loss_pct"]

# =========================================================
# INVESTOWN SUMMARY (NEW - SAFE ADDITIVE)
# =========================================================
investown_summary = get_investown_overview_payload()
investown_total_value_czk = investown_summary["portfolio_value_czk"]
investown_total_cost_czk = investown_summary["invested_amount_czk"]
investown_paid_out_czk = investown_summary["paid_out_czk"]
investown_total_pnl_czk = investown_summary["profit_czk"]
investown_projects_count = investown_summary["projects_count"]
investown_total_pnl_pct = (
    (investown_total_pnl_czk / investown_total_cost_czk) * 100
    if investown_total_cost_czk > 0 else 0.0
)

# =========================================================
# TOTALS
# =========================================================
net_worth_czk = crypto_total_value_czk + invest_total_value_czk + investown_total_value_czk
total_invested_czk = crypto_total_cost_czk + invest_total_cost_czk + investown_total_cost_czk
total_pnl_czk = crypto_total_pnl_czk + invest_total_pnl_czk + investown_total_pnl_czk
total_pnl_pct_all = (total_pnl_czk / total_invested_czk * 100) if total_invested_czk > 0 else 0.0

st.caption(f"Aktuální kurz: 1 USD = {usdczk:.2f} CZK")
# =========================================================
# 🔝 SIMPLE OVERVIEW (NEW - SAFE)
# =========================================================

st.subheader("Rychlý přehled")

# --- Crypto ---
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Crypto Investováno", fmt_czk(crypto_total_cost_czk))
with c2:
    st.metric("Crypto Hodnota", fmt_czk(crypto_total_value_czk))
with c3:
    st.metric("Crypto P/L", fmt_czk(crypto_total_pnl_czk), f"{total_pnl_pct:.2f}%")

st.divider()

# --- Invest ---
i1, i2, i3 = st.columns(3)
with i1:
    st.metric("Invest Investováno", fmt_czk(invest_total_cost_czk))
with i2:
    st.metric("Invest Hodnota", fmt_czk(invest_total_value_czk))
with i3:
    st.metric("Invest P/L", fmt_czk(invest_total_pnl_czk), f"{invest_total_pnl_pct:.2f}%")

st.divider()

# --- Investown ---
j1, j2, j3 = st.columns(3)
with j1:
    st.metric("Investown Investováno", fmt_czk(investown_total_cost_czk))
with j2:
    st.metric("Investown Hodnota", fmt_czk(investown_total_value_czk))
with j3:
    st.metric("Investown P/L", fmt_czk(investown_total_pnl_czk), f"{investown_total_pnl_pct:.2f}%")

st.divider()

# 🔝 HLAVNÍ ČÍSLO NAHOŘE
st.metric("Celkem investováno", fmt_czk(total_invested_czk))

# 🔽 Doplňkové metriky
top1, top2 = st.columns(2)
with top1:
    st.metric("Celková hodnota portfolia", fmt_czk(net_worth_czk))
with top2:
    st.metric("Celkový zisk / ztráta", fmt_czk(total_pnl_czk), f"{total_pnl_pct_all:.2f}%")
st.divider()

# =========================================================
# EXISTING BLOCKS KEPT AS-IS
# =========================================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("Crypto Tracker")
    st.write("Přehled kryptoměnového portfolia")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Investováno", format_usd(total_cost_usd), format_czk_crypto(total_cost_usd * usdczk))
    with c2:
        st.metric("Aktuální hodnota", format_usd(total_value_usd), format_czk_crypto(total_value_usd * usdczk))
    with c3:
        st.metric("Zisk / ztráta", format_usd(total_pnl_usd), f"{total_pnl_pct:.2f}%")

    if unavailable_prices:
        st.warning("Dočasně se nepodařilo načíst cenu pro: " + ", ".join(unavailable_prices))

    for coin in TRACKED_COINS:
        m = coin_metrics[coin]
        with st.container(border=True):
            top_left, top_right = st.columns([2, 1])
            with top_left:
                st.markdown(f"**{pretty_coin_name(coin)} ({pretty_coin_ticker(coin)})**")
                st.caption(f"Množství: {format_amount(m['amount'])}")
            with top_right:
                st.markdown(f"**{format_usd(m['value_usd'])}**")
                if m["pnl_pct"] is not None:
                    st.caption(f"P/L: {m['pnl_pct']:+.2f}%")
                else:
                    st.caption("Cena nedostupná")

with col2:
    st.subheader("Invest Tracker")
    st.write("Přehled investičních plánů")

    i1, i2, i3 = st.columns(3)
    with i1:
        st.metric("Hodnota pozic", fmt_czk(invest_positions_value_czk))
    with i2:
        st.metric("Cash rezerva", fmt_czk(invest_cash_balance_czk))
    with i3:
        st.metric("Celkem Invest", fmt_czk(invest_total_value_czk), f"{invest_total_pnl_pct:.2f}%")

    if not invest_summary["plans"]:
        st.info("Invest Tracker zatím neobsahuje aktivní investiční plán nebo data.")
    else:
        for plan in invest_summary["plans"]:
            with st.container(border=True):
                left, right = st.columns([2, 1])
                with left:
                    st.markdown(f"**{plan['icon']} {plan['display_name']}**")
                    st.caption(f"Pozice: {fmt_czk(plan['positions_value'])} · Cash: {fmt_czk(plan['cash_balance'])}")
                with right:
                    st.markdown(f"**{fmt_czk(plan['portfolio_value'])}**")
                    pnl_text = f"{plan['profit_loss']:+,.2f} CZK ({plan['profit_loss_pct']:+.2f}%)"
                    st.caption(f"P/L: {pnl_text.replace(',', ' ')}")

st.divider()

# =========================================================
# NEW INVESTOWN BLOCK
# =========================================================
st.subheader("Investown Tracker")
st.write("Přehled Investown projektů")

j1, j2, j3, j4 = st.columns(4)
with j1:
    st.metric("Hodnota portfolia", fmt_czk(investown_total_value_czk))
with j2:
    st.metric("Celkem vloženo", fmt_czk(investown_total_cost_czk))
with j3:
    st.metric("Vyplaceno", fmt_czk(investown_paid_out_czk))
with j4:
    st.metric("Počet projektů", investown_projects_count)

if not INVESTOWN_AVAILABLE:
    st.info("Investown service zatím není dostupný.")
elif investown_projects_count == 0:
    st.info("Investown Tracker zatím neobsahuje žádné projekty.")
else:
    st.caption(
        f"Celkový výsledek Investown: {fmt_czk(investown_total_pnl_czk)} "
        f"({investown_total_pnl_pct:.2f}%)"
    )