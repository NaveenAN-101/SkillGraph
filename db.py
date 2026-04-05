from neo4j import GraphDatabase

URI = "bolt://127.0.0.1:7687"
USERNAME = "neo4j"
PASSWORD = "naveen05"

driver = GraphDatabase.driver(
    URI,
    auth=(USERNAME, PASSWORD)
)

def run_query(query: str, params: dict = None):
    with driver.session() as session:
        result = session.run(query, params or {})
        return [record.data() for record in result]
