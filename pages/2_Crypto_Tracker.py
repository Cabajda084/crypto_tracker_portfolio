import json
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
PRICE_CACHE_FILE = "crypto_price_cache.json"
TRACKED_COINS = ["bitcoin", "ethereum", "solana", "polkadot"]
MAIN_COINS = {"bitcoin", "ethereum", "solana"}
DOT_COIN = "polkadot"
LAST_KNOWN_PRICES = {}

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (MyPortfolio/1.0; Streamlit)",
    "Accept": "application/json",
}

BINANCE_SYMBOL_MAP = {
    "bitcoin": "BTCUSDT",
    "ethereum": "ETHUSDT",
    "solana": "SOLUSDT",
    "polkadot": "DOTUSDT",
}

KRAKEN_PAIR_MAP = {
    "bitcoin": "XBTUSD",
    "ethereum": "ETHUSD",
    "solana": "SOLUSD",
    "polkadot": "DOTUSD",
}

COINBASE_SYMBOL_MAP = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL",
    "polkadot": "DOT",
}


def normalize_coin(coin):
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


def load_price_cache():
    try:
        with open(PRICE_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            clean = {}
            for key, value in data.items():
                try:
                    clean[normalize_coin(str(key))] = float(value)
                except Exception:
                    continue
            return clean
    except Exception:
        pass
    return {}


def save_price_cache(cache):
    try:
        with open(PRICE_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def safe_get_json(url, params=None, timeout=10):
    try:
        r = requests.get(
            url,
            params=params,
            headers=REQUEST_HEADERS,
            timeout=timeout,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def get_price_from_coingecko(coin_id):
    data = safe_get_json(
        "https://api.coingecko.com/api/v3/simple/price",
        params={"ids": coin_id, "vs_currencies": "usd"},
        timeout=10,
    )
    if isinstance(data, dict) and coin_id in data and "usd" in data[coin_id]:
        try:
            return float(data[coin_id]["usd"])
        except Exception:
            pass
    return None


def get_price_from_binance(coin_id):
    symbol = BINANCE_SYMBOL_MAP.get(coin_id)
    if not symbol:
        return None

    endpoints = [
        "https://api.binance.com/api/v3/ticker/price",
        "https://api-gcp.binance.com/api/v3/ticker/price",
        "https://api1.binance.com/api/v3/ticker/price",
        "https://api2.binance.com/api/v3/ticker/price",
        "https://api3.binance.com/api/v3/ticker/price",
        "https://api4.binance.com/api/v3/ticker/price",
    ]

    for endpoint in endpoints:
        data = safe_get_json(endpoint, params={"symbol": symbol}, timeout=8)
        if isinstance(data, dict) and "price" in data:
            try:
                return float(data["price"])
            except Exception:
                continue

    return None


def get_price_from_coinbase(coin_id):
    symbol = COINBASE_SYMBOL_MAP.get(coin_id)
    if not symbol:
        return None

    data = safe_get_json(
        "https://api.coinbase.com/v2/exchange-rates",
        params={"currency": symbol},
        timeout=10,
    )
    try:
        return float(data["data"]["rates"]["USD"])
    except Exception:
        return None


def get_price_from_kraken(coin_id):
    pair = KRAKEN_PAIR_MAP.get(coin_id)
    if not pair:
        return None

    data = safe_get_json(
        "https://api.kraken.com/0/public/Ticker",
        params={"pair": pair},
        timeout=10,
    )

    try:
        result = data.get("result", {})
        if not isinstance(result, dict):
            return None

        for _, pair_data in result.items():
            if isinstance(pair_data, dict) and "c" in pair_data and pair_data["c"]:
                return float(pair_data["c"][0])
    except Exception:
        pass

    return None


def resolve_price_with_fallback(coin_name, amount_now=0.0, cost_usd=0.0):
    price_now = get_crypto_price(coin_name)

    if price_now is not None:
        LAST_KNOWN_PRICES[coin_name] = float(price_now)
        save_price_cache(LAST_KNOWN_PRICES)
        return float(price_now)

    cached_price = LAST_KNOWN_PRICES.get(coin_name)
    if cached_price is not None:
        return float(cached_price)

    if amount_now > 0 and cost_usd > 0:
        return float(cost_usd / amount_now)

    return None


st.set_page_config(
    page_title="Crypto Tracker",
    page_icon="🪙",
    layout="wide",
    initial_sidebar_state="collapsed",
)


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

        .summary-card, .coin-card, .section-card, .transaction-card {
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

        .transaction-card {
            padding: 12px 14px;
            margin-bottom: 10px;
        }

        .transaction-title {
            font-size: 0.96rem;
            font-weight: 800;
            color: #111827;
            margin-bottom: 4px;
        }

        .transaction-sub {
            color: #6b7280;
            font-size: 0.9rem;
            line-height: 1.35;
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

            .summary-card, .coin-card, .section-card, .transaction-card {
                padding: 14px 14px;
                border-radius: 16px;
            }

            .summary-value {
                font-size: 1.25rem;
            }

            .coin-name {
                font-size: 1rem;
            }

            .coin-value {
                font-size: 1.05rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_css()
LAST_KNOWN_PRICES.update(load_price_cache())

if "crypto_edit_index" not in st.session_state:
    st.session_state.crypto_edit_index = None


def load_data():
    try:
        df = pd.read_csv(DATA_FILE)
        for col in ["date", "coin", "amount", "price"]:
            if col not in df.columns:
                df[col] = None
        return df[["date", "coin", "amount", "price"]]
    except Exception:
        return pd.DataFrame(columns=["date", "coin", "amount", "price"])


def save_data(df):
    df.to_csv(DATA_FILE, index=False)


def pretty_coin_name(coin):
    mapping = {
        "bitcoin": "Bitcoin",
        "ethereum": "Ethereum",
        "solana": "Solana",
        "polkadot": "Polkadot",
    }
    return mapping.get(coin, coin.title())


def pretty_coin_ticker(coin):
    mapping = {
        "bitcoin": "BTC",
        "ethereum": "ETH",
        "solana": "SOL",
        "polkadot": "DOT",
    }
    return mapping.get(coin, coin.upper())


def format_czk(value):
    return f"{value:,.2f} CZK".replace(",", " ")


def format_usd(value):
    if value is None or pd.isna(value):
        return "N/A"
    return f"${value:,.2f}"


def format_amount_exact(value):
    try:
        return f"{float(value):.8f}".rstrip("0").rstrip(".")
    except Exception:
        return "0"


def render_summary_card(label, value_main, value_sub=None, delta=None, positive=True):
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


def render_coin_card(row):
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
                    <div class="coin-name">{row['coin']}</div>
                    <div class="coin-ticker">{row['ticker']} · {format_amount_exact(row['amount'])} ks</div>
                </div>
                <div>
                    <div class="coin-value">{value_text}</div>
                </div>
            </div>
            <div class="coin-sub">Průměrný nákup: {format_usd(row['avg_buy_price_usd'])} · Aktuální cena: {current_price_text}</div>
            <div class="{pnl_class}">{pnl_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=45)
def get_crypto_price(coin):
    coin_id = normalize_coin(coin)
    providers = [
        get_price_from_coingecko,
        get_price_from_binance,
        get_price_from_coinbase,
        get_price_from_kraken,
    ]
    for provider in providers:
        try:
            price = provider(coin_id)
            if price is not None and price > 0:
                return float(price)
        except Exception:
            continue
    return None


@st.cache_data(ttl=1800)
def get_usdczk():
    data = safe_get_json("https://open.er-api.com/v6/latest/USD", timeout=12)
    try:
        return float(data["rates"]["CZK"])
    except Exception:
        pass

    data = safe_get_json("https://api.exchangerate-api.com/v4/latest/USD", timeout=12)
    try:
        return float(data["rates"]["CZK"])
    except Exception:
        pass

    data = safe_get_json(
        "https://api.frankfurter.dev/v1/latest",
        params={"base": "EUR", "symbols": "CZK,USD"},
        timeout=12,
    )
    try:
        eur_to_czk = float(data["rates"]["CZK"])
        eur_to_usd = float(data["rates"]["USD"])
        if eur_to_usd > 0:
            return eur_to_czk / eur_to_usd
    except Exception:
        pass

    return 23.0


def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Transactions")
    return output.getvalue()


def build_portfolio(df):
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


def format_transactions_df(df):
    out = df.copy()
    if out.empty:
        return out

    out["date"] = out["date"].astype(str)
    out["coin"] = out["coin"].astype(str)
    out["amount"] = pd.to_numeric(out["amount"], errors="coerce").apply(format_amount_exact)
    out["price"] = pd.to_numeric(out["price"], errors="coerce").apply(lambda x: f"{x:.2f}" if pd.notna(x) else "")
    return out


def format_portfolio_df(df):
    out = df.copy()
    if out.empty:
        return out

    out["amount"] = pd.to_numeric(out["amount"], errors="coerce").apply(format_amount_exact)
    for col in ["avg_buy_price_usd", "current_price_usd", "value_usd", "pnl_usd", "pnl_pct"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def summarize_portfolio_group(portfolio, include_coins):
    invested_usd = 0.0
    value_usd = 0.0
    for coin_name, data in portfolio.items():
        if coin_name not in include_coins:
            continue
        amount_now = float(data.get("amount", 0.0))
        cost_usd = float(data.get("cost", 0.0))
        if amount_now <= 0:
            continue
        invested_usd += cost_usd
        price_now = resolve_price_with_fallback(coin_name=coin_name, amount_now=amount_now, cost_usd=cost_usd)
        if price_now is not None:
            value_usd += amount_now * price_now
    pnl_usd = value_usd - invested_usd
    pnl_pct = (pnl_usd / invested_usd * 100) if invested_usd > 0 else 0.0
    return {
        "invested_usd": invested_usd,
        "value_usd": value_usd,
        "pnl_usd": pnl_usd,
        "pnl_pct": pnl_pct,
        "invested_czk": invested_usd * usdczk,
        "value_czk": value_usd * usdczk,
        "pnl_czk": pnl_usd * usdczk,
    }


def render_transaction_editor(df):
    if df.empty:
        st.info("Zatím tu nejsou žádné transakce k úpravě.")
        return

    formatted_df = format_transactions_df(df)

    for idx, row in formatted_df.sort_index(ascending=False).iterrows():
        row_left, row_right = st.columns([5, 1])
        with row_left:
            st.markdown(
                f"""
                <div class="transaction-card">
                    <div class="transaction-title">{pretty_coin_name(normalize_coin(row['coin']))}</div>
                    <div class="transaction-sub">Datum: {row['date']}<br>Množství: {row['amount']}<br>Cena: {row['price']} USD</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with row_right:
            if st.button("Upravit", key=f"edit_tx_{idx}", use_container_width=True):
                st.session_state.crypto_edit_index = int(idx)

    edit_index = st.session_state.crypto_edit_index
    if edit_index is None or edit_index not in df.index:
        return

    edit_row = df.loc[edit_index]
    try:
        default_date = pd.to_datetime(edit_row["date"]).date()
    except Exception:
        default_date = datetime.today().date()

    default_coin = normalize_coin(str(edit_row.get("coin", TRACKED_COINS[0])))
    if default_coin not in TRACKED_COINS:
        default_coin = TRACKED_COINS[0]

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Upravit vybraný nákup</div>', unsafe_allow_html=True)
    with st.form("edit_buy_form"):
        e1, e2 = st.columns(2)
        with e1:
            edit_date = st.date_input("Datum", value=default_date)
            edit_coin = st.selectbox("Coin", TRACKED_COINS, index=TRACKED_COINS.index(default_coin))
        with e2:
            edit_amount = st.number_input("Množství", min_value=0.0, value=float(edit_row.get("amount", 0.0) or 0.0), step=0.00000001, format="%.8f")
            edit_price = st.number_input("Cena při nákupu (USD)", min_value=0.0, value=float(edit_row.get("price", 0.0) or 0.0), step=0.01, format="%.2f")
        save_edit = st.form_submit_button("Uložit změny", use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Zrušit editaci", key="cancel_edit", use_container_width=True):
            st.session_state.crypto_edit_index = None
            st.rerun()
    with c2:
        if st.button("Smazat transakci", key="delete_tx", use_container_width=True):
            df = df.drop(index=edit_index).reset_index(drop=True)
            save_data(df)
            st.session_state.crypto_edit_index = None
            st.success("Transakce byla smazána.")
            st.rerun()

    if save_edit:
        df.loc[edit_index, "date"] = str(edit_date)
        df.loc[edit_index, "coin"] = normalize_coin(edit_coin)
        df.loc[edit_index, "amount"] = float(edit_amount)
        df.loc[edit_index, "price"] = float(edit_price)
        save_data(df)
        st.session_state.crypto_edit_index = None
        st.success("Transakce byla upravena.")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


st.markdown('<div class="app-title">🪙 Crypto Tracker</div>', unsafe_allow_html=True)
st.markdown('<div class="app-subtitle">Přehled krypta, nákupů, aktuálních cen a vývoje portfolia.</div>', unsafe_allow_html=True)

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
    price_now = resolve_price_with_fallback(coin_name=coin_name, amount_now=amount_now, cost_usd=cost_usd)
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
main_summary = summarize_portfolio_group(portfolio, MAIN_COINS)
dot_summary = summarize_portfolio_group(portfolio, {DOT_COIN})

col_refresh, _ = st.columns([1, 4])
with col_refresh:
    if st.button("🔄 Aktualizovat ceny teď", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.caption(f"Aktuální kurz: 1 USD = {usdczk:.2f} CZK")

with st.expander("Hlavní portfolio (BTC + ETH + SOL)", expanded=True):
    g1, g2, g3 = st.columns(3)
    with g1:
        render_summary_card("Investováno", format_czk(main_summary["invested_czk"]), format_usd(main_summary["invested_usd"]))
    with g2:
        render_summary_card("Aktuální hodnota", format_czk(main_summary["value_czk"]), format_usd(main_summary["value_usd"]))
    with g3:
        render_summary_card("Zisk / ztráta", format_czk(main_summary["pnl_czk"]), format_usd(main_summary["pnl_usd"]), f"{main_summary['pnl_pct']:+.2f} %", positive=main_summary["pnl_czk"] >= 0)

with st.expander("Polkadot", expanded=False):
    d1, d2, d3 = st.columns(3)
    with d1:
        render_summary_card("Investováno", format_czk(dot_summary["invested_czk"]), format_usd(dot_summary["invested_usd"]))
    with d2:
        render_summary_card("Aktuální hodnota", format_czk(dot_summary["value_czk"]), format_usd(dot_summary["value_usd"]))
    with d3:
        render_summary_card("Zisk / ztráta", format_czk(dot_summary["pnl_czk"]), format_usd(dot_summary["pnl_usd"]), f"{dot_summary['pnl_pct']:+.2f} %", positive=dot_summary["pnl_czk"] >= 0)

with st.expander("Celkem portfolio", expanded=True):
    m1, m2, m3 = st.columns(3)
    with m1:
        render_summary_card("Investováno", format_czk(invested_czk), format_usd(total_cost))
    with m2:
        render_summary_card("Aktuální hodnota", format_czk(value_czk), format_usd(total_value))
    with m3:
        render_summary_card("Zisk / ztráta", format_czk(pnl_czk), format_usd(total_pnl), f"{pnl_pct_total:+.2f} %", positive=pnl_czk >= 0)

if unavailable_prices:
    st.warning("Dočasně se nepodařilo načíst cenu pro: " + ", ".join(sorted(set(unavailable_prices))))

with st.expander("Portfolio coins", expanded=False):
    if not portfolio_df.empty:
        coins_for_cards = portfolio_df.sort_values("value_usd", ascending=False, na_position="last").reset_index(drop=True)
        for _, row in coins_for_cards.iterrows():
            render_coin_card(row)
    else:
        st.info("Zatím tu nejsou žádné kryptotransakce.")

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
            amount = st.number_input("Množství", min_value=0.0, value=0.0, step=0.00000001, format="%.8f")
            price = st.number_input("Cena při nákupu (USD)", min_value=0.0, value=0.0, step=0.01, format="%.2f")
        submitted = st.form_submit_button("Přidat nákup", use_container_width=True)
    if submitted:
        new_row = {"date": str(buy_date), "coin": normalize_coin(coin), "amount": float(amount), "price": float(price)}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_data(df)
        st.success("Nákup byl uložen.")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Export dat</div>', unsafe_allow_html=True)
    st.markdown('<div class="small-muted">Stáhni si všechny transakce do Excelu.</div>', unsafe_allow_html=True)
    excel_file = to_excel(df)
    st.download_button(
        label="📁 Stáhnout transakce do Excelu",
        data=excel_file,
        file_name="crypto_transactions.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

with st.expander("Transakce a editace nákupů", expanded=False):
    st.dataframe(format_transactions_df(df), use_container_width=True, hide_index=True)
    render_transaction_editor(df)

if not portfolio_df.empty:
    with st.expander("Portfolio detail", expanded=False):
        st.dataframe(format_portfolio_df(portfolio_df), use_container_width=True, hide_index=True)

if not portfolio_df.empty and PLOTLY_AVAILABLE:
    with st.expander("Rozložení portfolia", expanded=False):
        chart_df = portfolio_df.dropna(subset=["value_usd"])[["coin", "value_usd"]]
        if not chart_df.empty:
            fig = px.pie(chart_df, names="coin", values="value_usd", hole=0.4)
            fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=380)
            st.plotly_chart(fig, use_container_width=True)
