from pathlib import Path
import sqlite3
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent
DB_PATH = ROOT_DIR / "data" / "portfolio.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def read_df(query, params=()):
    conn = get_conn()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def fmt_czk(v: float) -> str:
    return f"{float(v):,.2f} CZK".replace(",", " ")


def get_plans():
    return read_df("""
        SELECT *
        FROM investment_plans
        WHERE status = 'active'
        ORDER BY sort_order, plan_name
    """)


def get_plan(plan_id: str):
    df = read_df("SELECT * FROM investment_plans WHERE plan_id = ?", (plan_id,))
    return None if df.empty else df.iloc[0].to_dict()


def get_assets(plan_id: str):
    return read_df("""
        SELECT *
        FROM plan_assets
        WHERE plan_id = ? AND is_active = 1
        ORDER BY sort_order, asset_name
    """, (plan_id,))


def get_cash(plan_id: str):
    return read_df("""
        SELECT *
        FROM cash_transactions
        WHERE plan_id = ?
        ORDER BY tx_date DESC, cash_tx_id DESC
    """, (plan_id,))


def get_trades(plan_id: str):
    return read_df("""
        SELECT *
        FROM investment_transactions
        WHERE plan_id = ?
        ORDER BY tx_date DESC, tx_id DESC
    """, (plan_id,))


def get_planned_orders(plan_id: str):
    return read_df("""
        SELECT *
        FROM planned_orders
        WHERE plan_id = ? AND status = 'planned'
        ORDER BY priority ASC, planned_date ASC, planned_order_id DESC
    """, (plan_id,))


def get_latest_prices():
    return read_df("""
        SELECT p1.*
        FROM asset_prices p1
        INNER JOIN (
            SELECT ticker, MAX(price_id) AS max_id
            FROM asset_prices
            GROUP BY ticker
        ) p2 ON p1.price_id = p2.max_id
        ORDER BY p1.ticker
    """)


def get_snapshots(plan_id: str):
    return read_df("""
        SELECT snapshot_date, portfolio_value, positions_value, cash_balance, invested_amount, profit_loss
        FROM portfolio_snapshots
        WHERE plan_id = ?
        ORDER BY snapshot_date
    """, (plan_id,))


def get_import_logs():
    return read_df("""
        SELECT *
        FROM import_logs
        ORDER BY import_id DESC
        LIMIT 20
    """)


