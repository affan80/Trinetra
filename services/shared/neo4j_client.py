from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver

load_dotenv()

DEFAULT_NEO4J_URI = "bolt://localhost:7687"


@lru_cache(maxsize=1)
def get_neo4j_driver() -> Driver:
    uri = os.getenv("NEO4J_URI", DEFAULT_NEO4J_URI)
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    return GraphDatabase.driver(
        uri,
        auth=(user, password),
    )


def verify_connection() -> bool:
    try:
        driver = get_neo4j_driver()

        with driver.session() as session:
            session.run("RETURN 1")

        return True

    except Exception:
        return False

