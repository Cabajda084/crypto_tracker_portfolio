import io
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Tuple

import altair as alt
import pandas as pd
import streamlit as st

from invest_service import (
    fmt_czk,
    get_plans,
    get_plan,
    get_assets,
    get_cash,
    get_trades,
    get_planned_orders,
    get_latest_prices,
    get_snapshots,
    get_import_logs,
    compute_summary,
    get_plan_assets_overview,
    compute_asset_summary,
    bootstrap_stock_module,
    get_stock_portfolio_summary,
    get_stock_transactions,
    import_xtb_my_trades_from_dataframe,
)

try:
    import yfinance as yf
    YF_AVAILABLE = True
except Exception:
    yf = None
    YF_AVAILABLE = False


ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "data" / "portfolio.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

BASE_CURRENCY = "CZK"

PLAN_CONFIG = {
    "kaja": {
        "owner_name": "Karolína",
        "plan_name": "Kája",
        "display_name": "S&P 500",
        "icon": "📈",
        "sort_order": 1,
        "primary_ticker": "SXR8.DE",
    },
    "investment_plan_1": {
        "owner_name": "Karolína",
        "plan_name": "Investment Plan #1",
        "display_name": "MSCI World",
        "icon": "🌍",
        "sort_order": 2,
        "primary_ticker": "EUNL.DE",
    },
}

INSTRUMENT_TO_PLAN = {
    "CORE S&P 500": "kaja",
    "ISHARES CORE S&P 500": "kaja",
    "CORE MSCI WORLD": "investment_plan_1",
    "ISHARES CORE MSCI WORLD": "investment_plan_1",
}

SUBACCOUNT_TO_PLAN = {
    "54079785": "kaja",
    "52421184": "investment_plan_1",
}

XTB_NAME_TO_TICKER = {
    "Core S&P 500": "SXR8.DE",
    "iShares Core S&P 500": "SXR8.DE",
    "Core MSCI World": "EUNL.DE",
    "iShares Core MSCI World": "EUNL.DE",
    "Duolingo": "DUOL.US",
    "MSCI India": "QDV5.DE",
}

TICKER_PRICE_META = {
    "SXR8.DE": {"yf": "SXR8.DE", "quote_currency": "EUR"},
    "EUNL.DE": {"yf": "EUNL.DE", "quote_currency": "EUR"},
    "DUOL.US": {"yf": "DUOL", "quote_currency": "USD"},
    "QDV5.DE": {"yf": "QDV5.DE", "quote_currency": "EUR"},
}

FX_TICKERS = {"EUR": "EURCZK=X", "USD": "USDCZK=X", "CZK": None}


def inject_css():
    st.markdown("""
    <style>
    .block-container {max-width: 1400px; padding-top: 1.8rem; padding-bottom: 2rem;}
    .hero-card, .section-card, .plan-card, .mini-card {
        background: #fff;
        border: 1px solid #eaeaea;
        border-radius: 22px;
        box-shadow: 0 8px 28px rgba(15,23,42,.04);
    }
    .hero-card {padding: 26px 28px; margin-bottom: 14px;}
    .hero-label {font-size: .95rem; color: #6b7280; margin-bottom: 8px;}
    .hero-value {font-size: 3rem; font-weight: 800; line-height: 1.05; color: #111827;}
    .hero-profit-pos,.profit-pos {color:#16a34a; font-weight:700;}
    .hero-profit-neg,.profit-neg {color:#dc2626; font-weight:700;}

    .plan-card {padding: 16px 18px; margin-bottom: 10px;}
    .plan-card.selected {border-color:#dbeafe; background:linear-gradient(180deg,#fff 0%,#f8fbff 100%);}
    .plan-row {display:flex; justify-content:space-between; align-items:center; gap:16px;}
    .plan-left {display:flex; gap:14px; align-items:center;}
    .plan-icon {width:50px; height:50px; border-radius:16px; background:#f3f4f6; display:flex; align-items:center; justify-content:center; font-size:24px;}
    .plan-title {font-size:1.15rem; font-weight:800; color:#111827;}
    .plan-sub {font-size:.92rem; color:#6b7280;}
    .plan-value {font-size:1.55rem; font-weight:800; color:#111827; text-align:right;}
    .plan-pnl {font-size:.96rem; text-align:right;}

    .mini-card {padding: 14px 16px;}
    .mini-label {font-size:.92rem; color:#6b7280; margin-bottom:6px;}
    .mini-value {font-size:1.45rem; font-weight:800; color:#111827; line-height:1.15;}

    .section-card {padding:18px 20px;}
    .soft-gap {height: 14px;}
    .muted {color:#6b7280;}
    </style>
    """, unsafe_allow_html=True)


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def execute(query, params=()):
    conn = get_conn()
    conn.execute(query, params)
    conn.commit()
    conn.close()


def read_df(query, params=()):
    conn = get_conn()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def column_exists(conn, table: str, column: str) -> bool:
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return column in [c[1] for c in cols]