def compute_summary(plan_id: str):
    cash_df = get_cash(plan_id)
    trades_df = get_trades(plan_id)
    assets_df = get_assets(plan_id)
    prices_df = get_latest_prices()

    cash_in = cash_df.loc[cash_df["tx_type"] == "deposit", "amount"].sum() if not cash_df.empty else 0.0
    cash_out = cash_df.loc[cash_df["tx_type"] == "withdrawal", "amount"].sum() if not cash_df.empty else 0.0
    cash_in_out = float(cash_in - cash_out)

    if trades_df.empty:
        positions = pd.DataFrame(
            columns=[
                "ticker", "asset_name", "quantity", "avg_buy_price",
                "invested_amount", "current_price", "current_value",
                "profit_loss", "profit_loss_pct", "allocation_pct"
            ]
        )
        positions_value = 0.0
        cash_balance = cash_in_out
        portfolio_value = cash_balance
        profit_loss = portfolio_value - cash_in_out

        return {
            "portfolio_value": float(portfolio_value),
            "positions_value": float(positions_value),
            "cash_balance": float(cash_balance),
            "cash_in_out": float(cash_in_out),
            "invested_amount": 0.0,
            "profit_loss": float(profit_loss),
            "profit_loss_pct": 0.0,
            "positions": positions,
        }

    tx = trades_df.copy()
    tx["signed_qty"] = tx.apply(
        lambda r: r["quantity"] if r["tx_type"] == "buy" else -r["quantity"],
        axis=1
    )

    qty = tx.groupby("ticker", as_index=False)["signed_qty"].sum().rename(
        columns={"signed_qty": "quantity"}
    )

    buys = tx[tx["tx_type"] == "buy"].copy()
    buy_sum = buys.groupby("ticker", as_index=False).agg(
        bought_qty=("quantity", "sum"),
        buy_total=("total_value", "sum"),
    )
    buy_sum["avg_buy_price"] = buy_sum.apply(
        lambda r: r["buy_total"] / r["bought_qty"] if r["bought_qty"] else 0.0,
        axis=1,
    )

    positions = (
        assets_df[["ticker", "asset_name"]]
        .merge(qty, on="ticker", how="left")
        .merge(buy_sum[["ticker", "buy_total", "avg_buy_price"]], on="ticker", how="left")
        .merge(prices_df[["ticker", "price"]], on="ticker", how="left")
    )

    positions["quantity"] = positions["quantity"].fillna(0.0)
    positions["buy_total"] = positions["buy_total"].fillna(0.0)
    positions["avg_buy_price"] = positions["avg_buy_price"].fillna(0.0)
    positions["price"] = positions["price"].fillna(0.0)

    positions = positions[positions["quantity"] > 0].copy()
    positions["invested_amount"] = positions["quantity"] * positions["avg_buy_price"]
    positions["current_price"] = positions["price"]
    positions["current_value"] = positions["quantity"] * positions["current_price"]
    positions["profit_loss"] = positions["current_value"] - positions["invested_amount"]
    positions["profit_loss_pct"] = positions.apply(
        lambda r: (r["profit_loss"] / r["invested_amount"] * 100) if r["invested_amount"] else 0.0,
        axis=1,
    )

    invested_amount = float(positions["invested_amount"].sum()) if not positions.empty else 0.0
    positions_value = float(positions["current_value"].sum()) if not positions.empty else 0.0
    buy_total = trades_df.loc[trades_df["tx_type"] == "buy", "total_value"].sum() if not trades_df.empty else 0.0
    sell_total = trades_df.loc[trades_df["tx_type"] == "sell", "total_value"].sum() if not trades_df.empty else 0.0
    cash_balance = float(cash_in_out - buy_total + sell_total)
    portfolio_value = positions_value + cash_balance
    profit_loss = portfolio_value - cash_in_out

    positions["allocation_pct"] = positions["current_value"] / portfolio_value * 100 if portfolio_value else 0.0

    return {
        "portfolio_value": float(portfolio_value),
        "positions_value": float(positions_value),
        "cash_balance": float(cash_balance),
        "cash_in_out": float(cash_in_out),
        "invested_amount": float(invested_amount),
        "profit_loss": float(profit_loss),
        "profit_loss_pct": (profit_loss / cash_in_out * 100) if cash_in_out else 0.0,
        "positions": positions.sort_values("current_value", ascending=False),
    }


def compute_total_summary():
    plans_df = get_plans()

    if plans_df.empty:
        return {
            "portfolio_value": 0.0,
            "positions_value": 0.0,
            "cash_balance": 0.0,
            "cash_in_out": 0.0,
            "invested_amount": 0.0,
            "profit_loss": 0.0,
            "profit_loss_pct": 0.0,
            "plans": [],
        }

    total = {
        "portfolio_value": 0.0,
        "positions_value": 0.0,
        "cash_balance": 0.0,
        "cash_in_out": 0.0,
        "invested_amount": 0.0,
        "profit_loss": 0.0,
    }

    plan_summaries = []

    for _, plan in plans_df.iterrows():
        summary = compute_summary(plan["plan_id"])

        total["portfolio_value"] += summary["portfolio_value"]
        total["positions_value"] += summary["positions_value"]
        total["cash_balance"] += summary["cash_balance"]
        total["cash_in_out"] += summary["cash_in_out"]
        total["invested_amount"] += summary["invested_amount"]
        total["profit_loss"] += summary["profit_loss"]

        plan_summaries.append({
            "plan_id": plan["plan_id"],
            "plan_name": plan.get("plan_name", plan["plan_id"]),
            "display_name": plan.get("display_name", plan["plan_id"]),
            "icon": plan.get("icon", "📈"),
            "portfolio_value": summary["portfolio_value"],
            "positions_value": summary["positions_value"],
            "cash_balance": summary["cash_balance"],
            "cash_in_out": summary["cash_in_out"],
            "invested_amount": summary["invested_amount"],
            "profit_loss": summary["profit_loss"],
            "profit_loss_pct": summary["profit_loss_pct"],
        })

    total["profit_loss_pct"] = (
        total["profit_loss"] / total["cash_in_out"] * 100 if total["cash_in_out"] else 0.0
    )
    total["plans"] = sorted(plan_summaries, key=lambda x: x["portfolio_value"], reverse=True)

    return total


