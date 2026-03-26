# invest_stock_service.py

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "portfolio.db"

FX_SYMBOLS = {
    "CZK": None,
    "USD": "USDCZK=X",
    "EUR": "EURCZK=X",
}


# =========================================================
# DB HELPERS
# =========================================================

def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path or DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_stock_tables(db_path: Optional[Path] = None) -> None:
    """
    Additive migration:
    creates new stock-related tables if they don't exist.
    Does NOT modify or remove any existing tables.
    """
    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL UNIQUE,
            name TEXT,
            isin TEXT,
            exchange TEXT,
            currency TEXT,
            yfinance_symbol TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_asset_id INTEGER NOT NULL,
            broker TEXT DEFAULT 'XTB',
            source TEXT DEFAULT 'MY_TRADES',
            transaction_type TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            settlement_date TEXT,
            quantity REAL NOT NULL,
            price_per_share REAL NOT NULL,
            currency TEXT,
            fx_rate_to_czk REAL,
            fee REAL DEFAULT 0,
            tax REAL DEFAULT 0,
            total_amount REAL,
            total_amount_czk REAL,
            external_id TEXT,
            import_log_id INTEGER,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(stock_asset_id) REFERENCES stock_assets(id)
        )
    """)

    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_stock_transactions_external_id
        ON stock_transactions(external_id)
        WHERE external_id IS NOT NULL
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_stock_transactions_asset_date
        ON stock_transactions(stock_asset_id, trade_date)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_stock_assets_ticker
        ON stock_assets(ticker)
    """)

    conn.commit()
    conn.close()


# =========================================================
# NORMALIZATION / FX HELPERS
# =========================================================

def normalize_stock_ticker(ticker: str) -> str:
    return str(ticker or "").strip().upper()


def guess_yfinance_symbol(ticker: str) -> str:
    """
    Conservative mapping:
    - AMZN.US -> AMZN
    - AMZN.USA -> AMZN
    - AAPL -> AAPL
    - BMW.DE -> BMW.DE
    """
    t = normalize_stock_ticker(ticker)

    if t.endswith(".US"):
        return t[:-3]
    if t.endswith(".USA"):
        return t[:-4]

    return t


def normalize_yfinance_symbol(yfinance_symbol: Optional[str], ticker: str) -> str:
    candidate = str(yfinance_symbol).strip().upper() if yfinance_symbol else ""
    if not candidate:
        return guess_yfinance_symbol(ticker)
    return guess_yfinance_symbol(candidate)


def get_stock_current_price(symbol: str) -> Optional[float]:
    """
    Safe helper.
    Returns None if yfinance is unavailable or fetch fails.
    """
    if yf is None or not symbol:
        return None

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d", auto_adjust=False)
        if hist.empty:
            return None
        closes = hist["Close"].dropna()
        if closes.empty:
            return None
        return float(closes.iloc[-1])
    except Exception:
        return None


def get_fx_rate_to_czk(currency: Optional[str]) -> float:
    ccy = str(currency or "CZK").strip().upper()
    fx_symbol = FX_SYMBOLS.get(ccy)

    if fx_symbol is None:
        return 1.0

    fx = get_stock_current_price(fx_symbol)
    if fx is None or fx <= 0:
        return 1.0

    return float(fx)


# =========================================================
# ASSET REGISTRY
# =========================================================

