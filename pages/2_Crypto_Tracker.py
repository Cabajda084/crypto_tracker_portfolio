import time
from datetime import datetime
from io import BytesIO

import pandas as pd
import requests
import streamlit as st

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except Exception:
    px = None
    PLOTLY_AVAILABLE = False


DATA_FILE = "transactions.csv"
TRACKED_COINS = ["bitcoin", "ethereum", "solana", "polkadot"]
MAIN_COINS = {"bitcoin", "ethereum", "solana"}
DOT_COIN = "polkadot"
LAST_KNOWN_PRICES = {}


# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Crypto Tracker",
    page_icon="🪙",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# STYLES
# =========================================================
def inject_css():
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1280px;
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }

        .app-title {
            font-size: 2.1rem;
            font-weight: 800;
            line-height: 1.1;
            margin-bottom: 0.15rem;
        }

        .app-subtitle {
            color: #6b7280;
            margin-bottom: 1rem;
        }

        .summary-card, .coin-card, .section-card {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 20px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        }

        .summary-card {
            padding: 16px 18px;
            margin-bottom: 12px;
        }

        .summary-label {
            font-size: 0.92rem;
            color: #6b7280;
            margin-bottom: 6px;
        }

        .summary-value {
            font-size: 1.55rem;
            font-weight: 800;
            color: #111827;
            line-height: 1.1;
            margin-bottom: 6px;
        }

        .summary-subvalue {
            font-size: 0.98rem;
            color: #6b7280;
            line-height: 1.2;
            margin-bottom: 6px;
        }

        .summary-delta-pos {
            color: #16a34a;
            font-weight: 700;
            margin-top: 6px;
        }

        .summary-delta-neg {
            color: #dc2626;
            font-weight: 700;
            margin-top: 6px;
        }

        .coin-card {
            padding: 14px 16px;
            margin-bottom: 10px;
        }

        .coin-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 12px;
        }

        .coin-name {
            font-size: 1.05rem;
            font-weight: 800;
            color: #111827;
            line-height: 1.1;
        }

        .coin-ticker {
            font-size: 0.88rem;
            color: #6b7280;
            margin-top: 4px;
        }

        .coin-value {
            font-size: 1.2rem;
            font-weight: 800;
            color: #111827;
            text-align: right;
            line-height: 1.1;
        }

        .coin-sub {
            color: #6b7280;
            font-size: 0.9rem;
            margin-top: 8px;
        }

        .coin-pl-pos {
            color: #16a34a;
            font-weight: 700;
            font-size: 0.92rem;
            margin-top: 8px;
        }

        .coin-pl-neg {
            color: #dc2626;
            font-weight: 700;
            font-size: 0.92rem;
            margin-top: 8px;
        }

        .section-card {
            padding: 16px 18px;
            margin-bottom: 12px;
        }

        .section-title {
            font-size: 1.08rem;
            font-weight: 800;
            margin-bottom: 0.8rem;
            color: #111827;
        }

        .small-muted {
            color: #6b7280;
            font-size: 0.92rem;
        }

        .stButton > button,
        .stDownloadButton > button,
        div[data-testid="stFormSubmitButton"] > button {
            width: 100%;
            border-radius: 12px;
            min-height: 44px;
            font-weight: 600;
        }

        @media (max-width: 768px) {
            .block-container {
                padding-top: 0.8rem;
                padding-left: 0.75rem;
                padding-right: 0.75rem;
                padding-bottom: 1.25rem;
            }

            .app-title {
                font-size: 1.6rem;
            }

            .app-subtitle {
                font-size: 0.92rem;
                margin-bottom: 0.8rem;
            }

            .summary-card {
                padding: 14px 14px;
                border-radius: 16px;
            }

            .summary-value {
                font-size: 1.25rem;
            }

            .summary-subvalue {
                font-size: 0.92rem;
            }

            .coin-card {
                padding: 12px 13px;
                border-radius: 16px;
            }

            .coin-name {
                font-size: 1rem;
            }

            .coin-value {
                font-size: 1.05rem;
            }

            .section-card {
                padding: 14px 14px;
                border-radius: 16px;
            }

            h1 {
                font-size: 1.55rem !important;
            }

            h2, h3 {
                font-size: 1.1rem !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_css()


# =========================================================
# HELPERS
# =========================================================
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
        "dot": "polkadot",
        "polkadot": "polkadot",
    }
    return mapping.get(c, c)


def pretty_coin_name(coin: str) -> str:
    mapping = {
        "bitcoin": "Bitcoin",
        "ethereum": "Ethereum",
        "solana": "Solana",
        "polkadot": "Polkadot",
    }
    return mapping.get(coin, coin.title())


def pretty_coin_ticker(coin: str) -> str:
    mapping = {
        "bitcoin": "BTC",
        "ethereum": "ETH",
        "solana": "SOL",
        "polkadot": "DOT",
    }
    return mapping.get(coin, coin.upper())


def format_czk(value: float) -> str:
    return f"{value:,.2f} CZK".replace(",", " ")


def format_usd(value) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"${value:,.2f}"


def format_amount_exact(value: float) -> str:
    try:
        return f"{float(value):.8f}".rstrip("0").rstrip(".")
    except Exception:
        return "0"


def render_summary_card(
    label: str,
    value_main: str,
    value_sub: str | None = None,
    delta: str | None = None,
    positive: bool = True,
):
    sub_html = f'<div class="summary-subvalue">{value_sub}</div>' if value_sub else ""
    delta_html = ""
    if delta:
        delta_class = "summary-delta-pos" if positive else "summary-delta-neg"
        delta_html = f'<div class="{delta_class}">{delta}</div>'

    st.markdown(
        f"""
        <div class="summary-card">
            <div class="summary-label">{label}</div>
            <div class="summary-value">{value_main}</div>
            {sub_html}
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_coin_card(row: pd.Series):
    pnl = row.get("pnl_usd")
    pnl_pct = row.get("pnl_pct")

    if pnl is None or pd.isna(pnl):
        pnl_text = "P/L: N/A"
        pnl_class = "coin-pl-neg"
    else:
        pnl_text = f"P/L: {format_usd(pnl)} ({pnl_pct:.2f}%)"
        pnl_class = "coin-pl-pos" if pnl >= 0 else "coin-pl-neg"

    current_price = row.get("current_price_usd")
    current_price_text = format_usd(current_price) if current_price is not None else "N/A"

    value_usd = row.get("value_usd")
    value_text = format_usd(value_usd) if value_usd is not None else "N/A"

    st.markdown(
        f"""
        <div class="coin-card">
            <div class="coin-top">
                <div>
                    <div class="coin-name">{row["coin"]}</div>
                    <div class="coin-ticker">{row["ticker"]} · {format_amount_exact(row["amount"])} ks</div>
                </div>
                <div class="coin-value">{value_text}</div>
            </div>
            <div class="coin-sub">
                Průměrný nákup: {format_usd(row["avg_buy_price_usd"])} · Aktuální cena: {current_price_text}
            </div>
            <div class="{pnl_class}">{pnl_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=60)
def get_crypto_price(coin: str):
    coin_id = normalize_coin(coin)

    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": coin_id, "vs_currencies": "usd"}
        r = requests.get(url, params=params, timeout=10)

        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and coin_id in data and "usd" in data[coin_id]:
                return float(data[coin_id]["usd"])
    except Exception:
        pass

    try:
        symbol_map = {
            "bitcoin": "BTCUSDT",
            "ethereum": "ETHUSDT",
            "solana": "SOLUSDT",
            "polkadot": "DOTUSDT",
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


def format_transactions_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        return out

    if "date" in out.columns:
        out["date"] = out["date"].astype(str)

    if "coin" in out.columns:
        out["coin"] = out["coin"].astype(str)

    if "amount" in out.columns:
        out["amount"] = pd.to_numeric(out["amount"], errors="coerce").apply(format_amount_exact)

    if "price" in out.columns:
        out["price"] = pd.to_numeric(out["price"], errors="coerce").apply(
            lambda x: f"{x:.2f}" if pd.notna(x) else ""
        )

    return out


def format_portfolio_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        return out

    if "amount" in out.columns:
        out["amount"] = pd.to_numeric(out["amount"], errors="coerce").apply(format_amount_exact)

    for col in ["avg_buy_price_usd", "current_price_usd", "value_usd", "pnl_usd", "pnl_pct"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    if "avg_buy_price_usd" in out.columns:
        out["avg_buy_price_usd"] = out["avg_buy_price_usd"].apply(
            lambda x: round(x, 2) if pd.notna(x) else None
        )
    if "current_price_usd" in out.columns:
        out["current_price_usd"] = out["current_price_usd"].apply(
            lambda x: round(x, 2) if pd.notna(x) else None
        )
    if "value_usd" in out.columns:
        out["value_usd"] = out["value_usd"].apply(
            lambda x: round(x, 2) if pd.notna(x) else None
        )
    if "pnl_usd" in out.columns:
        out["pnl_usd"] = out["pnl_usd"].apply(
            lambda x: round(x, 2) if pd.notna(x) else None
        )
    if "pnl_pct" in out.columns:
        out["pnl_pct"] = out["pnl_pct"].apply(
            lambda x: round(x, 2) if pd.notna(x) else None
        )

    return out


def summarize_portfolio_group(portfolio: dict, include_coins: set[str]) -> dict:
    invested_usd = 0.0
    value_usd = 0.0
    has_any = False
    has_missing_price = False

    for coin_name, data in portfolio.items():
        if coin_name not in include_coins:
            continue

        amount_now = float(data.get("amount", 0.0))
        cost_usd = float(data.get("cost", 0.0))

        if amount_now <= 0:
            continue

        has_any = True
        invested_usd += cost_usd

        price_now = get_crypto_price(coin_name)

        if price_now is not None:
            LAST_KNOWN_PRICES[coin_name] = price_now
        else:
            price_now = LAST_KNOWN_PRICES.get(coin_name)

        if price_now is None:
            has_missing_price = True
            continue

        value_usd += amount_now * price_now

    pnl_usd = value_usd - invested_usd
    pnl_pct = (pnl_usd / invested_usd * 100) if invested_usd > 0 else 0.0

    return {
        "has_any": has_any,
        "has_missing_price": has_missing_price,
        "invested_usd": invested_usd,
        "value_usd": value_usd,
        "pnl_usd": pnl_usd,
        "pnl_pct": pnl_pct,
        "invested_czk": invested_usd * usdczk,
        "value_czk": value_usd * usdczk,
        "pnl_czk": pnl_usd * usdczk,
    }


# =========================================================
# HEADER
# =========================================================
st.markdown('<div class="app-title">🪙 Crypto Tracker</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-subtitle">Přehled krypta, nákupů, aktuálních cen a vývoje portfolia.</div>',
    unsafe_allow_html=True,
)


# =========================================================
# LOAD DATA + BUILD SUMMARY
# =========================================================
df = load_data()
usdczk = get_usdczk()
portfolio = build_portfolio(df)

rows = []
total_cost = sum(v["cost"] for v in portfolio.values())
total_value = 0.0
unavailable_prices = []

for coin_name, data in portfolio.items():
    amount_now = float(data["amount"])
    cost_usd = float(data["cost"])

    if amount_now <= 0:
        continue

    price_now = get_crypto_price(coin_name)

    if price_now is not None:
        LAST_KNOWN_PRICES[coin_name] = price_now
    else:
        price_now = LAST_KNOWN_PRICES.get(coin_name)

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

    rows.append(
        {
            "coin": pretty_coin_name(coin_name),
            "ticker": pretty_coin_ticker(coin_name),
            "amount": amount_now,
            "avg_buy_price_usd": (cost_usd / amount_now) if amount_now > 0 else 0.0,
            "current_price_usd": price_now,
            "value_usd": value_usd,
            "pnl_usd": pnl_usd,
            "pnl_pct": pnl_pct,
        }
    )

portfolio_df = pd.DataFrame(rows)

total_pnl = total_value - total_cost
value_czk = total_value * usdczk
invested_czk = total_cost * usdczk
pnl_czk = total_pnl * usdczk
pnl_pct_total = (total_pnl / total_cost * 100) if total_cost > 0 else 0.0

main_summary = summarize_portfolio_group(portfolio, MAIN_COINS)
dot_summary = summarize_portfolio_group(portfolio, {DOT_COIN})


# =========================================================
# REFRESH BUTTON
# =========================================================
col_refresh, col_spacer = st.columns([1, 4])

with col_refresh:
    if st.button("🔄 Aktualizovat ceny teď", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# =========================================================
# TOP SUMMARY
# =========================================================
st.caption(f"Aktuální kurz: 1 USD = {usdczk:.2f} CZK")

st.markdown('<div class="section-title">Hlavní portfolio (BTC + ETH + SOL)</div>', unsafe_allow_html=True)
g1, g2, g3 = st.columns(3)
with g1:
    render_summary_card(
        "Investováno",
        format_czk(main_summary["invested_czk"]),
        format_usd(main_summary["invested_usd"]),
    )
with g2:
    render_summary_card(
        "Aktuální hodnota",
        format_czk(main_summary["value_czk"]),
        format_usd(main_summary["value_usd"]),
    )
with g3:
    render_summary_card(
        "Zisk / ztráta",
        format_czk(main_summary["pnl_czk"]),
        format_usd(main_summary["pnl_usd"]),
        f'{main_summary["pnl_pct"]:+.2f} %',
        positive=main_summary["pnl_czk"] >= 0,
    )

st.markdown("")
st.markdown('<div class="section-title">Polkadot</div>', unsafe_allow_html=True)
d1, d2, d3 = st.columns(3)
with d1:
    render_summary_card(
        "Investováno",
        format_czk(dot_summary["invested_czk"]),
        format_usd(dot_summary["invested_usd"]),
    )
with d2:
    render_summary_card(
        "Aktuální hodnota",
        format_czk(dot_summary["value_czk"]),
        format_usd(dot_summary["value_usd"]),
    )
with d3:
    render_summary_card(
        "Zisk / ztráta",
        format_czk(dot_summary["pnl_czk"]),
        format_usd(dot_summary["pnl_usd"]),
        f'{dot_summary["pnl_pct"]:+.2f} %',
        positive=dot_summary["pnl_czk"] >= 0,
    )

st.markdown("")
st.markdown('<div class="section-title">Celkem portfolio</div>', unsafe_allow_html=True)
m1, m2, m3 = st.columns(3)
with m1:
    render_summary_card(
        "Investováno",
        format_czk(invested_czk),
        format_usd(total_cost),
    )
with m2:
    render_summary_card(
        "Aktuální hodnota",
        format_czk(value_czk),
        format_usd(total_value),
    )
with m3:
    render_summary_card(
        "Zisk / ztráta",
        format_czk(pnl_czk),
        format_usd(total_pnl),
        f"{pnl_pct_total:+.2f} %",
        positive=pnl_czk >= 0,
    )

if unavailable_prices:
    st.warning("Dočasně se nepodařilo načíst cenu pro: " + ", ".join(sorted(set(unavailable_prices))))

st.markdown("")


# =========================================================
# COIN CARDS
# =========================================================
if not portfolio_df.empty:
    st.markdown('<div class="section-title">Portfolio coins</div>', unsafe_allow_html=True)

    coins_for_cards = portfolio_df.sort_values("value_usd", ascending=False, na_position="last").reset_index(drop=True)

    for _, row in coins_for_cards.iterrows():
        render_coin_card(row)

    st.markdown("")
else:
    st.info("Zatím tu nejsou žádné kryptotransakce.")


# =========================================================
# FORM + EXPORT
# =========================================================
left, right = st.columns([1.15, 1])

with left:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Přidat nákup</div>', unsafe_allow_html=True)

    with st.form("add_buy_form", clear_on_submit=True):
        f1, f2 = st.columns(2)

        with f1:
            buy_date = st.date_input("Datum", datetime.today())
            coin = st.selectbox("Coin", TRACKED_COINS)

        with f2:
            amount = st.number_input(
                "Množství",
                min_value=0.0,
                value=0.0,
                step=0.00000001,
                format="%.8f",
            )
            price = st.number_input(
                "Cena při nákupu (USD)",
                min_value=0.0,
                value=0.0,
                step=0.01,
                format="%.2f",
            )

        submitted = st.form_submit_button("Přidat nákup", use_container_width=True)

    if submitted:
        new_row = {
            "date": str(buy_date),
            "coin": normalize_coin(coin),
            "amount": float(amount),
            "price": float(price),
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_data(df)
        st.success("Nákup byl uložen.")
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Export dat</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="small-muted">Stáhni si všechny transakce do Excelu.</div>',
        unsafe_allow_html=True,
    )

    excel_file = to_excel(df)
    st.download_button(
        label="📁 Stáhnout transakce do Excelu",
        data=excel_file,
        file_name="crypto_transactions.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# TRANSACTIONS
# =========================================================
st.markdown('<div class="section-title">Transakce</div>', unsafe_allow_html=True)
st.dataframe(format_transactions_df(df), use_container_width=True, hide_index=True)


# =========================================================
# PORTFOLIO TABLE
# =========================================================
if not portfolio_df.empty:
    st.markdown("")
    st.markdown('<div class="section-title">Portfolio detail</div>', unsafe_allow_html=True)
    st.dataframe(format_portfolio_df(portfolio_df), use_container_width=True, hide_index=True)


# =========================================================
# PIE CHART
# =========================================================
if not portfolio_df.empty and PLOTLY_AVAILABLE:
    st.markdown("")
    st.markdown('<div class="section-title">Rozložení portfolia</div>', unsafe_allow_html=True)

    chart_df = portfolio_df.dropna(subset=["value_usd"])[["coin", "value_usd"]]

    if not chart_df.empty:
        fig = px.pie(
            chart_df,
            names="coin",
            values="value_usd",
            hole=0.4,
        )
        fig.update_layout(
            margin=dict(l=10, r=10, t=30, b=10),
            height=380,
        )
        st.plotly_chart(fig, use_container_width=True)