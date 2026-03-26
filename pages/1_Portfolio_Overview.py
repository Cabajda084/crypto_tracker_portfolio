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
TRACKED_COINS = ["bitcoin", "ethereum", "solana"]


def inject_css():
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1380px;
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }

        .app-subtitle {
            color: #6b7280;
            font-size: 0.98rem;
            margin-top: -0.35rem;
            margin-bottom: 1.1rem;
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
            padding: 26px 28px;
            margin-bottom: 1rem;
            background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%);
        }

        .hero-label {
            font-size: 0.9rem;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.5rem;
            font-weight: 700;
        }

        .hero-value {
            font-size: 3rem;
            line-height: 1.05;
            font-weight: 800;
            color: #111827;
            margin-bottom: 0.35rem;
        }

        .hero-subrow {
            display: flex;
            flex-wrap: wrap;
            gap: 14px;
            align-items: center;
            color: #6b7280;
            font-size: 0.98rem;
        }

        .summary-card {
            padding: 18px 20px;
            height: 100%;
            margin-bottom: 0.8rem;
        }

        .summary-label {
            color: #6b7280;
            font-size: 0.9rem;
            margin-bottom: 0.45rem;
            font-weight: 600;
        }

        .summary-value {
            color: #111827;
            font-size: 1.9rem;
            line-height: 1.1;
            font-weight: 800;
            margin-bottom: 0.35rem;
        }

        .summary-meta {
            color: #6b7280;
            font-size: 0.92rem;
        }

        .tracker-card {
            padding: 22px 22px 18px 22px;
            margin-top: 0.4rem;
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
            font-size: 1.2rem;
            font-weight: 800;
            color: #111827;
            margin-bottom: 0.2rem;
        }

        .tracker-desc {
            color: #6b7280;
            font-size: 0.94rem;
        }

        .section-spacer {
            height: 0.35rem;
        }

        .asset-card {
            padding: 16px 18px;
            margin-bottom: 0.75rem;
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
            font-size: 1.02rem;
            font-weight: 800;
            margin-bottom: 0.25rem;
        }

        .asset-sub {
            color: #6b7280;
            font-size: 0.9rem;
        }

        .asset-value {
            color: #111827;
            font-size: 1.25rem;
            font-weight: 800;
            text-align: right;
            line-height: 1.15;
        }

        .asset-pnl {
            font-size: 0.92rem;
            text-align: right;
            margin-top: 0.2rem;
        }

        .pill-positive,
        .pill-negative,
        .pill-neutral {
            display: inline-block;
            padding: 0.22rem 0.55rem;
            border-radius: 999px;
            font-size: 0.85rem;
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
            height: 0.25rem;
        }

        @media (max-width: 768px) {
            .block-container {
                padding-top: 0.8rem;
                padding-left: 0.8rem;
                padding-right: 0.8rem;
                padding-bottom: 1.25rem;
            }

            .hero-card,
            .summary-card,
            .tracker-card,
            .asset-card {
                border-radius: 20px;
            }

            .hero-card {
                padding: 20px 18px;
            }

            .hero-value {
                font-size: 2.2rem;
            }

            .summary-value {
                font-size: 1.6rem;
            }

            .tracker-header,
            .asset-top {
                display: block;
            }

            .asset-value,
            .asset-pnl {
                text-align: left;
                margin-top: 0.55rem;
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

st.title("Portfolio Overview")
st.markdown('<div class="app-subtitle">Celkový přehled portfolia napříč Crypto, Invest, My Trades a Investown.</div>', unsafe_allow_html=True)

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
# HERO
# =========================================================
st.markdown(
    f"""
    <div class="hero-card">
        <div class="hero-label">Celková hodnota portfolia</div>
        <div class="hero-value">{fmt_czk(net_worth_czk)}</div>
        <div class="hero-subrow">
            <span>Celkem investováno: <strong>{fmt_czk(total_invested_czk)}</strong></span>
            <span class="{profit_class}">{fmt_czk(total_pnl_czk)} · {total_pnl_pct_all:+.2f}%</span>
            <span>1 USD = <strong>{usdczk:.2f} CZK</strong></span>
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
        "Crypto",
        fmt_czk(crypto_total_value_czk),
        f"Investováno {fmt_czk(crypto_total_cost_czk)} · P/L {fmt_czk(crypto_total_pnl_czk)} · {total_pnl_pct:+.2f}%",
    )
with top2:
    render_summary_card(
        "Invest",
        fmt_czk(invest_total_value_czk),
        f"Plány + My Trades · Investováno {fmt_czk(invest_total_cost_czk)} · P/L {fmt_czk(invest_total_pnl_czk)} · {invest_total_pnl_pct:+.2f}%",
    )
with top3:
    render_summary_card(
        "Investown",
        fmt_czk(investown_total_value_czk),
        f"Investováno {fmt_czk(investown_total_cost_czk)} · P/L {fmt_czk(investown_total_pnl_czk)} · {investown_total_pnl_pct:+.2f}%",
    )

# =========================================================
# SECONDARY SUMMARY
# =========================================================
sub1, sub2, sub3 = st.columns(3)
with sub1:
    render_summary_card("Celkem investováno", fmt_czk(total_invested_czk), "Součet všech vložených prostředků")
with sub2:
    render_summary_card("Celkový zisk / ztráta", fmt_czk(total_pnl_czk), f"{total_pnl_pct_all:+.2f}% celkem")
with sub3:
    render_summary_card("Kurz USD/CZK", f"{usdczk:.2f}", "Aktuální kurz použitý pro přepočet")

st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

# =========================================================
# CRYPTO + INVEST
# =========================================================
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="tracker-card">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="tracker-header">
            <div>
                <div class="tracker-title">Crypto Tracker</div>
                <div class="tracker-desc">Přehled kryptoměnového portfolia</div>
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
        render_summary_card("Zisk / ztráta", format_usd(total_pnl_usd), f"{total_pnl_pct:+.2f}%")

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

with col2:
    st.markdown('<div class="tracker-card">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="tracker-header">
            <div>
                <div class="tracker-title">Invest Tracker</div>
                <div class="tracker-desc">Přehled investičních plánů a My Trades akcií</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    i1, i2, i3 = st.columns(3)
    with i1:
        render_summary_card("Hodnota pozic", fmt_czk(invest_positions_value_czk), "Plány + My Trades")
    with i2:
        render_summary_card("Cash rezerva", fmt_czk(invest_cash_balance_czk), "Volná hotovost v plánech")
    with i3:
        render_summary_card("Celkem Invest", fmt_czk(invest_total_value_czk), f"P/L {invest_total_pnl_pct:+.2f}%")

    st.markdown('<div class="small-gap"></div>', unsafe_allow_html=True)

    if not invest_plans and stock_positions_count == 0:
        st.info("Invest Tracker zatím neobsahuje aktivní investiční plán nebo My Trades akcie.")
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

        if stock_positions_count > 0:
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
            <div class="tracker-title">Investown Tracker</div>
            <div class="tracker-desc">Přehled Investown projektů</div>
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
    st.info("Investown service zatím není dostupný.")
elif investown_projects_count == 0:
    st.info("Investown Tracker zatím neobsahuje žádné projekty.")
else:
    render_asset_card(
        title="Souhrnný výsledek Investown",
        subtitle="Celkový výkon všech Investown projektů",
        value=fmt_czk(investown_total_pnl_czk),
        pnl_text=f"{investown_total_pnl_pct:+.2f}%",
        pnl_positive=investown_total_pnl_czk >= 0,
    )

st.markdown("</div>", unsafe_allow_html=True)