def get_portfolio_overview_payload():
    total = compute_total_summary()
    return {
        "total_value_czk": total["portfolio_value"],
        "positions_value_czk": total["positions_value"],
        "cash_balance_czk": total["cash_balance"],
        "invested_amount_czk": total["invested_amount"],
        "profit_loss_czk": total["profit_loss"],
        "profit_loss_pct": total["profit_loss_pct"],
        "plans": total["plans"],
    }


def get_asset_transactions(plan_id: str, ticker: str):
    return read_df("""
        SELECT *
        FROM investment_transactions
        WHERE plan_id = ? AND ticker = ?
        ORDER BY tx_date DESC, tx_id DESC
    """, (plan_id, ticker))


def get_latest_price_for_ticker(ticker: str):
    df = read_df("""
        SELECT *
        FROM asset_prices
        WHERE ticker = ?
        ORDER BY price_id DESC
        LIMIT 1
    """, (ticker,))
    return None if df.empty else df.iloc[0].to_dict()


def get_plan_assets_overview(plan_id: str):
    summary = compute_summary(plan_id)
    positions = summary["positions"].copy()
    if positions.empty:
        return positions
    return positions.sort_values("current_value", ascending=False).reset_index(drop=True)


def compute_asset_summary(plan_id: str, ticker: str):
    positions = get_plan_assets_overview(plan_id)
    if positions.empty:
        return None

    asset = positions[positions["ticker"] == ticker]
    if asset.empty:
        return None

    row = asset.iloc[0]
    latest_price = get_latest_price_for_ticker(ticker)
    tx_df = get_asset_transactions(plan_id, ticker)

    buys = tx_df[tx_df["tx_type"] == "buy"].copy() if not tx_df.empty else pd.DataFrame()
    sells = tx_df[tx_df["tx_type"] == "sell"].copy() if not tx_df.empty else pd.DataFrame()

    return {
        "ticker": row["ticker"],
        "asset_name": row["asset_name"],
        "quantity": float(row["quantity"]),
        "avg_buy_price": float(row["avg_buy_price"]),
        "invested_amount": float(row["invested_amount"]),
        "current_price": float(row["current_price"]),
        "current_value": float(row["current_value"]),
        "profit_loss": float(row["profit_loss"]),
        "profit_loss_pct": float(row["profit_loss_pct"]),
        "allocation_pct": float(row["allocation_pct"]),
        "buy_count": int(len(buys)),
        "sell_count": int(len(sells)),
        "latest_price_date": latest_price["price_date"] if latest_price else None,
        "latest_price_source": latest_price["source"] if latest_price else None,
        "transactions": tx_df,
    }
# =========================================================
# STOCK EXTENSION (ADDITIVE ONLY)
# =========================================================

try:
    from invest_stock_service import (
        bootstrap_stock_module,
        get_stock_assets,
        get_stock_transactions,
        get_stock_positions,
        get_stock_portfolio_summary,
        import_xtb_my_trades_from_dataframe,
        add_stock_transaction,
    )
except Exception:
    # bezpečné fallback chování, aby se existující app nerozbila
    def bootstrap_stock_module(*args, **kwargs):
        return None

    def get_stock_assets(*args, **kwargs):
        return []

    def get_stock_transactions(*args, **kwargs):
        return []

    def get_stock_positions(*args, **kwargs):
        return []

    def get_stock_portfolio_summary(*args, **kwargs):
        return {
            "positions_count": 0,
            "total_cost_basis": 0.0,
            "total_market_value": 0.0,
            "total_unrealized_pnl": 0.0,
            "positions": [],
        }

    def import_xtb_my_trades_from_dataframe(*args, **kwargs):
        return {"imported": 0, "skipped": 0, "errors": ["stock module unavailable"]}

    def add_stock_transaction(*args, **kwargs):
        return None