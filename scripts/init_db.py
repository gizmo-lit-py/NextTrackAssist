from sqlalchemy import text

from app.extensions import engine


def main():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    print("Database connection is ready. Run `python scripts/migrate.py` to apply migrations.")


if __name__ == "__main__":
    main()