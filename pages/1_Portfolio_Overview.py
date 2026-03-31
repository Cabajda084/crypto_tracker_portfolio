import json
import streamlit as st
import pandas as pd
import requests

from invest_service import get_portfolio_overview_payload, fmt_czk
from invest_stock_service import get_stock_portfolio_summary

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
PRICE_CACHE_FILE = "crypto_price_cache.json"
TRACKED_COINS = ["bitcoin", "ethereum", "solana", "polkadot"]

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


def inject_css():
    st.markdown(
        """
        <style>
        [data-testid="stHeader"] {
            display: none;
        }

        [data-testid="stToolbar"] {
            display: none;
        }

        #MainMenu {
            visibility: hidden;
        }

        footer {
            visibility: hidden;
        }

        .block-container {
            max-width: 1280px;
            padding-top: 0.9rem;
            padding-bottom: 6rem;
            padding-left: 0.9rem;
            padding-right: 0.9rem;
        }

        .nav-row {
            margin-bottom: 0.65rem;
        }

        .nav-row div[data-testid="stButton"] > button {
            min-height: 42px;
            border-radius: 14px;
            background: #ffffff;
            color: #111827;
            border: 1px solid #e5e7eb;
            box-shadow: none;
            font-size: 0.9rem;
            white-space: nowrap;
            margin-bottom: 0.2rem;
        }

        .page-hero {
            background: linear-gradient(135deg, #312e81 0%, #4338ca 55%, #7c3aed 100%);
            border-radius: 28px;
            padding: 24px 22px;
            color: white;
            box-shadow: 0 16px 40px rgba(67, 56, 202, 0.18);
            margin-bottom: 1rem;
        }

        .page-badge {
            display: inline-block;
            background: rgba(255, 255, 255, 0.14);
            border: 1px solid rgba(255, 255, 255, 0.16);
            color: white;
            border-radius: 999px;
            padding: 6px 12px;
            font-size: 0.78rem;
            font-weight: 700;
            margin-bottom: 0.8rem;
        }

        .page-title {
            font-size: 2.1rem;
            line-height: 1.02;
            font-weight: 800;
            margin-bottom: 0.45rem;
        }

        .page-subtitle {
            color: rgba(255, 255, 255, 0.92);
            font-size: 0.98rem;
            line-height: 1.5;
        }

        .hero-card,
        .summary-card,
        .tracker-card,
        .asset-card {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 24px;
            box-shadow: 0 8px 30px rgba(15, 23, 42, 0.05);
        }

        .hero-card {
            padding: 24px 24px;
            margin-bottom: 1rem;
            background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%);
        }

        .hero-single {
            margin-bottom: 0.9rem;
        }

        .hero-metric {
            background: #ffffff;
            border: 1px solid #eceff3;
            border-radius: 20px;
            padding: 16px 18px;
        }

        .hero-label {
            font-size: 0.88rem;
            color: #6b7280;
            margin-bottom: 0.42rem;
            font-weight: 700;
        }

        .hero-value {
            font-size: 2.25rem;
            line-height: 1.05;
            font-weight: 800;
            color: #111827;
            margin-bottom: 0.15rem;
        }

        .hero-subvalue {
            color: #6b7280;
            font-size: 0.9rem;
            line-height: 1.4;
        }

        .hero-result {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            align-items: center;
            justify-content: space-between;
            background: #ffffff;
            border: 1px solid #eceff3;
            border-radius: 20px;
            padding: 15px 18px;
        }

        .hero-result-left {
            color: #6b7280;
            font-size: 0.94rem;
        }

        .hero-result-title {
            color: #111827;
            font-size: 0.95rem;
            font-weight: 800;
            margin-bottom: 0.2rem;
        }

        .summary-card {
            padding: 18px 18px;
            height: 100%;
            margin-bottom: 0.8rem;
        }

        .summary-label {
            color: #6b7280;
            font-size: 0.88rem;
            margin-bottom: 0.45rem;
            font-weight: 600;
        }

        .summary-value {
            color: #111827;
            font-size: 1.75rem;
            line-height: 1.08;
            font-weight: 800;
            margin-bottom: 0.3rem;
        }

        .summary-meta {
            color: #6b7280;
            font-size: 0.9rem;
            line-height: 1.4;
        }

        .tracker-card {
            padding: 20px 20px 16px 20px;
            margin-top: 0.35rem;
            margin-bottom: 1rem;
        }

        .tracker-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 16px;
            margin-bottom: 0.9rem;
        }

        .tracker-title {
            font-size: 1.16rem;
            font-weight: 800;
            color: #111827;
            margin-bottom: 0.16rem;
        }

        .tracker-desc {
            color: #6b7280;
            font-size: 0.93rem;
            line-height: 1.45;
        }

        .section-spacer {
            height: 0.2rem;
        }

        .asset-card {
            padding: 15px 16px;
            margin-bottom: 0.72rem;
            background: linear-gradient(180deg, #ffffff 0%, #fbfbfb 100%);
        }

        .asset-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 14px;
        }

        .asset-title {
            color: #111827;
            font-size: 1rem;
            font-weight: 800;
            margin-bottom: 0.22rem;
        }

        .asset-sub {
            color: #6b7280;
            font-size: 0.89rem;
            line-height: 1.4;
        }

        .asset-value {
            color: #111827;
            font-size: 1.2rem;
            font-weight: 800;
            text-align: right;
            line-height: 1.12;
        }

        .asset-pnl {
            font-size: 0.9rem;
            text-align: right;
            margin-top: 0.2rem;
        }

        .pill-positive,
        .pill-negative,
        .pill-neutral {
            display: inline-block;
            padding: 0.28rem 0.6rem;
            border-radius: 999px;
            font-size: 0.84rem;
            font-weight: 700;
        }

        .pill-positive {
            color: #166534;
            background: #dcfce7;
        }

        .pill-negative {
            color: #991b1b;
            background: #fee2e2;
        }

        .pill-neutral {
            color: #374151;
            background: #f3f4f6;
        }

        .small-gap {
            height: 0.18rem;
        }

        @media (max-width: 768px) {
            .block-container {
                padding-top: 0.75rem;
                padding-left: 0.8rem;
                padding-right: 0.8rem;
                padding-bottom: 6.5rem;
            }

            .page-hero,
            .hero-card,
            .summary-card,
            .tracker-card,
            .asset-card {
                border-radius: 20px;
            }

            .page-hero {
                padding: 18px 16px;
                margin-bottom: 0.85rem;
            }

            .page-title {
                font-size: 1.7rem;
            }

            .page-subtitle {
                font-size: 0.94rem;
            }

            .hero-card {
                padding: 18px 16px;
            }

            .hero-value {
                font-size: 1.95rem;
            }

            .summary-value {
                font-size: 1.45rem;
            }

            .tracker-header,
            .asset-top {
                display: block;
            }

            .asset-value,
            .asset-pnl {
                text-align: left;
                margin-top: 0.5rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_summary_card(title: str, value: str, meta: str = ""):
    st.markdown(
        f"""
        <div class="summary-card">
            <div class="summary-label">{title}</div>
            <div class="summary-value">{value}</div>
            <div class="summary-meta">{meta}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_asset_card(title: str, subtitle: str, value: str, pnl_text: str = "", pnl_positive=None):
    if pnl_positive is True:
        pill_class = "pill-positive"
    elif pnl_positive is False:
        pill_class = "pill-negative"
    else:
        pill_class = "pill-neutral"

    pnl_html = f'<span class="{pill_class}">{pnl_text}</span>' if pnl_text else ""

    st.markdown(
        f"""
        <div class="asset-card">
            <div class="asset-top">
                <div>
                    <div class="asset-title">{title}</div>
                    <div class="asset-sub">{subtitle}</div>
                </div>
                <div>
                    <div class="asset-value">{value}</div>
                    <div class="asset-pnl">{pnl_html}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
        "dot": "polkadot",
        "polkadot": "polkadot",
    }
    return mapping.get(c, c)


def load_price_cache() -> dict:
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


def save_price_cache(cache: dict) -> None:
    try:
        with open(PRICE_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def safe_get_json(url: str, params: dict = None, timeout: int = 10):
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


def get_price_from_coingecko(coin_id: str):
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


def get_price_from_binance(coin_id: str):
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


def get_price_from_coinbase(coin_id: str):
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


def get_price_from_kraken(coin_id: str):
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


def load_data() -> pd.DataFrame:
    try:
        df = pd.read_csv(DATA_FILE)
        for col in ["date", "coin", "amount", "price"]:
            if col not in df.columns:
                df[col] = None
        return df[["date", "coin", "amount", "price"]]
    except Exception:
        return pd.DataFrame(columns=["date", "coin", "amount", "price"])


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


@st.cache_data(ttl=45)
def get_crypto_price(coin: str):
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


def resolve_price_with_fallback(coin_name: str, amount_now: float = 0.0, cost_usd: float = 0.0):
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


def get_coin_metrics(portfolio: dict, usdczk: float):
    metrics = {}
    unavailable_prices = []

    for coin in TRACKED_COINS:
        data = portfolio.get(coin, {"amount": 0.0, "cost": 0.0, "avg_buy_price": 0.0})
        amount = float(data["amount"])
        cost_usd = float(data["cost"])
        avg_buy_price = float(data["avg_buy_price"])

        price_now = resolve_price_with_fallback(
            coin_name=coin,
            amount_now=amount,
            cost_usd=cost_usd,
        )

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
    try:
        summary = get_investown_summary() or {}
        projects = get_investown_projects() or []

        invested_total = float(summary.get("invested", 0.0) or 0.0)
        paid_out_total = float(summary.get("paid_out", 0.0) or 0.0)
        profit_total = float(summary.get("profit", 0.0) or 0.0)

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


inject_css()
LAST_KNOWN_PRICES.update(load_price_cache())

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

st.markdown('<div class="nav-row">', unsafe_allow_html=True)

nav1, nav2, nav3 = st.columns([1, 1, 4])

with nav1:
    if st.button("← Domů"):
        st.switch_page("Start.py")

with nav2:
    if st.button("Odhlásit se"):
        st.session_state.authenticated = False
        st.switch_page("Start.py")

st.markdown('</div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="page-hero">
        <div class="page-badge">PŘEHLED</div>
        <div class="page-title">Moje portfolio</div>
        <div class="page-subtitle">
            Jednoduchý přehled toho, kolik je celkem investováno, kolik má portfolio teď hodnotu a jak si vede.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

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
invest_total_value_czk_base = float(invest_summary.get("total_value_czk", 0.0) or 0.0)
invest_positions_value_czk_base = float(invest_summary.get("positions_value_czk", 0.0) or 0.0)
invest_cash_balance_czk = float(invest_summary.get("cash_balance_czk", 0.0) or 0.0)
invest_total_cost_czk_base = float(invest_summary.get("invested_amount_czk", 0.0) or 0.0)
invest_total_pnl_czk_base = float(invest_summary.get("profit_loss_czk", 0.0) or 0.0)
invest_plans = invest_summary.get("plans", [])

# =========================================================
# STOCKS / MY TRADES SUMMARY (SAFE ADDITIVE)
# =========================================================
try:
    stock_summary = get_stock_portfolio_summary() or {}
except Exception:
    stock_summary = {}

stock_positions = stock_summary.get("positions", []) or []
stock_positions_count = int(stock_summary.get("positions_count", 0) or 0)
stock_total_cost_czk = float(stock_summary.get("total_cost_basis", 0.0) or 0.0)
stock_total_value_czk = float(stock_summary.get("total_market_value", 0.0) or 0.0)
stock_total_pnl_czk = float(stock_summary.get("total_unrealized_pnl", 0.0) or 0.0)
stock_total_pnl_pct = (
    (stock_total_pnl_czk / stock_total_cost_czk) * 100
    if stock_total_cost_czk > 0 else 0.0
)

invest_positions_value_czk = invest_positions_value_czk_base + stock_total_value_czk
invest_total_cost_czk = invest_total_cost_czk_base + stock_total_cost_czk
invest_total_pnl_czk = invest_total_pnl_czk_base + stock_total_pnl_czk
invest_total_value_czk = invest_total_value_czk_base + stock_total_value_czk
invest_total_pnl_pct = (
    (invest_total_pnl_czk / invest_total_cost_czk) * 100
    if invest_total_cost_czk > 0 else 0.0
)

# =========================================================
# INVESTOWN SUMMARY
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

profit_class = "pill-positive" if total_pnl_czk >= 0 else "pill-negative"

# =========================================================
# HERO - ONLY TOTAL INVESTED
# =========================================================
st.markdown(
    f"""
    <div class="hero-card">
        <div class="hero-single">
            <div class="hero-metric">
                <div class="hero-label">Celkem investováno</div>
                <div class="hero-value">{fmt_czk(total_invested_czk)}</div>
                <div class="hero-subvalue">Všechny vložené prostředky dohromady</div>
            </div>
        </div>
        <div class="hero-result">
            <div class="hero-result-left">
                <div class="hero-result-title">Celkový výsledek</div>
                <div>Rozdíl mezi investovanou částkou a aktuální hodnotou</div>
            </div>
            <div>
                <span class="{profit_class}">{fmt_czk(total_pnl_czk)} · {total_pnl_pct_all:+.2f}%</span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# TOP SUMMARY CARDS
# =========================================================
top1, top2, top3 = st.columns(3)

with top1:
    render_summary_card(
        "Kryptoměny",
        fmt_czk(crypto_total_value_czk),
        f"Investováno {fmt_czk(crypto_total_cost_czk)} · Výsledek {fmt_czk(crypto_total_pnl_czk)} · {total_pnl_pct:+.2f}%",
    )

with top2:
    render_summary_card(
        "XTB + My Trades",
        fmt_czk(invest_total_value_czk),
        f"Investováno {fmt_czk(invest_total_cost_czk)} · Výsledek {fmt_czk(invest_total_pnl_czk)} · {invest_total_pnl_pct:+.2f}%",
    )

with top3:
    render_summary_card(
        "Investown",
        fmt_czk(investown_total_value_czk),
        f"Investováno {fmt_czk(investown_total_cost_czk)} · Výsledek {fmt_czk(investown_total_pnl_czk)} · {investown_total_pnl_pct:+.2f}%",
    )

# =========================================================
# SECONDARY SUMMARY - CURRENT VALUE MOVED LOWER
# =========================================================
sub1, sub2, sub3 = st.columns(3)

with sub1:
    render_summary_card("Aktuální hodnota", fmt_czk(net_worth_czk), "Součet všech částí portfolia")

with sub2:
    render_summary_card("Celkový výsledek", fmt_czk(total_pnl_czk), f"{total_pnl_pct_all:+.2f}%")

with sub3:
    render_summary_card("Kurz USD/CZK", f"{usdczk:.2f}", "Použitý kurz pro přepočet")

st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

# =========================================================
# CRYPTO
# =========================================================
st.markdown('<div class="tracker-card">', unsafe_allow_html=True)
st.markdown(
    """
    <div class="tracker-header">
        <div>
            <div class="tracker-title">Kryptoměny</div>
            <div class="tracker-desc">Přehled kryptoměnové části portfolia</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns(3)
with c1:
    render_summary_card("Investováno", format_usd(total_cost_usd), format_czk_crypto(total_cost_usd * usdczk))
with c2:
    render_summary_card("Aktuální hodnota", format_usd(total_value_usd), format_czk_crypto(total_value_usd * usdczk))
with c3:
    render_summary_card("Výsledek", format_usd(total_pnl_usd), f"{total_pnl_pct:+.2f}%")

if unavailable_prices:
    st.warning("Dočasně se nepodařilo načíst cenu pro: " + ", ".join(unavailable_prices))

st.markdown('<div class="small-gap"></div>', unsafe_allow_html=True)

for coin in TRACKED_COINS:
    m = coin_metrics[coin]
    render_asset_card(
        title=f"{pretty_coin_name(coin)} ({pretty_coin_ticker(coin)})",
        subtitle=f"Množství: {format_amount(m['amount'])}",
        value=format_usd(m["value_usd"]),
        pnl_text=(
            f"{m['pnl_pct']:+.2f}%"
            if m["pnl_pct"] is not None
            else "Cena nedostupná"
        ),
        pnl_positive=(m["pnl_pct"] >= 0) if m["pnl_pct"] is not None else None,
    )

st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# XTB
# =========================================================
st.markdown('<div class="tracker-card">', unsafe_allow_html=True)
st.markdown(
    """
    <div class="tracker-header">
        <div>
            <div class="tracker-title">XTB</div>
            <div class="tracker-desc">Přehled investičních plánů XTB</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

x1, x2, x3 = st.columns(3)
with x1:
    render_summary_card("Hodnota pozic", fmt_czk(invest_positions_value_czk_base), "Aktuální hodnota plánů")
with x2:
    render_summary_card("Cash rezerva", fmt_czk(invest_cash_balance_czk), "Volná hotovost v plánech")
with x3:
    render_summary_card(
        "Celkem XTB",
        fmt_czk(invest_total_value_czk_base),
        f"Výsledek {((invest_total_pnl_czk_base / invest_total_cost_czk_base) * 100 if invest_total_cost_czk_base > 0 else 0.0):+.2f}%",
    )

st.markdown('<div class="small-gap"></div>', unsafe_allow_html=True)

if not invest_plans:
    st.info("Zatím tu nejsou žádné aktivní investiční plány.")
else:
    for plan in invest_plans:
        pnl_positive = plan["profit_loss"] >= 0
        render_asset_card(
            title=f"{plan['icon']} {plan['display_name']}",
            subtitle=f"Pozice: {fmt_czk(plan['positions_value'])} · Cash: {fmt_czk(plan['cash_balance'])}",
            value=fmt_czk(plan["portfolio_value"]),
            pnl_text=f"{plan['profit_loss_pct']:+.2f}%",
            pnl_positive=pnl_positive,
        )

st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# MY TRADES
# =========================================================
st.markdown('<div class="tracker-card">', unsafe_allow_html=True)
st.markdown(
    """
    <div class="tracker-header">
        <div>
            <div class="tracker-title">My Trades</div>
            <div class="tracker-desc">Přehled akciových obchodů a otevřených pozic</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

m1, m2, m3 = st.columns(3)
with m1:
    render_summary_card("Investováno", fmt_czk(stock_total_cost_czk), "Celkový cost basis")
with m2:
    render_summary_card("Aktuální hodnota", fmt_czk(stock_total_value_czk), "Součet otevřených pozic")
with m3:
    render_summary_card("Výsledek", fmt_czk(stock_total_pnl_czk), f"{stock_total_pnl_pct:+.2f}%")

st.markdown('<div class="small-gap"></div>', unsafe_allow_html=True)

if stock_positions_count == 0:
    st.info("Zatím tu nejsou žádné My Trades akcie.")
else:
    render_asset_card(
        title="📊 My Trades akcie",
        subtitle=f"Pozice: {stock_positions_count} · Investováno: {fmt_czk(stock_total_cost_czk)}",
        value=fmt_czk(stock_total_value_czk),
        pnl_text=f"{stock_total_pnl_pct:+.2f}%",
        pnl_positive=stock_total_pnl_czk >= 0,
    )

    for position in stock_positions:
        qty = float(position.get("quantity_open", 0.0) or 0.0)
        title = f"{position.get('name', position.get('ticker', 'Akcie'))} ({position.get('ticker', '')})"
        subtitle = f"Množství: {f'{qty:.4f}'.rstrip('0').rstrip('.')} · Měna: {position.get('currency', 'N/A')}"
        render_asset_card(
            title=title,
            subtitle=subtitle,
            value=fmt_czk(float(position.get("market_value", 0.0) or 0.0)),
            pnl_text=fmt_czk(float(position.get("unrealized_pnl", 0.0) or 0.0)),
            pnl_positive=float(position.get("unrealized_pnl", 0.0) or 0.0) >= 0,
        )

st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# INVESTOWN
# =========================================================
st.markdown('<div class="tracker-card">', unsafe_allow_html=True)
st.markdown(
    """
    <div class="tracker-header">
        <div>
            <div class="tracker-title">Investown</div>
            <div class="tracker-desc">Přehled Investown projektů na jednom místě</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

j1, j2, j3, j4 = st.columns(4)
with j1:
    render_summary_card("Hodnota portfolia", fmt_czk(investown_total_value_czk), "Aktuální konzervativní ocenění")
with j2:
    render_summary_card("Celkem vloženo", fmt_czk(investown_total_cost_czk), "Součet investovaných prostředků")
with j3:
    render_summary_card("Vyplaceno", fmt_czk(investown_paid_out_czk), "Dosud vyplacené prostředky")
with j4:
    render_summary_card("Počet projektů", str(investown_projects_count), "Aktivní projekty v přehledu")

if not INVESTOWN_AVAILABLE:
    st.info("Investown data teď nejsou dostupná.")
elif investown_projects_count == 0:
    st.info("Zatím tu nejsou žádné Investown projekty.")
else:
    render_asset_card(
        title="Souhrnný výsledek Investown",
        subtitle="Celkový výkon všech Investown projektů",
        value=fmt_czk(investown_total_pnl_czk),
        pnl_text=f"{investown_total_pnl_pct:+.2f}%",
        pnl_positive=investown_total_pnl_czk >= 0,
    )

st.markdown("</div>", unsafe_allow_html=True)