def ensure_column(conn, table: str, column: str, column_sql: str):
    if not column_exists(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_sql}")


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS investment_plans (
            plan_id TEXT PRIMARY KEY,
            owner_name TEXT NOT NULL,
            plan_name TEXT NOT NULL,
            display_name TEXT,
            base_currency TEXT NOT NULL DEFAULT 'CZK',
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            note TEXT,
            icon TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0,
            primary_ticker TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS plan_assets (
            plan_asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            asset_name TEXT NOT NULL,
            asset_type TEXT NOT NULL DEFAULT 'ETF',
            target_weight REAL NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            note TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0,
            UNIQUE(plan_id, ticker)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cash_transactions (
            cash_tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id TEXT NOT NULL,
            tx_date TEXT NOT NULL,
            tx_type TEXT NOT NULL,
            amount REAL NOT NULL,
            note TEXT,
            source TEXT,
            source_file TEXT,
            external_id TEXT,
            UNIQUE(plan_id, source, external_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS investment_transactions (
            tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id TEXT NOT NULL,
            tx_date TEXT NOT NULL,
            ticker TEXT NOT NULL,
            tx_type TEXT NOT NULL,
            quantity REAL NOT NULL,
            price_per_unit REAL NOT NULL,
            fee REAL NOT NULL DEFAULT 0,
            total_value REAL NOT NULL,
            note TEXT,
            source TEXT,
            source_file TEXT,
            external_id TEXT,
            UNIQUE(plan_id, source, external_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS planned_orders (
            planned_order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            planned_date TEXT,
            planned_amount REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'planned',
            priority INTEGER NOT NULL DEFAULT 1,
            note TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS asset_prices (
            price_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            price REAL NOT NULL,
            currency TEXT NOT NULL DEFAULT 'CZK',
            price_date TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'manual',
            quote_currency TEXT,
            fx_rate_to_czk REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id TEXT NOT NULL,
            snapshot_date TEXT NOT NULL,
            portfolio_value REAL NOT NULL,
            positions_value REAL NOT NULL,
            cash_balance REAL NOT NULL,
            invested_amount REAL NOT NULL,
            profit_loss REAL NOT NULL,
            UNIQUE(plan_id, snapshot_date)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS import_logs (
            import_id INTEGER PRIMARY KEY AUTOINCREMENT,
            imported_at TEXT NOT NULL,
            source TEXT NOT NULL,
            source_file TEXT,
            plan_id TEXT,
            product_filter TEXT,
            inserted_cash INTEGER NOT NULL DEFAULT 0,
            inserted_investments INTEGER NOT NULL DEFAULT 0,
            inserted_assets INTEGER NOT NULL DEFAULT 0,
            skipped_duplicates INTEGER NOT NULL DEFAULT 0,
            note TEXT
        )
    """)

    for table, cols in {
        "investment_plans": {
            "display_name": "TEXT",
            "icon": "TEXT",
            "sort_order": "INTEGER NOT NULL DEFAULT 0",
            "primary_ticker": "TEXT",
        },
        "cash_transactions": {
            "source": "TEXT",
            "source_file": "TEXT",
            "external_id": "TEXT",
        },
        "investment_transactions": {
            "source": "TEXT",
            "source_file": "TEXT",
            "external_id": "TEXT",
        },
        "asset_prices": {
            "quote_currency": "TEXT",
            "fx_rate_to_czk": "REAL",
        },
        "import_logs": {
            "source": "TEXT NOT NULL DEFAULT 'xtb'",
            "source_file": "TEXT",
            "plan_id": "TEXT",
            "product_filter": "TEXT",
            "inserted_cash": "INTEGER NOT NULL DEFAULT 0",
            "inserted_investments": "INTEGER NOT NULL DEFAULT 0",
            "inserted_assets": "INTEGER NOT NULL DEFAULT 0",
            "skipped_duplicates": "INTEGER NOT NULL DEFAULT 0",
            "note": "TEXT",
        },
    }.items():
        for c, t in cols.items():
            ensure_column(conn, table, c, t)

    conn.commit()
    conn.close()


def seed_plans():
    for plan_id, cfg in PLAN_CONFIG.items():
        existing = read_df("SELECT 1 FROM investment_plans WHERE plan_id = ?", (plan_id,))
        if existing.empty:
            execute("""
                INSERT INTO investment_plans(
                    plan_id, owner_name, plan_name, display_name, base_currency,
                    created_at, status, note, icon, sort_order, primary_ticker
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                plan_id, cfg["owner_name"], cfg["plan_name"], cfg["display_name"], BASE_CURRENCY,
                datetime.now().isoformat(), "active", "Výchozí investiční plán",
                cfg["icon"], cfg["sort_order"], cfg["primary_ticker"]
            ))
        else:
            execute("""
                UPDATE investment_plans
                SET display_name = ?, icon = ?, sort_order = ?, primary_ticker = ?
                WHERE plan_id = ?
            """, (cfg["display_name"], cfg["icon"], cfg["sort_order"], cfg["primary_ticker"], plan_id))


def safe_date(v) -> Optional[str]:
    if v is None or pd.isna(v):
        return None
    try:
        return str(pd.to_datetime(v).date())
    except Exception:
        return None


def parse_buy_comment(comment: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    if comment is None or pd.isna(comment):
        return None, None
    m = re.search(r"OPEN BUY\s+([\d\.]+)(?:/[\d\.]+)?\s+@\s+([\d\.]+)", str(comment), flags=re.IGNORECASE)
    if not m:
        return None, None
    return float(m.group(1)), float(m.group(2))


def parse_subaccount(comment: Optional[str]) -> Optional[str]:
    if comment is None or pd.isna(comment):
        return None
    m = re.search(r"\bto\s+(\d{6,12})\b", str(comment), flags=re.IGNORECASE)
    return m.group(1) if m else None


def normalize_ticker(instrument: Optional[str], explicit_ticker: Optional[str] = None) -> str:
    if explicit_ticker and pd.notna(explicit_ticker):
        return str(explicit_ticker).strip().upper()
    if instrument is None or pd.isna(instrument):
        return "UNKNOWN"
    return XTB_NAME_TO_TICKER.get(str(instrument).strip(), str(instrument).strip()).upper()


def resolve_plan_by_instrument(instrument: Optional[str]) -> Optional[str]:
    if instrument is None or pd.isna(instrument):
        return None
    return INSTRUMENT_TO_PLAN.get(str(instrument).strip().upper())


def infer_asset_type(name: str, category: Optional[str] = None) -> str:
    if category and str(category).strip().upper() == "ETF":
        return "ETF"
    return "ETF"


def upsert_asset(plan_id: str, ticker: str, asset_name: str, asset_type: str = "ETF") -> bool:
    existing = read_df("SELECT 1 FROM plan_assets WHERE plan_id = ? AND ticker = ?", (plan_id, ticker))
    if existing.empty:
        execute("""
            INSERT INTO plan_assets(plan_id, ticker, asset_name, asset_type, target_weight, is_active, note, sort_order)
            VALUES (?, ?, ?, ?, 0, 1, '', 0)
        """, (plan_id, ticker, asset_name, asset_type))
        return True
    return False


def insert_cash(plan_id: str, tx_date: str, tx_type: str, amount: float, note: str = "", source: str = "manual",
                source_file: Optional[str] = None, external_id: Optional[str] = None) -> bool:
    try:
        execute("""
            INSERT INTO cash_transactions(plan_id, tx_date, tx_type, amount, note, source, source_file, external_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (plan_id, tx_date, tx_type, float(amount), note, source, source_file, external_id))
        return True
    except sqlite3.IntegrityError:
        return False


def insert_trade(plan_id: str, tx_date: str, ticker: str, tx_type: str, quantity: float, price_per_unit: float,
                 fee: float = 0.0, note: str = "", source: str = "manual",
                 source_file: Optional[str] = None, external_id: Optional[str] = None) -> bool:
    total_value = float(quantity) * float(price_per_unit) + float(fee)
    try:
        execute("""
            INSERT INTO investment_transactions(
                plan_id, tx_date, ticker, tx_type, quantity, price_per_unit, fee, total_value,
                note, source, source_file, external_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (plan_id, tx_date, ticker, tx_type, float(quantity), float(price_per_unit), float(fee),
              float(total_value), note, source, source_file, external_id))
        return True
    except sqlite3.IntegrityError:
        return False


def add_planned_order(plan_id: str, ticker: str, planned_date: str, planned_amount: float, note: str = "", priority: int = 1):
    execute("""
        INSERT INTO planned_orders(plan_id, ticker, planned_date, planned_amount, status, priority, note)
        VALUES (?, ?, ?, ?, 'planned', ?, ?)
    """, (plan_id, ticker, planned_date, float(planned_amount), int(priority), note))


def set_asset_price(ticker: str, price_czk: float, source: str = "manual", quote_currency: str = "CZK",
                    fx_rate_to_czk: float = 1.0, price_date: Optional[str] = None):
    execute("""
        INSERT INTO asset_prices(ticker, price, currency, price_date, source, quote_currency, fx_rate_to_czk)
        VALUES (?, ?, 'CZK', ?, ?, ?, ?)
    """, (ticker, float(price_czk), price_date or str(date.today()), source, quote_currency, fx_rate_to_czk))


def fetch_yf_close(symbol: str) -> float:
    if not YF_AVAILABLE:
        raise RuntimeError("Chybí balíček yfinance. Nainstaluj: python -m pip install yfinance")
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="7d", auto_adjust=False)
    if hist.empty or hist["Close"].dropna().empty:
        raise RuntimeError(f"Nepodařilo se načíst cenu pro {symbol}")
    return float(hist["Close"].dropna().iloc[-1])


def fetch_fx_rate_to_czk(currency: str) -> float:
    fx_symbol = FX_TICKERS.get(currency.upper())
    if fx_symbol is None:
        return 1.0
    return fetch_yf_close(fx_symbol)


def get_trade_fx_rate_for_ticker(ticker: str) -> float:
    meta = TICKER_PRICE_META.get(ticker)
    if not meta:
        return 1.0

    quote_currency = meta.get("quote_currency", "CZK")
    if quote_currency == "CZK":
        return 1.0

    return fetch_fx_rate_to_czk(quote_currency)


def refresh_auto_prices() -> tuple[list, list]:
    assets = read_df("SELECT DISTINCT ticker FROM plan_assets WHERE is_active = 1 ORDER BY ticker")
    ok, err = [], []
    if assets.empty:
        return ok, err

    for ticker in assets["ticker"].tolist():
        meta = TICKER_PRICE_META.get(ticker)
        if not meta:
            err.append(f"{ticker}: chybí mapování ceny")
            continue
        try:
            quote = fetch_yf_close(meta["yf"])
            fx = fetch_fx_rate_to_czk(meta["quote_currency"])
            price_czk = quote * fx
            set_asset_price(
                ticker,
                price_czk,
                source="yahoo_finance_auto",
                quote_currency=meta["quote_currency"],
                fx_rate_to_czk=fx
            )
            ok.append({"ticker": ticker, "quote": quote, "fx": fx, "price_czk": price_czk})
        except Exception as e:
            err.append(f"{ticker}: {e}")

    return ok, err


def save_daily_snapshot(plan_id: str):
    summary = compute_summary(plan_id)
    execute("""
        INSERT OR REPLACE INTO portfolio_snapshots(
            plan_id, snapshot_date, portfolio_value, positions_value, cash_balance, invested_amount, profit_loss
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        plan_id, str(date.today()), summary["portfolio_value"], summary["positions_value"],
        summary["cash_balance"], summary["invested_amount"], summary["profit_loss"]
    ))


def maybe_snapshot_today():
    for plan_id in PLAN_CONFIG.keys():
        exists = read_df(
            "SELECT 1 FROM portfolio_snapshots WHERE plan_id = ? AND snapshot_date = ?",
            (plan_id, str(date.today()))
        )
        prices = get_latest_prices()
        if exists.empty and not prices.empty:
            save_daily_snapshot(plan_id)


def detect_xtb_header_row(df: pd.DataFrame, sheet_name: str) -> int:
    expected = {
        "Cash Operations": {"Type", "Instrument", "Time", "Amount", "ID", "Comment", "Product"},
        "Closed Positions": {"Instrument", "Ticker", "Volume", "Close Price", "Close Time (UTC)", "Product"},
    }[sheet_name]
    for i in range(min(10, len(df))):
        vals = {str(v).strip() for v in df.iloc[i].tolist() if pd.notna(v) and str(v).strip()}
        if len(expected.intersection(vals)) >= 3:
            return i
    return 3


def read_xtb_sheet(xls: pd.ExcelFile, sheet_name: str) -> pd.DataFrame:
    preview = pd.read_excel(xls, sheet_name=sheet_name, header=None)
    header_row = detect_xtb_header_row(preview, sheet_name)
    df = pd.read_excel(xls, sheet_name=sheet_name, header=header_row)
    df.columns = [str(c).strip() for c in df.columns]
    return df.dropna(how="all")

def import_xtb_report(uploaded_file, product_filter: str = "Investment Plans"):
    xls = pd.ExcelFile(io.BytesIO(uploaded_file.getvalue()))
    source_file = uploaded_file.name

    # =========================================================
    # STOCKS: XTB "My Trades" -> stock_transactions
    # =========================================================
    if product_filter == "My Trades":
        inserted_cash = 0
        inserted_trades = 0
        inserted_assets = 0
        skipped = 0

        closed_df = read_xtb_sheet(xls, "Closed Positions")
        closed_df = closed_df[closed_df["Product"].astype(str).str.strip() == product_filter].copy()

        # normalizace čísel
        if "Volume" in closed_df.columns:
            closed_df["Volume"] = pd.to_numeric(closed_df["Volume"], errors="coerce").fillna(0.0)
        if "Close Price" in closed_df.columns:
            closed_df["Close Price"] = pd.to_numeric(closed_df["Close Price"], errors="coerce").fillna(0.0)

        # XTB -> Yahoo mapping
        stock_symbol_map = {
            "AMZN.US": "AMZN",
            "META.US": "META",
            "MSFT.US": "MSFT",
            "DUOL.US": "DUOL",
            "AMZN": "AMZN",
            "META": "META",
            "MSFT": "MSFT",
            "DUOL": "DUOL",
        }

        # název sloupce se může lišit podle exportu
        currency_col = None
        for candidate in ["Currency", "Profit currency", "Currency pair"]:
            if candidate in closed_df.columns:
                currency_col = candidate
                break

        side_col = None
        for candidate in ["Side", "Type"]:
            if candidate in closed_df.columns:
                side_col = candidate
                break

        result = import_xtb_my_trades_from_dataframe(
            closed_df,
            ticker_column="Ticker",
            name_column="Instrument",
            side_column=side_col or "Type",
            date_column="Close Time (UTC)",
            quantity_column="Volume",
            price_column="Close Price",
            currency_column=currency_col or "Currency",
            external_id_column="Position ID" if "Position ID" in closed_df.columns else None,
            yfinance_symbol_map=stock_symbol_map,
        )

        inserted_trades = int(result.get("imported", 0))
        skipped = int(result.get("skipped", 0))

        execute("""
            INSERT INTO import_logs(
                imported_at, source, source_file, plan_id, product_filter,
                inserted_cash, inserted_investments, inserted_assets, skipped_duplicates, note
            ) VALUES (?, 'xtb', ?, 'stocks', ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            source_file,
            product_filter,
            inserted_cash,
            inserted_trades,
            inserted_assets,
            skipped,
            "Import XTB reportu - My Trades (stocks)"
        ))

        return inserted_cash, inserted_trades, inserted_assets, skipped

    # =========================================================
    # ETF: XTB "Investment Plans" -> existing logic
    # =========================================================
    inserted_cash = inserted_trades = inserted_assets = skipped = 0

    cash_df = read_xtb_sheet(xls, "Cash Operations")
    cash_df = cash_df[cash_df["Product"].astype(str).str.strip() == product_filter].copy()
    cash_df["Amount"] = pd.to_numeric(cash_df["Amount"], errors="coerce").fillna(0.0)

    id_to_plan = {}

    for _, r in cash_df.iterrows():
        op_type = str(r.get("Type", "")).strip()
        xtb_id = r.get("ID")
        comment = r.get("Comment")
        instrument = r.get("Instrument")
        amount = float(r.get("Amount", 0.0))
        tx_date = safe_date(r.get("Time"))
        if not tx_date:
            continue

        plan_id = None
        subacc = parse_subaccount(comment)
        if subacc and subacc in SUBACCOUNT_TO_PLAN:
            plan_id = SUBACCOUNT_TO_PLAN[subacc]
            if pd.notna(xtb_id):
                id_to_plan[str(xtb_id)] = plan_id
        if not plan_id and pd.notna(xtb_id):
            plan_id = id_to_plan.get(str(xtb_id))
        if not plan_id:
            plan_id = resolve_plan_by_instrument(instrument)
        if not plan_id:
            continue

        if op_type in ["Deposit", "Withdrawal", "Transfer", "Subaccount transfer"]:
            mapped_type, mapped_amount = None, None
            if op_type == "Deposit" and amount > 0:
                mapped_type, mapped_amount = "deposit", amount
            elif op_type == "Withdrawal":
                mapped_type, mapped_amount = "withdrawal", abs(amount)
            elif op_type in ["Transfer", "Subaccount transfer"]:
                if amount > 0:
                    mapped_type, mapped_amount = "deposit", amount
                elif amount < 0:
                    mapped_type, mapped_amount = "withdrawal", abs(amount)

            if mapped_type:
                ok = insert_cash(
                    plan_id,
                    tx_date,
                    mapped_type,
                    mapped_amount,
                    note=f"XTB import: {op_type} | {comment or ''}",
                    source="xtb",
                    source_file=source_file,
                    external_id=f"xtb_cash_{xtb_id}_{op_type}_{tx_date}_{mapped_amount}_{plan_id}"
                )
                inserted_cash += 1 if ok else 0
                skipped += 0 if ok else 1

        elif op_type == "Stock purchase":
            qty, price = parse_buy_comment(comment)
            if qty is None or price is None:
                continue

            ticker = normalize_ticker(instrument)
            asset_name = str(instrument).strip() if pd.notna(instrument) else ticker

            if upsert_asset(plan_id, ticker, asset_name, infer_asset_type(asset_name)):
                inserted_assets += 1

            fx = get_trade_fx_rate_for_ticker(ticker)
            price_czk = price * fx

            ok = insert_trade(
                plan_id,
                tx_date,
                ticker,
                "buy",
                qty,
                price_czk,
                0.0,
                note=f"XTB import: {comment or ''}",
                source="xtb",
                source_file=source_file,
                external_id=f"xtb_buy_{xtb_id}_{ticker}_{tx_date}_{qty}_{price}_{plan_id}"
            )
            inserted_trades += 1 if ok else 0
            skipped += 0 if ok else 1

    closed_df = read_xtb_sheet(xls, "Closed Positions")
    closed_df = closed_df[closed_df["Product"].astype(str).str.strip() == product_filter].copy()
    closed_df["Volume"] = pd.to_numeric(closed_df["Volume"], errors="coerce").fillna(0.0)
    closed_df["Close Price"] = pd.to_numeric(closed_df["Close Price"], errors="coerce").fillna(0.0)

    for _, r in closed_df.iterrows():
        plan_id = resolve_plan_by_instrument(r.get("Instrument"))
        if not plan_id:
            continue

        tx_date = safe_date(r.get("Close Time (UTC)"))
        qty = float(r.get("Volume", 0.0))
        price = float(r.get("Close Price", 0.0))
        if not tx_date or qty <= 0 or price <= 0:
            continue

        ticker = normalize_ticker(r.get("Instrument"), r.get("Ticker"))
        asset_name = str(r.get("Instrument")).strip() if pd.notna(r.get("Instrument")) else ticker

        if upsert_asset(plan_id, ticker, asset_name, infer_asset_type(asset_name, r.get("Category"))):
            inserted_assets += 1

        fx = get_trade_fx_rate_for_ticker(ticker)
        price_czk = price * fx

        ok = insert_trade(
            plan_id,
            tx_date,
            ticker,
            "sell",
            qty,
            price_czk,
            0.0,
            note=f"XTB import: closed position ID {r.get('Position ID')}",
            source="xtb",
            source_file=source_file,
            external_id=f"xtb_sell_{r.get('Position ID')}_{ticker}_{tx_date}_{qty}_{price}_{plan_id}"
        )
        inserted_trades += 1 if ok else 0
        skipped += 0 if ok else 1

    execute("""
        INSERT INTO import_logs(
            imported_at, source, source_file, plan_id, product_filter,
            inserted_cash, inserted_investments, inserted_assets, skipped_duplicates, note
        ) VALUES (?, 'xtb', ?, 'all_plans', ?, ?, ?, ?, ?, 'Import XTB reportu')
    """, (
        datetime.now().isoformat(),
        source_file,
        product_filter,
        inserted_cash,
        inserted_trades,
        inserted_assets,
        skipped
    ))

    return inserted_cash, inserted_trades, inserted_assets, skipped


def render_hero(total):
    cls = "hero-profit-pos" if total["profit_loss"] >= 0 else "hero-profit-neg"
    st.markdown(f"""
    <div class="hero-card">
        <div class="hero-label">Souhrn všech investičních plánů</div>
        <div class="hero-value">{fmt_czk(total["positions_value"])}</div>
        <div class="{cls}">Zisk / ztráta: {total["profit_loss"]:+,.2f} CZK ({total["profit_loss_pct"]:+,.2f}%)</div>
        <div class="muted" style="margin-top:8px;">
            Cash celkem: {fmt_czk(total["cash_balance"])} · Celkem plánů včetně cash: {fmt_czk(total["portfolio_value"])}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_plan_card(plan, summary, selected):
    cls = "plan-card selected" if selected else "plan-card"
    pnl_cls = "profit-pos" if summary["profit_loss"] >= 0 else "profit-neg"
    st.markdown(f"""
    <div class="{cls}">
      <div class="plan-row">
        <div class="plan-left">
          <div class="plan-icon">{plan['icon']}</div>
          <div>
            <div class="plan-title">{plan['display_name']}</div>
            <div class="plan-sub">
              Pozice {fmt_czk(summary['positions_value'])} · Cash {fmt_czk(summary['cash_balance'])}
            </div>
          </div>
        </div>
        <div>
          <div class="plan-value">{fmt_czk(summary['positions_value'])}</div>
          <div class="plan-pnl {pnl_cls}">
            Celkem {fmt_czk(summary['portfolio_value'])} · P/L {summary['profit_loss']:+,.2f} CZK ({summary['profit_loss_pct']:+,.2f}%)
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_mini(label, value, delta=None, positive=True):
    delta_html = ""
    if delta is not None:
        delta_html = f'<div class="{"profit-pos" if positive else "profit-neg"}">{delta}</div>'
    st.markdown(
        f'<div class="mini-card"><div class="mini-label">{label}</div><div class="mini-value">{value}</div>{delta_html}</div>',
        unsafe_allow_html=True
    )


def render_allocations(positions: pd.DataFrame):
    if positions.empty:
        st.info("Zatím nejsou žádné investice v plánu.")
        return
    for _, r in positions.sort_values("allocation_pct", ascending=False).iterrows():
        pct = max(0.0, min(float(r["allocation_pct"]), 100.0))
        st.markdown(f"""
        <div style="margin-bottom:14px;">
          <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
            <div><b>{r['asset_name']}</b><br><span class="muted">{r['ticker']}</span></div>
            <div style="text-align:right;"><b>{pct:.2f}%</b><br><span class="muted">{fmt_czk(float(r['current_value']))}</span></div>
          </div>
          <div style="height:10px;background:#f3f4f6;border-radius:999px;overflow:hidden;">
            <div style="width:{pct}%;height:10px;background:linear-gradient(90deg,#60a5fa,#34d399);"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)


def render_snapshot_chart(plan_id: str):
    df = get_snapshots(plan_id)
    if df.empty:
        st.info("Zatím nejsou snapshoty portfolia.")
        return

    melt = df.melt(
        id_vars=["snapshot_date"],
        value_vars=["portfolio_value", "positions_value", "cash_balance"],
        var_name="series",
        value_name="value"
    )
    name_map = {
        "portfolio_value": "Celkem plán",
        "positions_value": "Hodnota pozic",
        "cash_balance": "Penížní rezerva",
    }
    melt["series"] = melt["series"].map(name_map)

    chart = alt.Chart(melt).mark_line(point=True).encode(
        x=alt.X("snapshot_date:T", title="Datum"),
        y=alt.Y("value:Q", title="CZK"),
        color=alt.Color("series:N", title=""),
        tooltip=["snapshot_date:T", "series:N", alt.Tooltip("value:Q", format=",.2f")]
    ).properties(height=320)

    st.altair_chart(chart, use_container_width=True)


st.set_page_config(page_title="Invest Tracker", page_icon="📈", layout="wide")
inject_css()
init_db()

try:
    bootstrap_stock_module()
except Exception:
    pass

seed_plans()

if "selected_invest_plan" not in st.session_state:
    st.session_state.selected_invest_plan = "kaja"

plans = get_plans().to_dict("records")
plan_summaries = {p["plan_id"]: compute_summary(p["plan_id"]) for p in plans}
total = {
    "portfolio_value": sum(v["portfolio_value"] for v in plan_summaries.values()),
    "positions_value": sum(v["positions_value"] for v in plan_summaries.values()),
    "cash_balance": sum(v["cash_balance"] for v in plan_summaries.values()),
    "profit_loss": sum(v["profit_loss"] for v in plan_summaries.values()),
    "cash_in_out": sum(v["cash_in_out"] for v in plan_summaries.values()),
}
total["profit_loss_pct"] = (total["profit_loss"] / total["cash_in_out"] * 100) if total["cash_in_out"] else 0.0

maybe_snapshot_today()

st.title("📈 Invest Tracker")
render_hero(total)

st.subheader("Investiční plány")
for p in plans:
    render_plan_card(p, plan_summaries[p["plan_id"]], st.session_state.selected_invest_plan == p["plan_id"])
    if st.button(f"Otevřít {p['display_name']}", key=f"open_{p['plan_id']}", use_container_width=True):
        st.session_state.selected_invest_plan = p["plan_id"]
        st.rerun()

selected_plan_id = st.session_state.selected_invest_plan
selected_plan = get_plan(selected_plan_id)
summary = compute_summary(selected_plan_id)
assets = get_assets(selected_plan_id)
trades = get_trades(selected_plan_id)
cash = get_cash(selected_plan_id)
planned = get_planned_orders(selected_plan_id)
prices = get_latest_prices()
assets_overview = get_plan_assets_overview(selected_plan_id)

if "selected_asset_ticker" not in st.session_state:
    st.session_state.selected_asset_ticker = None

if not assets_overview.empty:
    available_tickers = assets_overview["ticker"].tolist()
    if st.session_state.selected_asset_ticker not in available_tickers:
        st.session_state.selected_asset_ticker = available_tickers[0]
else:
    st.session_state.selected_asset_ticker = None

st.markdown('<div class="soft-gap"></div>', unsafe_allow_html=True)
st.markdown(f"## {selected_plan['icon']} {selected_plan['display_name']}")
st.caption(f"Interní název plánu: {selected_plan['plan_name']} | Vlastník: {selected_plan['owner_name']}")

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    render_mini("Hodnota pozic", fmt_czk(summary["positions_value"]))
with c2:
    render_mini("Zisk / ztráta", fmt_czk(summary["profit_loss"]), f"{summary['profit_loss_pct']:+.2f} %", summary["profit_loss"] >= 0)
with c3:
    render_mini("Investováno", fmt_czk(summary["invested_amount"]))
with c4:
    render_mini("Penížní rezerva", fmt_czk(summary["cash_balance"]))
with c5:
    render_mini("Celkem plán", fmt_czk(summary["portfolio_value"]))

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Přehled", "Aktiva", "Budoucí nákupy", "Transakce", "Import XTB"])

with tab1:
    left, right = st.columns([1.35, 1])

    with left:
        st.markdown("### Vývoj portfolia")
        render_snapshot_chart(selected_plan_id)

        st.markdown("### Přehled investic")
        if summary["positions"].empty:
            st.info("Zatím nejsou žádné investice.")
        else:
            show = summary["positions"].copy()
            for col in [
                "quantity", "avg_buy_price", "invested_amount", "current_price",
                "current_value", "profit_loss", "profit_loss_pct", "allocation_pct"
            ]:
                show[col] = show[col].round(2 if col != "quantity" else 6)
            st.dataframe(show, use_container_width=True, hide_index=True)

    with right:
        st.markdown("### Alokace portfolia")
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        render_allocations(summary["positions"])
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("### Ceny a denní snapshot")
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        if not YF_AVAILABLE:
            st.warning("Pro automatické ceny nainstaluj: python -m pip install yfinance")
        rc1, rc2 = st.columns(2)
        with rc1:
            if st.button("Aktualizovat ceny", use_container_width=True):
                ok, err = refresh_auto_prices()
                if ok:
                    st.success(f"Aktualizováno {len(ok)} tickerů.")
                for e in err:
                    st.warning(e)
                st.rerun()
        with rc2:
            if st.button("Uložit denní snapshot", use_container_width=True):
                save_daily_snapshot(selected_plan_id)
                st.success("Denní snapshot uložen.")
                st.rerun()

        plan_ticker = selected_plan.get("primary_ticker")
        latest = prices[prices["ticker"] == plan_ticker]
        if not latest.empty:
            row = latest.iloc[0]
            st.markdown(
                f'<div class="muted">Poslední cena: <b>{fmt_czk(float(row["price"]))}</b> · {row["price_date"]} · {row["source"]}</div>',
                unsafe_allow_html=True
            )
        else:
            st.info("Zatím není uložená žádná cena.")

        with st.form("manual_price", clear_on_submit=True):
            ticker = st.selectbox(
                "Ticker",
                assets["ticker"].tolist() if not assets.empty else [selected_plan["primary_ticker"]]
            )
            price = st.number_input("Ruční cena v CZK", min_value=0.0, value=0.0, step=1.0)
            submit = st.form_submit_button("Uložit ruční cenu", use_container_width=True)
            if submit and price > 0:
                set_asset_price(ticker, price, source="manual")
                st.success("Ruční cena uložena.")
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.markdown("### Aktiva v plánu")

    if assets_overview.empty:
        st.info("V tomto plánu zatím nejsou žádná aktiva.")
    else:
        left, right = st.columns([1.2, 1])

        with left:
            overview = assets_overview.copy()
            for col in [
                "quantity", "avg_buy_price", "invested_amount",
                "current_price", "current_value", "profit_loss",
                "profit_loss_pct", "allocation_pct"
            ]:
                overview[col] = overview[col].round(2 if col != "quantity" else 6)

            st.dataframe(
                overview[[
                    "asset_name", "ticker", "quantity", "current_price",
                    "current_value", "profit_loss", "profit_loss_pct", "allocation_pct"
                ]],
                use_container_width=True,
                hide_index=True
            )

            chosen = st.selectbox(
                "Vyber aktivum",
                options=assets_overview["ticker"].tolist(),
                index=assets_overview["ticker"].tolist().index(st.session_state.selected_asset_ticker)
                if st.session_state.selected_asset_ticker in assets_overview["ticker"].tolist()
                else 0,
                format_func=lambda x: f"{x} — {assets_overview.loc[assets_overview['ticker'] == x, 'asset_name'].iloc[0]}"
            )
            st.session_state.selected_asset_ticker = chosen

        with right:
            asset_detail = compute_asset_summary(selected_plan_id, st.session_state.selected_asset_ticker)

            if not asset_detail:
                st.info("Detail aktiva není k dispozici.")
            else:
                st.markdown(f"### {asset_detail['asset_name']}")
                st.caption(f"Ticker: {asset_detail['ticker']}")

                a1, a2 = st.columns(2)
                with a1:
                    render_mini("Aktuální hodnota", fmt_czk(asset_detail["current_value"]))
                with a2:
                    render_mini(
                        "Zisk / ztráta",
                        fmt_czk(asset_detail["profit_loss"]),
                        f"{asset_detail['profit_loss_pct']:+.2f} %",
                        asset_detail["profit_loss"] >= 0
                    )

                b1, b2 = st.columns(2)
                with b1:
                    render_mini("Množství", f"{asset_detail['quantity']:.6f}".rstrip("0").rstrip("."))
                with b2:
                    render_mini("Alokace", f"{asset_detail['allocation_pct']:.2f} %")

                c1, c2 = st.columns(2)
                with c1:
                    render_mini("Průměrná nákupní cena", fmt_czk(asset_detail["avg_buy_price"]))
                with c2:
                    render_mini("Aktuální cena", fmt_czk(asset_detail["current_price"]))

                d1, d2 = st.columns(2)
                with d1:
                    render_mini("Počet nákupů", str(asset_detail["buy_count"]))
                with d2:
                    render_mini("Počet prodejů", str(asset_detail["sell_count"]))

                if asset_detail["latest_price_date"]:
                    st.caption(
                        f"Poslední cena: {asset_detail['latest_price_date']} · {asset_detail['latest_price_source']}"
                    )

                st.markdown("### Transakce aktiva")
                tx_df = asset_detail["transactions"].copy()

                if tx_df.empty:
                    st.info("Pro toto aktivum zatím nejsou transakce.")
                else:
                    show_tx = tx_df.copy()
                    for col in ["quantity", "price_per_unit", "fee", "total_value"]:
                        if col in show_tx.columns:
                            show_tx[col] = show_tx[col].round(2)
                    st.dataframe(show_tx, use_container_width=True, hide_index=True)

with tab3:
    col1, col2 = st.columns([1.5, 1])
    with col1:
        st.markdown("### Plánované nákupy")
        if planned.empty:
            st.info("Žádné plánované nákupy.")
        else:
            st.dataframe(planned, use_container_width=True, hide_index=True)
    with col2:
        st.markdown("### Přidat plánovaný nákup")
        choices = assets["ticker"].tolist() if not assets.empty else [selected_plan["primary_ticker"]]
        with st.form("planned_buy", clear_on_submit=True):
            ticker = st.selectbox("Ticker", choices)
            pdate = st.date_input("Plánované datum", value=date.today())
            amount = st.number_input("Částka", min_value=0.0, value=0.0, step=100.0)
            note = st.text_input("Poznámka")
            submit = st.form_submit_button("Uložit", use_container_width=True)
            if submit and amount > 0:
                add_planned_order(selected_plan_id, ticker, str(pdate), amount, note, 1)
                st.success("Plánovaný nákup uložen.")
                st.rerun()

with tab4:
    tc1, tc2 = st.columns(2)
    with tc1:
        st.markdown("### Cash transakce")
        st.dataframe(cash, use_container_width=True, hide_index=True) if not cash.empty else st.info("Žádné cash transakce.")
    with tc2:
        st.markdown("### Investiční transakce")
        st.dataframe(trades, use_container_width=True, hide_index=True) if not trades.empty else st.info("Žádné investiční transakce.")

with tab5:
    st.markdown("### Import XTB reportu")
    uploaded = st.file_uploader("Nahraj XTB report (.xlsx)", type=["xlsx"])
    product_filter = st.selectbox("Produkt", ["Investment Plans", "My Trades"], index=0)
    if st.button("Importovat XTB", use_container_width=True, disabled=uploaded is None):
        try:
            a, b, c, d = import_xtb_report(uploaded, product_filter)
            st.success(f"Hotovo. Cash: {a}, transakce: {b}, nová aktiva: {c}, duplicity: {d}")
            st.rerun()
        except Exception as e:
            st.error(f"Import selhal: {e}")

    st.markdown("### Historie importů")
    logs = get_import_logs()
    st.dataframe(logs, use_container_width=True, hide_index=True) if not logs.empty else st.info("Zatím žádný import.")

st.markdown("---")
st.subheader("Akcie (My Trades)")

stock_summary = get_stock_portfolio_summary()

sc1, sc2, sc3, sc4 = st.columns(4)
with sc1:
    render_mini("Počet pozic", str(stock_summary.get("positions_count", 0)))
with sc2:
    render_mini("Nákupní hodnota", fmt_czk(stock_summary.get("total_cost_basis", 0.0)))
with sc3:
    render_mini("Tržní hodnota", fmt_czk(stock_summary.get("total_market_value", 0.0)))
with sc4:
    stock_pnl = float(stock_summary.get("total_unrealized_pnl", 0.0))
    render_mini(
        "Nerealizovaný P/L",
        fmt_czk(stock_pnl),
        None,
        stock_pnl >= 0
    )

stock_positions = stock_summary.get("positions", [])

if not stock_positions:
    st.info("Zatím nejsou evidované žádné akcie z XTB My Trades.")
else:
    stock_df = pd.DataFrame(stock_positions).copy()

    rename_map = {
        "ticker": "Ticker",
        "name": "Název",
        "currency": "Měna",
        "quantity_open": "Počet ks",
        "avg_cost": "Průměrná nákupní cena",
        "cost_basis": "Nákupní hodnota",
        "current_price": "Aktuální cena",
        "market_value": "Tržní hodnota",
        "unrealized_pnl": "Nerealizovaný P/L",
        "yfinance_symbol": "Yahoo symbol",
    }

    display_df = stock_df.rename(columns=rename_map)

    numeric_cols = [
        "Počet ks",
        "Průměrná nákupní cena",
        "Nákupní hodnota",
        "Aktuální cena",
        "Tržní hodnota",
        "Nerealizovaný P/L",
    ]
    for col in numeric_cols:
        if col in display_df.columns:
            display_df[col] = pd.to_numeric(display_df[col], errors="coerce").round(4)

    st.markdown("### Otevřené pozice")
    st.dataframe(
        display_df[[
            "Ticker",
            "Název",
            "Měna",
            "Počet ks",
            "Průměrná nákupní cena",
            "Aktuální cena",
            "Tržní hodnota",
            "Nerealizovaný P/L",
        ]],
        use_container_width=True,
        hide_index=True
    )

    with st.expander("Historie stock transakcí"):
        stock_tx = get_stock_transactions()
        if stock_tx:
            stock_tx_df = pd.DataFrame(stock_tx).copy()

            for col in [
                "quantity",
                "price_per_share",
                "fx_rate_to_czk",
                "fee",
                "tax",
                "total_amount",
                "total_amount_czk",
            ]:
                if col in stock_tx_df.columns:
                    stock_tx_df[col] = pd.to_numeric(stock_tx_df[col], errors="coerce").round(4)

            st.dataframe(stock_tx_df, use_container_width=True, hide_index=True)
        else:
            st.info("Zatím nejsou evidované žádné stock transakce.")