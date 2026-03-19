from invest_service import init_invest_db, seed_default_stocks

if __name__ == "__main__":
    init_invest_db("data/portfolio.db")
    seed_default_stocks("data/portfolio.db")
    print("Migration complete.")
