from .graph import run

result = run("Which routes have the highest delay?", session_id="user-123")
print(result.answer)
print(result.cypher_queries)   # for audit / debug
print(result.iterations_used)  # for audit / debug