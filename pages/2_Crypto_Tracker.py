import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from io import BytesIO
import time

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


def save_data(df: pd.DataFrame) -> None:
    df.to_csv(DATA_FILE, index=False)


def normalize_coin(coin: str) -> str:
    c = (coin or "").strip().lower()
    mapping = {
        "eth": "ethereum",
        "ether": "ethereum",
        "ethereum": "ethereum",
        "btc": "bitcoin",
        "bitcoin": "bitcoin",
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


@st.cache_data(ttl=3600)
def get_price_history_usd(coin: str, start_dt: datetime, end_dt: datetime) -> pd.Series:
    coin_id = normalize_coin(coin)
    start_ts = int(time.mktime(start_dt.timetuple()))
    end_ts = int(time.mktime(end_dt.timetuple()))

    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"
    params = {"vs_currency": "usd", "from": start_ts, "to": end_ts}

    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()

        prices = data.get("prices", [])
        if not prices:
            return pd.Series(dtype=float)

        dfp = pd.DataFrame(prices, columns=["ts", "price"])
        dfp["date"] = pd.to_datetime(dfp["ts"], unit="ms").dt.date
        return dfp.groupby("date")["price"].last()
    except Exception:
        return pd.Series(dtype=float)


def to_excel(df: pd.DataFrame):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Transactions")
    return output.getvalue()


def build_portfolio(df: pd.DataFrame) -> dict:
    portfolio = {}
    if df.empty:
        return portfolio

    df = df.copy()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0.0)

    for _, row in df.iterrows():
        coin = normalize_coin(str(row["coin"]))
        amount = float(row["amount"])
        price = float(row["price"])

        if coin not in portfolio:
            portfolio[coin] = {"amount": 0.0, "cost": 0.0}

        portfolio[coin]["amount"] += amount
        portfolio[coin]["cost"] += amount * price

    return portfolio


def format_czk(value: float) -> str:
    return f"{value:,.0f} CZK".replace(",", " ")


def format_usd(value) -> str:
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


st.set_page_config(page_title="Crypto Tracker", page_icon="🪙", layout="wide")
st.title("🪙 Crypto Tracker")

# =========================================================
# DATA + SUMMARY (nahoře pod názvem)
# =========================================================
df = load_data()
usdczk = get_usdczk()
portfolio = build_portfolio(df)

rows = []
total_cost = sum(v["cost"] for v in portfolio.values())
total_value = 0.0
unavailable_prices = []

for coin_name, data in portfolio.items():
    price_now = get_crypto_price(coin_name)
    amount_now = float(data["amount"])
    cost_usd = float(data["cost"])

    if amount_now <= 0:
        continue

    if price_now is None:
        value_usd = None
        pnl_usd = None
        pnl_pct = None
        unavailable_prices.append(pretty_coin_ticker(coin_name))
    else:
        value_usd = amount_now * price_now
        pnl_usd = value_usd - cost_usd
        pnl_pct = (pnl_usd / cost_usd * 100) if cost_usd > 0 else 0.0
        total_value += value_usd

    rows.append({
        "coin": pretty_coin_name(coin_name),
        "ticker": pretty_coin_ticker(coin_name),
        "amount": amount_now,
        "avg_buy_price_usd": (cost_usd / amount_now) if amount_now > 0 else 0.0,
        "current_price_usd": price_now,
        "value_usd": value_usd,
        "pnl_usd": pnl_usd,
        "pnl_pct": pnl_pct,
    })

portfolio_df = pd.DataFrame(rows)
total_pnl = total_value - total_cost
value_czk = total_value * usdczk
invested_czk = total_cost * usdczk
pnl_czk = total_pnl * usdczk
pnl_pct_total = (total_pnl / total_cost * 100) if total_cost > 0 else 0.0

st.caption(f"Aktuální kurz: 1 USD = {usdczk:.2f} CZK")


c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Investováno", format_czk(invested_czk))
with c2:
    st.metric("Aktuální hodnota", format_czk(value_czk))
with c3:
    st.metric("Zisk / ztráta", format_czk(pnl_czk), f"{pnl_pct_total:.2f}%")

if unavailable_prices:
    st.warning("Dočasně se nepodařilo načíst cenu pro: " + ", ".join(sorted(set(unavailable_prices))))

st.divider()

# =========================================================
# FORMULÁŘ PRO PŘIDÁNÍ NÁKUPU
# =========================================================
st.header("Přidat nákup")
date = st.date_input("Datum", datetime.today())
coin = st.selectbox("Coin", TRACKED_COINS)
amount = st.number_input("Množství", min_value=0.0, value=0.0, step=0.00000001, format="%.8f")
price = st.number_input("Cena při nákupu (USD)", min_value=0.0, value=0.0, step=0.01)

if st.button("Přidat nákup"):
    new_row = {
        "date": str(date),
        "coin": normalize_coin(coin),
        "amount": float(amount),
        "price": float(price),
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_data(df)
    st.success("Uloženo.")
    st.rerun()

# =========================================================
# TRANSAKCE
# =========================================================
st.header("Transakce")
st.dataframe(df, use_container_width=True, hide_index=True)

# =========================================================
# EXPORT
# =========================================================
st.subheader("📁 Export dat")
excel_file = to_excel(df)
st.download_button(
    label="Stáhnout transakce do Excelu",
    data=excel_file,
    file_name="crypto_transactions.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# =========================================================
# PORTFOLIO + GRAFY
# =========================================================
if not portfolio_df.empty:
    show_df = portfolio_df.copy()

    for col in ["amount"]:
        if col in show_df.columns:
            show_df[col] = pd.to_numeric(show_df[col], errors="coerce").round(8)

    for col in ["avg_buy_price_usd", "current_price_usd", "value_usd", "pnl_usd", "pnl_pct"]:
        if col in show_df.columns:
            show_df[col] = pd.to_numeric(show_df[col], errors="coerce").round(2)

    st.subheader("Portfolio")
    st.dataframe(show_df, use_container_width=True, hide_index=True)

    chart_df = portfolio_df.dropna(subset=["value_usd"])[["coin", "value_usd"]]
    if not chart_df.empty:
        st.subheader("Rozložení portfolia")
        fig = px.pie(chart_df, names="coin", values="value_usd")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📈 Vývoj portfolia v čase")
    start_dt = pd.to_datetime(df["date"], errors="coerce").min()
    start_dt = start_dt.to_pydatetime() if pd.notna(start_dt) else datetime.today()
    end_dt = datetime.today()

    history_values = {}
    for coin_name, data in portfolio.items():
        if float(data["amount"]) <= 0:
            continue

        series = get_price_history_usd(coin_name, start_dt, end_dt)
        if len(series) == 0:
            continue

        history_values[pretty_coin_name(coin_name)] = series * float(data["amount"])

    if history_values:
        hist_df = pd.DataFrame(history_values)
        hist_df["total"] = hist_df.sum(axis=1)

        fig_hist = px.line(hist_df, y="total", title="Hodnota portfolia v čase (USD)")
        st.plotly_chart(fig_hist, use_container_width=True)
    else:
        st.info("Nepodařilo se načíst historická data pro graf vývoje portfolia.")
else:
    st.info("Zatím tu nejsou žádné kryptotransakce.")