import os
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(override=True)

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))

DATABASE_URL = f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"

try:
    logging.debug(f"Connecting to database {MYSQL_HOST}:{MYSQL_PORT}")  
    engine = create_engine(DATABASE_URL, echo=True)
    logging.debug("Database connection established successfully.")
except Exception as e:
    logging.error(f"Error connecting to the database: {e}")
    raise


def list_database():
    try:
        with engine.connect() as connection:
            results = connection.execute(text("SHOW DATABASES;")).fetchall()
            return {"databases": [row[0] for row in results]}
    except Exception as e:
        print("Error listing databases:", e)
        return {"error": str(e)}


def list_tables(database_name: str = None):
    db = database_name if database_name else MYSQL_DATABASE
    try:
        with engine.connect() as connection:
            results = connection.execute(
                text(f"SHOW TABLES FROM `{db}`")
            ).fetchall()
            return {"tables": [row[0] for row in results]}
    except Exception as e:
        print("Error listing tables:", e)
        return {"error": str(e)}

def list_columns(table_name: str):  
    try:
        with engine.connect() as connection:
            results = connection.execute(text(f"SHOW COLUMNS FROM `{table_name}`")).fetchall()
            return {"columns": [row[0] for row in results]}
    except Exception as e:
        print("Error listing columns:", e)
        return {"error": str(e)}


if __name__ == "__main__":
    print(list_database()) 