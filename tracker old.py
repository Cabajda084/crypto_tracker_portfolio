import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
import urllib.parse
from io import BytesIO

DATA_FILE = "transactions.csv"


def load_data() -> pd.DataFrame:
    try:
        df = pd.read_csv(DATA_FILE)
        # základní jistota sloupců
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


@st.cache_data(ttl=60)
def get_crypto_price(coin: str):
    coin_id = normalize_coin(coin)

    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": coin_id, "vs_currencies": "usd"}

    try:
        r = requests.get(url, params=params, timeout=15)
        # když CoinGecko rate-limituje
        if r.status_code == 429:
            return None

        r.raise_for_status()
        data = r.json()

        if not isinstance(data, dict) or coin_id not in data:
            return None
        if "usd" not in data[coin_id]:
            return None

        return float(data[coin_id]["usd"])
    except Exception:
        return None


@st.cache_data(ttl=300)
def get_usdczk():
    # stabilnější než open.er-api (často padá)
    try:
        r = requests.get(
            "https://api.exchangerate.host/latest?base=USD&symbols=CZK",
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        return float(data["rates"]["CZK"])
    except Exception:
        return None
import time

@st.cache_data(ttl=60*60)
def get_price_history_usd(coin: str, start_dt: datetime, end_dt: datetime) -> pd.Series:

    coin_id = normalize_coin(coin)

    start_ts = int(time.mktime(start_dt.timetuple()))
    end_ts = int(time.mktime(end_dt.timetuple()))

    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"
    params = {
        "vs_currency": "usd",
        "from": start_ts,
        "to": end_ts
    }

    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()

        prices = data.get("prices", [])
        if not prices:
            return pd.Series(dtype=float)

        dfp = pd.DataFrame(prices, columns=["ts", "price"])
        dfp["date"] = pd.to_datetime(dfp["ts"], unit="ms").dt.date

        daily = dfp.groupby("date")["price"].last()
        return daily

    except Exception:
        return pd.Series(dtype=float)



# ===============================
# XTB AKCIE – DATA FUNKCE
# ===============================

STOCKS_FILE = "xtb_stocks.csv"

TRACKED_STOCKS = {
    "Amazon": "AMZN",
    "Duolingo": "DUOL",
    "Meta": "META",
    "Microsoft": "MSFT",
}

def load_xtb_stocks() -> pd.DataFrame:
    try:
        df = pd.read_csv(STOCKS_FILE)
    except Exception:
        df = pd.DataFrame(columns=["date", "ticker", "shares", "price_usd"])

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date

    for col in ["shares", "price_usd"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    return df


def save_xtb_stocks(df: pd.DataFrame) -> None:
    df.to_csv(STOCKS_FILE, index=False)


@st.cache_data(ttl=60*15)
def get_stock_price_usd_stooq(ticker: str):
    t = ticker.lower() + ".us"
    url = f"https://stooq.com/q/l/?s={t}&f=sd2t2ohlcv&h&e=csv"

    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()

        lines = r.text.strip().splitlines()
        if len(lines) < 2:
            return None

        import csv
        row = next(csv.DictReader(lines))
        close = row.get("Close")

        if close in (None, "", "N/A"):
            return None

        return float(close)

    except Exception:
        return None

@st.cache_data(ttl=60*60)
def get_usdczk():
    url = "https://api.exchangerate.host/latest?base=USD&symbols=CZK"

    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        return float(data["rates"]["CZK"])
    except Exception:
        return 23
# UI
df = load_data()
# =========================

page = st.sidebar.radio(
    "Navigace",
    ["📊 Přehled", "🪙 Crypto", "📈 Akcie (XTB)", "🧾 Investiční plány (XTB)"]
)
if page == "📊 Přehled":

    st.title("📊 Přehled portfolia")

    # načtení crypto dat
    df_crypto = load_data()

    crypto_invested = 0
    crypto_value = 0

    if len(df_crypto) > 0:

        df_crypto["amount"] = pd.to_numeric(df_crypto["amount"], errors="coerce").fillna(0)
        df_crypto["price"] = pd.to_numeric(df_crypto["price"], errors="coerce").fillna(0)

        crypto_invested = (df_crypto["amount"] * df_crypto["price"]).sum()

        portfolio = {}

        for _, row in df_crypto.iterrows():
            coin = normalize_coin(str(row["coin"]))
            amount = float(row["amount"])

            if coin not in portfolio:
                portfolio[coin] = 0

            portfolio[coin] += amount

        for coin, amount in portfolio.items():
            price = get_crypto_price(coin)

            if price is not None:
                crypto_value += price * amount

    # kurz USD -> CZK
    usdczk = get_usdczk()

    crypto_value_czk = crypto_value * usdczk
    crypto_invested_czk = crypto_invested * usdczk

    st.subheader("Crypto")

    col1, col2 = st.columns(2)

    col1.metric("Investováno", f"{crypto_invested_czk:,.0f} Kč")
    col2.metric("Aktuální hodnota", f"{crypto_value_czk:,.0f} Kč")


elif page == "🪙 Crypto":

    st.title("Crypto Portfolio Tracker by Lucie")
    usdczk = get_usdczk()


st.header("Přidat nákup")
date = st.date_input("Datum", datetime.today())
coin = st.text_input("Coin (např. bitcoin, ethereum, solana)")
amount = st.number_input("Množství", min_value=0.0, value=0.0, step=0.00000001, format="%.8f")
price = st.number_input("Cena při nákupu (USD) – cena 1 coinu", min_value=0.0, value=0.0, step=0.01)

if st.button("Přidat nákup"):
    coin_norm = normalize_coin(coin)
    new_row = {"date": str(date), "coin": coin_norm, "amount": float(amount), "price": float(price)}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_data(df)
    st.success("Uloženo ✅")

st.header("Transakce")
st.dataframe(df)

st.subheader("📁 Export dat")

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Transactions")
    return output.getvalue()

excel_file = to_excel(df)

st.download_button(
    label="Stáhnout transakce do Excelu",
    data=excel_file,
    file_name="crypto_transactions.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# Celkem investováno
total_invested = 0.0
if len(df) > 0:
    # pozor na typy
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0.0)
    total_invested = float((df["amount"] * df["price"]).sum())

st.subheader("Celkem investováno")
st.write(f"{total_invested:.2f} USD")

# Portfolio (aktuální hodnota)
if len(df) > 0:
    portfolio = {}
    for _, row in df.iterrows():
        c = normalize_coin(str(row["coin"]))
        a = float(row["amount"])
        p = float(row["price"])
        if c not in portfolio:
            portfolio[c] = {"amount": 0.0, "cost": 0.0}
        portfolio[c]["amount"] += a
        portfolio[c]["cost"] += a * p

    coins = []
    values = []
    total_value = 0.0
    total_cost = 0.0

    for c, data in portfolio.items():
        price_now = get_crypto_price(c)
        if price_now is None:
            st.warning(f"Nemůžu stáhnout aktuální cenu pro coin: {c} (zkus za chvíli).")
            continue

        value = data["amount"] * price_now
        cost = data["cost"]

        coins.append(c)
        # values.append(value)

        total_value += value
        total_cost += cost

    pnl = total_value - total_cost
    usdczk = get_usdczk()
    value_czk = total_value * usdczk

st.header("Portfolio")
st.write(f"Hodnota (USD): {total_value:.2f}")
st.write(f"Hodnota (CZK): {value_czk:,.0f}")

st.write(f"Zisk / ztráta (USD): {pnl:.2f}")

pnl_percent = (pnl / total_cost) * 100 if total_cost > 0 else 0

if pnl >= 0:
    st.success(f"📈 Zisk: {pnl_percent:.2f}%")
else:
    st.error(f"📉 Ztráta: {pnl_percent:.2f}%")

    if len(values) > 0:
        st.subheader("Rozložení portfolia (USD)")
        chart_df = pd.DataFrame({"coin": coins, "value": values})
        fig = px.pie(chart_df, names="coin", values="value")
        st.plotly_chart(fig, use_container_width=True)
st.subheader("📈 Vývoj portfolia v čase")

if len(df) > 0:
    start_dt = pd.to_datetime(df["date"]).min().to_pydatetime()
    end_dt = datetime.today()

    history_values = {}

    for coin, data in portfolio.items():
        series = get_price_history_usd(coin, start_dt, end_dt)
        if len(series) == 0:
            continue

        amount = data["amount"]
        history_values[coin] = series * amount

    if history_values:
        hist_df = pd.DataFrame(history_values)
        hist_df["total"] = hist_df.sum(axis=1)

        fig_hist = px.line(
            hist_df,
            y="total",
            title="Hodnota portfolia v čase (USD)"
        )
        st.plotly_chart(fig_hist, use_container_width=True)

elif page == "📈 Akcie (XTB)":

    st.title("🟢 Akciové portfolio (XTB)")

    # --- načti data akcií (csv) ---
    df_stocks = load_xtb_stocks()

    # --- formulář: přidat nákup ---
    st.header("🧾 Přidat nákup akcie")

    with st.form("xtb_stock_form"):
        col1, col2 = st.columns(2)

        with col1:
            ticker = st.text_input("Ticker (např. AMZN, META, MSFT)")
            ticker = ticker.upper()
            shares = st.number_input("Počet akcií", min_value=0.0, value=0.0, step=0.001)

        with col2:
            buy_price_usd = st.number_input("Nákupní cena za 1 akcii (USD)", min_value=0.0, value=0.0, step=0.01)
            date_stock = st.date_input("Datum nákupu")

        submit_stock = st.form_submit_button("Uložit nákup")

    if submit_stock:
        new_row = {
            "date": str(date_stock),
            "ticker": str(ticker).upper(),
            "shares": float(shares),
            "price_usd": float(buy_price_usd),
        }
        df_stocks = pd.concat([df_stocks, pd.DataFrame([new_row])], ignore_index=True)
        save_xtb_stocks(df_stocks)
        st.success("✅ Nákup uložen.")

    st.divider()
    st.subheader("📋 Transakce akcií")

    if len(df_stocks) == 0:
    st.info("Zatím tu nemáš žádné akciové nákupy.")
else:
    st.dataframe(df_stocks, use_container_width=True)

    df_stocks["shares"] = pd.to_numeric(df_stocks["shares"], errors="coerce").fillna(0.0)
    df_stocks["price_usd"] = pd.to_numeric(df_stocks["price_usd"], errors="coerce").fillna(0.0)

    invested_usd = (df_stocks["shares"] * df_stocks["price_usd"]).sum()

    # výpočet aktuální hodnoty
    rows = []

    for ticker in df_stocks["ticker"].unique():

        t_df = df_stocks[df_stocks["ticker"] == ticker]

        total_shares = t_df["shares"].sum()
        cost_usd = (t_df["shares"] * t_df["price_usd"]).sum()

        price_now = get_stock_price_usd_stooq(ticker)

        if price_now is None:
            price_now = 0

        value_usd = total_shares * price_now
        pnl = value_usd - cost_usd

        rows.append({
            "ticker": ticker,
            "shares": total_shares,
            "price_now": price_now,
            "value_usd": value_usd,
            "pnl_usd": pnl
        })

    df_sum = pd.DataFrame(rows)

    total_value = df_sum["value_usd"].sum()
    total_pnl = total_value - invested_usd

    usdczk = get_usdczk()

    st.subheader("📊 Souhrn")

    col1, col2, col3 = st.columns(3)

    col1.metric("Investováno", f"{invested_usd*usdczk:,.0f} CZK")
    col2.metric("Hodnota", f"{total_value*usdczk:,.0f} CZK")

    if total_pnl >= 0:
        col3.success(f"Zisk {total_pnl*usdczk:,.0f} CZK")
    else:
        col3.error(f"Ztráta {total_pnl*usdczk:,.0f} CZK")

    st.subheader("📈 Přehled podle akcií")
    st.dataframe(df_sum)
    # --- tabulka transakcí ---
    st.subheader("📋 Transakce akcií")
    if len(df_stocks) == 0:
        st.info("Zatím tu nemáš žádné akciové nákupy.")
    else:
        st.dataframe(df_stocks, use_container_width=True)

        # --- výpočty portfolia ---
        df_stocks["shares"] = pd.to_numeric(df_stocks["shares"], errors="coerce").fillna(0.0)
        df_stocks["price_usd"] = pd.to_numeric(df_stocks["price_usd"], errors="coerce").fillna(0.0)

        invested_usd = float((df_stocks["shares"] * df_stocks["price_usd"]).sum())

        # aktuální ceny (online) + hodnota
        tickers = sorted(df_stocks["ticker"].dropna().unique().tolist())
        rows = []

        for t in tickers:
            t_df = df_stocks[df_stocks["ticker"] == t]
            total_shares = float(t_df["shares"].sum())
            avg_buy = float((t_df["shares"] * t_df["price_usd"]).sum() / total_shares) if total_shares > 0 else 0.0
            cost_usd = float((t_df["shares"] * t_df["price_usd"]).sum())

            # online cena
            px = get_stock_price_usd_stooq(t)
            if px is None:
                px = 0.0

            value_usd = float(total_shares * px)
            pnl_usd = float(value_usd - cost_usd)
            pnl_pct = float((pnl_usd / cost_usd) * 100) if cost_usd > 0 else 0.0

            rows.append({
                "ticker": t,
                "shares": total_shares,
                "avg_buy_usd": round(avg_buy, 4),
                "price_now_usd": round(px, 4),
                "cost_usd": round(cost_usd, 2),
                "value_usd": round(value_usd, 2),
                "pnl_usd": round(pnl_usd, 2),
                "pnl_pct": round(pnl_pct, 2),
            })

        df_sum = pd.DataFrame(rows)

        total_value_usd = float(df_sum["value_usd"].sum())
        total_pnl_usd = float(total_value_usd - invested_usd)
        total_pnl_pct = float((total_pnl_usd / invested_usd) * 100) if invested_usd > 0 else 0.0

        # kurz USD->CZK (už máš funkci get_usdczk())
        usdczk = get_usdczk()
        if usdczk is None:
            usdczk = 1.0

        invested_czk = invested_usd * usdczk
        total_value_czk = total_value_usd * usdczk
        total_pnl_czk = total_pnl_usd * usdczk

        # --- metriky nahoře ---
        st.subheader("📌 Souhrn akcií")
        c1, c2, c3 = st.columns(3)
        c1.metric("Investováno", f"{invested_czk:,.0f} CZK", f"{invested_usd:,.2f} USD")
        c2.metric("Aktuální hodnota", f"{total_value_czk:,.0f} CZK", f"{total_value_usd:,.2f} USD")

        if total_pnl_usd >= 0:
            c3.success(f"✅ Zisk: {total_pnl_czk:,.0f} CZK ({total_pnl_pct:.2f}%)")
        else:
            c3.error(f"🔻 Ztráta: {total_pnl_czk:,.0f} CZK ({total_pnl_pct:.2f}%)")

        # --- tabulka souhrnu ---
        st.subheader("📊 Přehled podle akcií")
        st.dataframe(df_sum, use_container_width=True)

        # --- graf rozložení ---
        if len(df_sum) > 0 and df_sum["value_usd"].sum() > 0:
            st.subheader("🥧 Rozložení portfolia")
                fig_pie = px.pie(df_sum, names="ticker", values="value_usd")
                st.plotly_chart(fig_pie, use_container_width=True)


elif page == "🧾 Investiční plány (XTB)":
    st.title("…")
    st.info("Tahle stránka je zatím prázdná.")

     
