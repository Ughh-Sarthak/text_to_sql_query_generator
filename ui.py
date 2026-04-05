import streamlit as st
import requests

BASE_URL = "http://127.0.0.1:8000"

st.title("AI SQL Query Generator and Executor")

# ── Check if backend is alive ──────────────────────────────────────────────
def is_backend_running():
    try:
        r = requests.get(f"{BASE_URL}/docs", timeout=2)
        return r.status_code == 200
    except requests.exceptions.ConnectionError:
        return False

if not is_backend_running():
    st.error(
        "❌ Backend server is NOT running.\n\n"
        "Please start it with:\n"
        "```\nuvicorn app:app --reload --port 8000\n```"
    )
    st.stop()   # Don't render anything else until server is up

st.success("✅ Backend connected")

# ── Generate SQL ───────────────────────────────────────────────────────────
query_input = st.text_input("Enter your natural language question:")

if st.button("Generate SQL"):
    if not query_input.strip():
        st.warning("Please enter a question first.")
    else:
        with st.spinner("Generating SQL..."):
            try:
                response = requests.post(
                    f"{BASE_URL}/generate_sql",
                    json={"query": query_input},
                    timeout=30
                )
                response.raise_for_status()         # raises on 4xx / 5xx
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
                # Show the actual server error text
                st.error(f"Server returned an error ({e.response.status_code}):")
                st.code(e.response.text)
            except requests.exceptions.JSONDecodeError:
                st.error("Backend returned an empty or invalid response.")
                st.code(response.text or "(empty response)")

# ── Execute SQL ────────────────────────────────────────────────────────────
if "sql_query" in st.session_state:
    st.info(f"Ready to execute:\n```sql\n{st.session_state['sql_query']}\n```")

    if st.button("Execute Generated SQL"):
        with st.spinner("Executing..."):
            try:
                response = requests.post(
                    f"{BASE_URL}/execute_sql",
                    json={"query": st.session_state["sql_query"]},
                    timeout=30
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
                        st.write(results)
                    else:
                        st.write("Query ran successfully but returned no rows.")

                    st.subheader("Index Suggestion:")
                    st.write(index_suggestion)

            except requests.exceptions.ConnectionError:
                st.error("Lost connection to backend.")
            except requests.exceptions.HTTPError as e:
                st.error(f"Server error ({e.response.status_code}):")
                st.code(e.response.text)
            except requests.exceptions.JSONDecodeError:
                st.error("Backend returned an empty or invalid response.")
                st.code(response.text or "(empty response)")