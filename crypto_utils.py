import requests


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


def get_crypto_price(symbol: str) -> dict:
    coin_id = normalize_coin(symbol)

    result = {
        "symbol": coin_id,
        "price_usd": None,
        "price_czk": None,
        "error": None,
    }

    usdczk = 23.0

    # USD/CZK rate
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and "rates" in data and "CZK" in data["rates"]:
            usdczk = float(data["rates"]["CZK"])
    except Exception:
        try:
            r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=10)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict) and "rates" in data and "CZK" in data["rates"]:
                usdczk = float(data["rates"]["CZK"])
        except Exception:
            pass

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
                price_usd = float(data[coin_id]["usd"])
                result["price_usd"] = price_usd
                result["price_czk"] = price_usd * usdczk
                return result

        if r.status_code == 429:
            result["error"] = "CoinGecko rate limit"

    except Exception as e:
        result["error"] = str(e)

    # =========================================================
    # 2) BINANCE (FALLBACK)
    # =========================================================
    try:
        symbol_map = {
            "bitcoin": "BTCUSDT",
            "ethereum": "ETHUSDT",
            "solana": "SOLUSDT",
        }

        binance_symbol = symbol_map.get(coin_id)

        if binance_symbol:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={binance_symbol}"
            r = requests.get(url, timeout=10)

            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict) and "price" in data:
                    price_usd = float(data["price"])
                    result["price_usd"] = price_usd
                    result["price_czk"] = price_usd * usdczk
                    result["error"] = None
                    return result

    except Exception as e:
        result["error"] = f"Fallback error: {e}"

    return result