def get_or_create_stock_asset(
    ticker: str,
    name: Optional[str] = None,
    isin: Optional[str] = None,
    exchange: Optional[str] = None,
    currency: Optional[str] = None,
    yfinance_symbol: Optional[str] = None,
    db_path: Optional[Path] = None
) -> int:
    ticker = normalize_stock_ticker(ticker)
    currency = str(currency).strip().upper() if currency else None
    yfinance_symbol = normalize_yfinance_symbol(yfinance_symbol, ticker)

    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.execute("SELECT id FROM stock_assets WHERE ticker = ?", (ticker,))
    row = cur.fetchone()

    if row:
        asset_id = row["id"]

        cur.execute("""
            UPDATE stock_assets
            SET
                name = COALESCE(?, name),
                isin = COALESCE(?, isin),
                exchange = COALESCE(?, exchange),
                currency = COALESCE(?, currency),
                yfinance_symbol = COALESCE(?, yfinance_symbol)
            WHERE id = ?
        """, (name, isin, exchange, currency, yfinance_symbol, asset_id))

        conn.commit()
        conn.close()
        return asset_id

    cur.execute("""
        INSERT INTO stock_assets (
            ticker, name, isin, exchange, currency, yfinance_symbol
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (ticker, name, isin, exchange, currency, yfinance_symbol))

    asset_id = cur.lastrowid
    conn.commit()
    conn.close()
    return asset_id


def get_stock_assets(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    df = pd.read_sql_query("""
        SELECT *
        FROM stock_assets
        WHERE is_active = 1
        ORDER BY ticker
    """, conn)
    conn.close()
    return df.to_dict(orient="records")


# =========================================================
# TRANSACTIONS
# =========================================================

def add_stock_transaction(
    ticker: str,
    transaction_type: Optional[str] = None,
    trade_date: Optional[str] = None,
    quantity: float = 0.0,
    price_per_share: float = 0.0,
    currency: str = "USD",
    name: Optional[str] = None,
    isin: Optional[str] = None,
    exchange: Optional[str] = None,
    yfinance_symbol: Optional[str] = None,
    settlement_date: Optional[str] = None,
    fx_rate_to_czk: Optional[float] = None,
    fee: float = 0.0,
    tax: float = 0.0,
    total_amount: Optional[float] = None,
    total_amount_czk: Optional[float] = None,
    external_id: Optional[str] = None,
    import_log_id: Optional[int] = None,
    notes: Optional[str] = None,
    db_path: Optional[Path] = None,
    side: Optional[str] = None,
    source: Optional[str] = None,
    broker: Optional[str] = None,
) -> int:
    """
    Additive insert.
    Safe for repeated imports if external_id is stable.

    Backward compatible:
    - accepts transaction_type="BUY"/"SELL"
    - also accepts side="BUY"/"SELL" from manual UI
    - accepts source / broker overrides without breaking older calls
    """
    init_stock_tables(db_path)

    ticker = normalize_stock_ticker(ticker)
    currency = str(currency or "USD").strip().upper()
    resolved_transaction_type = (transaction_type or side or "").strip().upper()
    resolved_source = str(source).strip().upper() if source else "MY_TRADES"
    resolved_broker = str(broker).strip().upper() if broker else "XTB"
    resolved_yfinance_symbol = normalize_yfinance_symbol(yfinance_symbol, ticker)

    if not resolved_transaction_type:
        raise ValueError("Chybí transaction_type / side.")

    if resolved_transaction_type not in {"BUY", "SELL"}:
        raise ValueError(f"Neplatný transaction_type: {resolved_transaction_type}")

    if not trade_date:
        raise ValueError("Chybí trade_date.")

    quantity = float(quantity)
    price_per_share = float(price_per_share)
    fee = float(fee or 0.0)
    tax = float(tax or 0.0)

    if quantity <= 0:
        raise ValueError("Quantity musí být větší než 0.")

    if price_per_share <= 0:
        raise ValueError("Price per share musí být větší než 0.")

    asset_id = get_or_create_stock_asset(
        ticker=ticker,
        name=name,
        isin=isin,
        exchange=exchange,
        currency=currency,
        yfinance_symbol=resolved_yfinance_symbol,
        db_path=db_path
    )

    conn = get_connection(db_path)
    cur = conn.cursor()

    if external_id:
        cur.execute("""
            SELECT id FROM stock_transactions WHERE external_id = ?
        """, (external_id,))
        existing = cur.fetchone()
        if existing:
            conn.close()
            return existing["id"]

    if total_amount is None:
        total_amount = (quantity * price_per_share) + fee + tax

    if fx_rate_to_czk is None or float(fx_rate_to_czk or 0) <= 0:
        fx_rate_to_czk = get_fx_rate_to_czk(currency)

    if total_amount_czk is None:
        total_amount_czk = float(total_amount) * float(fx_rate_to_czk)

    cur.execute("""
        INSERT INTO stock_transactions (
            stock_asset_id,
            broker,
            source,
            transaction_type,
            trade_date,
            settlement_date,
            quantity,
            price_per_share,
            currency,
            fx_rate_to_czk,
            fee,
            tax,
            total_amount,
            total_amount_czk,
            external_id,
            import_log_id,
            notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        asset_id,
        resolved_broker,
        resolved_source,
        resolved_transaction_type,
        trade_date,
        settlement_date,
        quantity,
        price_per_share,
        currency,
        fx_rate_to_czk,
        fee,
        tax,
        total_amount,
        total_amount_czk,
        external_id,
        import_log_id,
        notes
    ))

    tx_id = cur.lastrowid
    conn.commit()
    conn.close()
    return tx_id


