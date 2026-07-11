# Neo4j Setup Documentation

## Objective

Set up Neo4j locally on macOS and verify the connection using Python.

## Steps Performed

### 1. Installed Neo4j

```bash
brew install neo4j
```

### 2. Started Neo4j Service

```bash
brew services start neo4j
```

### 3. Set Initial Password

```bash
neo4j-admin dbms set-initial-password neo4j123
```

### 4. Connected to Neo4j Browser



Verified using:

```cypher
RETURN "Neo4j Ready";
```

Output:

```
Neo4j Ready
```

### 5. Installed Neo4j Python Driver

```bash
pip3 install neo4j
```

### 6. Tested Python Connection

Python script:

```python
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "neo4j123"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

with driver.session() as session:
    result = session.run("RETURN 'Neo4j + Python Connected' AS msg")
    print(result.single()["msg"])
```

Output:

```
Neo4j + Python Connected
```

## Status

* Neo4j Installed
* Neo4j Service Running
* Browser Connected
* Python Driver Installed
* Python Connection Verified
* `.env` is added to `.gitignore`


