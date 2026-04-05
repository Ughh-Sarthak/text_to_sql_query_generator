from fastapi import FastAPI
from pydantic import BaseModel
from querygen import generate_sql_query, execute_sql_query

app = FastAPI()

class QueryRequest(BaseModel):
    query: str

@app.post("/generate_sql")
async def generate_sql(request: QueryRequest):
    sql_query = generate_sql_query(request.query)
    if not sql_query:
        return {"error": "Failed to generate SQL query."}
    return {"sql_query": sql_query}

@app.post("/execute_sql")
async def execute_sql(request: QueryRequest):
    sql_query = request.query
    results = execute_sql_query(sql_query)
    if results is None:
        return {"error": "Failed to execute SQL query."}
    
    serialized_rows = [list(row) for row in results["results"]]
    
    return {
        "results": serialized_rows,
        "index_suggestion": results["index_suggestion"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)