def get_stock_transactions(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    df = pd.read_sql_query("""
        SELECT
            st.id,
            sa.ticker,
            sa.name,
            sa.currency AS asset_currency,
            sa.yfinance_symbol,
            st.broker,
            st.source,
            st.transaction_type,
            st.trade_date,
            st.settlement_date,
            st.quantity,
            st.price_per_share,
            st.currency,
            st.fx_rate_to_czk,
            st.fee,
            st.tax,
            st.total_amount,
            st.total_amount_czk,
            st.external_id,
            st.notes,
            st.created_at
        FROM stock_transactions st
        JOIN stock_assets sa ON sa.id = st.stock_asset_id
        ORDER BY st.trade_date DESC, st.id DESC
    """, conn)
    conn.close()
    return df.to_dict(orient="records")


def get_stock_transactions_df(db_path: Optional[Path] = None) -> pd.DataFrame:
    conn = get_connection(db_path)
    df = pd.read_sql_query("""
        SELECT
            st.id,
            st.stock_asset_id,
            sa.ticker,
            sa.name,
            COALESCE(sa.currency, st.currency) AS asset_currency,
            COALESCE(sa.yfinance_symbol, sa.ticker) AS yfinance_symbol,
            st.broker,
            st.source,
            st.transaction_type,
            st.trade_date,
            st.quantity,
            st.price_per_share,
            st.currency,
            st.fx_rate_to_czk,
            st.fee,
            st.tax,
            st.total_amount,
            st.total_amount_czk,
            st.external_id
        FROM stock_transactions st
        JOIN stock_assets sa ON sa.id = st.stock_asset_id
        ORDER BY st.trade_date ASC, st.id ASC
    """, conn)
    conn.close()
    return df


def get_stock_transaction_detail(transaction_id: int, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    row = conn.execute("""
        SELECT
            st.id,
            st.stock_asset_id,
            sa.ticker,
            sa.name,
            sa.yfinance_symbol,
            st.broker,
            st.source,
            st.transaction_type,
            st.trade_date,
            st.settlement_date,
            st.quantity,
            st.price_per_share,
            st.currency,
            st.fx_rate_to_czk,
            st.fee,
            st.tax,
            st.total_amount,
            st.total_amount_czk,
            st.external_id,
            st.import_log_id,
            st.notes,
            st.created_at
        FROM stock_transactions st
        JOIN stock_assets sa ON sa.id = st.stock_asset_id
        WHERE st.id = ?
        LIMIT 1
    """, (int(transaction_id),)).fetchone()
    conn.close()

    if not row:
        return None

    return dict(row)


def delete_manual_stock_transaction(transaction_id: int, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Safe delete:
    - deletes only stock transaction rows
    - allows delete only for manual entries
    - protects imported / external rows
    """
    tx = get_stock_transaction_detail(transaction_id, db_path=db_path)

    if not tx:
        return {
            "deleted": False,
            "reason": "not_found",
            "message": "Transakce nebyla nalezena."
        }

    source_value = str(tx.get("source") or "").strip().lower()
    external_id = tx.get("external_id")

    if source_value != "manual":
        return {
            "deleted": False,
            "reason": "not_manual",
            "message": "Smazat lze pouze ručně zadané stock transakce."
        }

    if external_id not in (None, ""):
        return {
            "deleted": False,
            "reason": "has_external_id",
            "message": "Transakce s external_id nelze mazat touto akcí."
        }

    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM stock_transactions WHERE id = ?", (int(transaction_id),))
    deleted_rows = cur.rowcount
    conn.commit()
    conn.close()

    if deleted_rows <= 0:
        return {
            "deleted": False,
            "reason": "not_deleted",
            "message": "Transakci se nepodařilo smazat."
        }

    return {
        "deleted": True,
        "reason": None,
        "message": "Ruční stock transakce byla smazána.",
        "transaction_id": int(transaction_id),
        "ticker": tx.get("ticker"),
        "name": tx.get("name"),
    }


# =========================================================
# POSITION CALCULATION
# =========================================================

def get_stock_positions(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Computes open positions from stock_transactions.

    Safe rules:
    - avg_cost / current_price stay in native asset currency
    - cost_basis / market_value / unrealized_pnl are returned in CZK
      because UI summary cards format them as CZK
    """
    df = get_stock_transactions_df(db_path)

    if df.empty:
        return []

    positions = []

    for ticker, group in df.groupby("ticker", sort=True):
        group = group.sort_values(["trade_date", "id"])

        quantity_open = 0.0
        total_cost_native = 0.0
        total_cost_czk = 0.0

        asset_name = group["name"].iloc[0]
        asset_currency = str(group["asset_currency"].iloc[0] or "USD").strip().upper()
        yfinance_symbol = normalize_yfinance_symbol(group["yfinance_symbol"].iloc[0], ticker)

        for _, row in group.iterrows():
            side = str(row["transaction_type"]).upper()
            qty = float(row["quantity"] or 0.0)
            price_native = float(row["price_per_share"] or 0.0)
            fee = float(row["fee"] or 0.0)
            tax = float(row["tax"] or 0.0)

            tx_total_native = row["total_amount"]
            tx_total_czk = row["total_amount_czk"]
            tx_fx = row["fx_rate_to_czk"]

            if pd.isna(tx_total_native) or tx_total_native is None:
                tx_total_native = (qty * price_native) + fee + tax
            else:
                tx_total_native = float(tx_total_native)

            if pd.isna(tx_fx) or tx_fx is None or float(tx_fx) <= 0:
                tx_fx = get_fx_rate_to_czk(asset_currency)
            else:
                tx_fx = float(tx_fx)

            if pd.isna(tx_total_czk) or tx_total_czk is None:
                tx_total_czk = float(tx_total_native) * tx_fx
            else:
                tx_total_czk = float(tx_total_czk)

            if side == "BUY":
                quantity_open += qty
                total_cost_native += tx_total_native
                total_cost_czk += tx_total_czk

            elif side == "SELL":
                if quantity_open > 0:
                    avg_cost_native = total_cost_native / quantity_open if quantity_open > 0 else 0.0
                    avg_cost_czk = total_cost_czk / quantity_open if quantity_open > 0 else 0.0

                    quantity_open -= qty
                    total_cost_native -= avg_cost_native * qty
                    total_cost_czk -= avg_cost_czk * qty

                    if quantity_open < 0:
                        quantity_open = 0.0
                        total_cost_native = 0.0
                        total_cost_czk = 0.0

        if quantity_open <= 0:
            continue

        avg_cost_native = (total_cost_native / quantity_open) if quantity_open > 0 else 0.0

        current_price_native = get_stock_current_price(yfinance_symbol)
        current_fx_to_czk = get_fx_rate_to_czk(asset_currency)

        current_price_czk = (
            current_price_native * current_fx_to_czk
            if current_price_native is not None else None
        )
        market_value_czk = (
            quantity_open * current_price_czk
            if current_price_czk is not None else None
        )
        unrealized_pnl_czk = (
            market_value_czk - total_cost_czk
            if market_value_czk is not None else None
        )

        positions.append({
            "ticker": normalize_stock_ticker(ticker),
            "name": asset_name,
            "currency": asset_currency,
            "yfinance_symbol": yfinance_symbol,
            "quantity_open": round(quantity_open, 8),
            "avg_cost": round(avg_cost_native, 4),
            "cost_basis": round(total_cost_czk, 4),
            "current_price": round(current_price_native, 4) if current_price_native is not None else None,
            "current_price_czk": round(current_price_czk, 4) if current_price_czk is not None else None,
            "market_value": round(market_value_czk, 4) if market_value_czk is not None else None,
            "unrealized_pnl": round(unrealized_pnl_czk, 4) if unrealized_pnl_czk is not None else None,
            "fx_rate_to_czk": round(current_fx_to_czk, 6) if current_fx_to_czk is not None else None,
        })

    return positions


def get_stock_portfolio_summary(db_path: Optional[Path] = None) -> Dict[str, Any]:
    positions = get_stock_positions(db_path)

    total_cost = sum(float(p["cost_basis"] or 0.0) for p in positions)
    total_market_value = sum(float(p["market_value"] or 0.0) for p in positions)
    total_unrealized = sum(float(p["unrealized_pnl"] or 0.0) for p in positions)

    return {
        "positions_count": len(positions),
        "total_cost_basis": round(total_cost, 4),
        "total_market_value": round(total_market_value, 4),
        "total_unrealized_pnl": round(total_unrealized, 4),
        "positions": positions,
    }


# =========================================================
# XTB IMPORT - STOCKS ONLY
# =========================================================

def classify_xtb_row_for_stocks(row: pd.Series) -> bool:
    """
    Conservative classifier:
    returns True only for XTB 'My Trades' rows.
    Adjust column names according to your export format.
    """
    combined = " | ".join([str(v) for v in row.values if pd.notna(v)]).upper()

    has_my_trades = "MY TRADES" in combined
    has_investment_plan = "INVESTMENT PLAN" in combined or "INVESTMENT PLANS" in combined

    if has_my_trades and not has_investment_plan:
        return True

    if "STOCK" in combined and not has_investment_plan:
        return True

    return False


def import_xtb_my_trades_from_dataframe(
    df: pd.DataFrame,
    ticker_column: str = "Ticker",
    name_column: str = "Name",
    side_column: str = "Side",
    date_column: str = "Trade date",
    quantity_column: str = "Quantity",
    price_column: str = "Price",
    currency_column: str = "Currency",
    external_id_column: Optional[str] = None,
    yfinance_symbol_map: Optional[Dict[str, str]] = None,
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Imports only stock trades from XTB export dataframe.
    This function is intentionally separated from ETF import logic.
    """
    init_stock_tables(db_path)

    imported = 0
    skipped = 0
    errors = []

    yfinance_symbol_map = yfinance_symbol_map or {}

    for idx, row in df.iterrows():
        try:
            if not classify_xtb_row_for_stocks(row):
                skipped += 1
                continue

            ticker = normalize_stock_ticker(row[ticker_column])
            name = str(row[name_column]).strip() if name_column in row and pd.notna(row[name_column]) else ticker
            side = str(row[side_column]).strip().upper()
            trade_date = pd.to_datetime(row[date_column]).strftime("%Y-%m-%d")
            quantity = float(row[quantity_column])
            price = float(row[price_column])
            currency = str(row[currency_column]).strip().upper()

            ext_id = None
            if external_id_column and external_id_column in row and pd.notna(row[external_id_column]):
                ext_id = str(row[external_id_column]).strip()

            raw_yf_symbol = yfinance_symbol_map.get(ticker, ticker)
            resolved_yf_symbol = normalize_yfinance_symbol(raw_yf_symbol, ticker)

            add_stock_transaction(
                ticker=ticker,
                transaction_type=side,
                trade_date=trade_date,
                quantity=quantity,
                price_per_share=price,
                currency=currency,
                name=name,
                yfinance_symbol=resolved_yf_symbol,
                external_id=ext_id,
                db_path=db_path
            )
            imported += 1

        except Exception as e:
            errors.append({"row": idx, "error": str(e)})

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors
    }


# =========================================================
# SAFE BOOTSTRAP
# =========================================================

def bootstrap_stock_module(db_path: Optional[Path] = None) -> None:
    init_stock_tables(db_path)