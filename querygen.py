import os
import sqlparse
import re
from groq import Groq
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from database import engine, list_columns, list_tables, list_database

load_dotenv(override=True)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MAX_TABLES = 5
MAX_COLUMNS_PER_TABLE = 10


# ── NEW: builds schema dict from database.py helpers ──────────────────────────
def get_schema() -> dict:
    """
    Returns a dict of the form:
        { table_name: [(col_name, dtype), ...], ... }
    Capped at MAX_TABLES tables and MAX_COLUMNS_PER_TABLE columns each.
    """
    schema = {}

    tables_result = list_tables()
    if "error" in tables_result:
        print(f"Error fetching tables: {tables_result['error']}")
        return schema

    tables = tables_result["tables"][:MAX_TABLES]

    for table in tables:
        columns_result = list_columns(table)          # Fix: pass table name
        if "error" in columns_result:
            print(f"Error fetching columns for {table}: {columns_result['error']}")
            continue

        # list_columns returns column names; pair each with a placeholder dtype
        cols = columns_result["columns"][:MAX_COLUMNS_PER_TABLE]
        schema[table] = [(col, "unknown") for col in cols]

    return schema


def clean_sql_output(response_text: str) -> str | None:
    clean_query = re.sub(r"```sql\n(.*?)\n```", r"\1", response_text, flags=re.DOTALL)
    sql_match = re.search(r"SELECT .*?;", clean_query, re.IGNORECASE | re.DOTALL)
    return sql_match.group(0) if sql_match else None


def validate_sql_query(query: str) -> tuple[bool, str | None]:
    try:
        parsed = sqlparse.parse(query)
        if not parsed:
            return False, "Query is empty or invalid."
        return True, None
    except Exception as e:
        return False, f"Error validating SQL query: {str(e)}"


def generate_sql_query(nl_question: str) -> str | None:
    schema = get_schema()

    if not schema:
        print("No schema available. Check your database connection.")
        return None

    schema_text = "\n".join(
        [
            f"Table: {table}\nColumns: {', '.join([col for col, dtype in columns])}"
            for table, columns in schema.items()
        ]
    )

    prompt = f"""You are an expert SQL query generator. Given a natural language question and the \
database schema, generate a valid SQL query that answers the question.
The database schema is as follows:
{schema_text}

Question: {nl_question}

Generate only the SQL query with no explanation. End the query with a semicolon."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        raw_sql_query = response.choices[0].message.content.strip()
        clean_query = clean_sql_output(raw_sql_query)
        return clean_query
    except Exception as e:
        print(f"Error generating SQL query: {str(e)}")
        return None


def suggest_index(sql_query: str) -> str:
    try:
        with engine.connect() as connection:
            result = connection.execute(text(f"EXPLAIN {sql_query}"))
            explain_output = result.fetchall()

        print("\nQuery Execution Plan:")
        for row in explain_output:
            print(row)

        return (
            "Consider adding indexes on columns used in WHERE clause "
            "or JOIN conditions for better performance."
        )
    except Exception as e:
        return f"Error suggesting index: {str(e)}"


def execute_sql_query(sql_query: str) -> dict | None:
    is_valid, error_message = validate_sql_query(sql_query)
    if not is_valid:
        print(f"Invalid SQL query: {error_message}")
        return None

    try:
        with engine.connect() as connection:
            result = connection.execute(text(sql_query))
            rows = result.fetchall()

        index_suggestion = suggest_index(sql_query)
        return {"results": rows, "index_suggestion": index_suggestion}
    except SQLAlchemyError as e:
        print(f"Database Execution Error: {str(e)}")
        return None


if __name__ == "__main__":
    user_input = input("Enter your Natural Language Query: ")
    sql_query = generate_sql_query(user_input)

    if sql_query:
        print(f"\nGenerated SQL Query:\n{sql_query}")
        execution_results = execute_sql_query(sql_query)
        if execution_results:
            print("\nQuery Results:")
            for row in execution_results["results"]:
                print(row)
            print(f"\nIndex Suggestion: {execution_results['index_suggestion']}")
        else:
            print("Failed to execute SQL query.")
    else:
        print("Failed to generate SQL query.")