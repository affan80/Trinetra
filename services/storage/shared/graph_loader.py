from services.shared.neo4j_client import get_neo4j_driver


def load_article(article: dict):
    """
    Store one processed article into Neo4j.
    """

    driver = get_neo4j_driver()

    with driver.session() as session:

        session.run(
            """
            MERGE (a:Article {url:$url})
            SET a.title=$title,
                a.text=$text,
                a.published_at=$published_at

            MERGE (au:Author {name:$author})

            MERGE (s:Source {
                name:$source_name,
                type:$source_type
            })

            MERGE (au)-[:WROTE]->(a)
            MERGE (a)-[:PUBLISHED_BY]->(s)
            """,
            article,
        )

        topics = article.get("topic_tags") or []

        for topic in topics:
            session.run(
                """
                MATCH (a:Article {url:$url})
                MERGE (t:Topic {name:$topic})
                MERGE (a)-[:HAS_TOPIC]->(t)
                """,
                {
                    "url": article["url"],
                    "topic": topic,
                },
            )
