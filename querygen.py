import os
import sqlparse
import re
from groq import Groq
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from database import get_schema, engine

load_dotenv(override=True)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def clean_sql_output(response_text):
    clean_query = re.sub(r"```sql\n(.*?)\n```", r"\1", response_text, flags=re.DOTALL)
    sql_match = re.search(r"SELECT .*?;", clean_query, re.IGNORECASE | re.DOTALL)
    return sql_match.group(0) if sql_match else None


def validate_sql_query(query):
    try:
        parsed = sqlparse.parse(query)
        if not parsed:
            return False, "Query is empty or invalid."
        return True, None
    except Exception as e:
        return False, f"Error validating SQL query: {str(e)}"


def generate_sql_query(nl_question):
    schema = get_schema()

    schema_text = "\n".join(
        [
            f"Table: {table}\nColumns: {', '.join([col for col, dtype in columns])}"
            for table, columns in schema.items()
        ]
    )

    prompt = f"""You are an expert SQL query generator. Given a natural language question and the database schema, generate a valid SQL query that answers the question.
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


def suggest_index(sql_query):
    try:
        with engine.connect() as connection:
            explain_query = f"EXPLAIN {sql_query}"
            result = connection.execute(text(explain_query))
            explain_output = result.fetchall()

        print("\nQuery Execution Plan:")
        for row in explain_output:
            print(row)

        return "Consider adding indexes on columns used in WHERE clause or JOIN conditions for better performance."
    except Exception as e:
        return f"Error suggesting index: {str(e)}"


def execute_sql_query(sql_query):
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
        print(f"Generated SQL Query:\n{sql_query}")
        execution_results = execute_sql_query(sql_query)
        if execution_results:
            print("Query Results:")
            for row in execution_results["results"]:
                print(row)
            print(f"Index Suggestion: {execution_results['index_suggestion']}")
        else:
            print("Failed to execute SQL query.")
    else:
        print("Failed to generate SQL query.")