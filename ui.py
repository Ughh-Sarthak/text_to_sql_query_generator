import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

def is_backend_running():
    try:
        r = requests.get(f"{API_URL}/docs", timeout=2)
        return r.status_code == 200
    except requests.exceptions.ConnectionError:
        return False

if not is_backend_running():
    st.error(
        "❌ Backend server is NOT running.\n\n"
        "Please start it with:\n"
        "```\nuvicorn app:app --reload --port 8000\n```"
    )
    st.stop()

st.success("✅ Backend connected")
st.title("AI SQL Query Generator and Executor")

# ── Sidebar ────────────────────────────────────────────────────────────────
st.sidebar.header("Database Explorer")

# List Databases
if st.sidebar.button("List Databases", key="list_db_btn"):
    response = requests.get(f"{API_URL}/list_databases/")
    if response.status_code == 200:
        databases = response.json().get("databases", [])
        st.sidebar.write("Available Databases:")
        st.sidebar.write(databases)
    else:
        st.sidebar.error("Failed to fetch databases.")

# List Tables
selected_db = st.sidebar.text_input("Enter database name to list tables:", key="db_input")
if st.sidebar.button("List Tables", key="list_tables_btn"):
    if not selected_db.strip():
        st.sidebar.warning("Please enter a database name.")
    else:
        response = requests.get(f"{API_URL}/list_tables/{selected_db}")
        if response.status_code == 200:
            tables = response.json().get("tables", [])
            st.sidebar.write("Tables in Database:")
            st.sidebar.write(tables)
        else:
            st.sidebar.error("Error fetching tables.")

# List Columns
selected_table = st.sidebar.text_input("Enter table name to list columns:", key="table_input")
if st.sidebar.button("List Columns", key="list_columns_btn"):
    if not selected_table.strip():
        st.sidebar.warning("Please enter a table name.")
    else:
        response = requests.get(f"{API_URL}/list_columns/{selected_table}")
        if response.status_code == 200:
            columns = response.json().get("columns", [])
            st.sidebar.write("Columns in Table:")
            st.sidebar.write(columns)
        else:
            st.sidebar.error("Error fetching columns.")

# ── Generate SQL ───────────────────────────────────────────────────────────
st.subheader("Generate SQL Query")
query_input = st.text_input("Enter your natural language question:", key="nl_input")

if st.button("Generate SQL", key="generate_btn"):
    if not query_input.strip():
        st.warning("Please enter a question first.")
    else:
        with st.spinner("Generating SQL..."):
            try:
                response = requests.post(
                    f"{API_URL}/generate_sql",
                    json={"query": query_input},
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()

                if "error" in data:
                    st.error(f"Generation error: {data['error']}")
                else:
                    sql_query = data.get("sql_query", "")
                    st.success("SQL Generated!")
                    st.code(sql_query, language="sql")
                    st.session_state["sql_query"] = sql_query

            except requests.exceptions.ConnectionError:
                st.error("Cannot reach backend. Is `uvicorn app:app --reload` running?")
            except requests.exceptions.Timeout:
                st.error("Request timed out. The model may be slow — try again.")
            except requests.exceptions.HTTPError as e:
                st.error(f"Server returned an error ({e.response.status_code}):")
                st.code(e.response.text)
            except requests.exceptions.JSONDecodeError:
                st.error("Backend returned an empty or invalid response.")
                st.code(response.text or "(empty response)")

# ── Execute SQL ────────────────────────────────────────────────────────────
if "sql_query" in st.session_state:
    st.subheader("Execute SQL Query")
    st.info(f"Ready to execute:\n```sql\n{st.session_state['sql_query']}\n```")

    if st.button("Execute Generated SQL", key="execute_btn"):
        with st.spinner("Executing..."):
            try:
                response = requests.post(
                    f"{API_URL}/execute_sql",
                    json={"query": st.session_state["sql_query"]},
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()

                if "error" in data:
                    st.error(f"Execution error: {data['error']}")
                else:
                    results = data.get("results", [])
                    index_suggestion = data.get("index_suggestion", "No tips available.")

                    st.subheader("Execution Results:")
                    if results:
                        st.dataframe(results)   # nicer than st.write for tabular data
                    else:
                        st.write("Query ran successfully but returned no rows.")

                    st.subheader("Index Suggestion:")
                    st.info(index_suggestion)

            except requests.exceptions.ConnectionError:
                st.error("Lost connection to backend.")
            except requests.exceptions.HTTPError as e:
                st.error(f"Server error ({e.response.status_code}):")
                st.code(e.response.text)
            except requests.exceptions.JSONDecodeError:
                st.error("Backend returned an empty or invalid response.")
                st.code(response.text or "(empty response)")