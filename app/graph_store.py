"""Neo4j graph database operations for GraphRAG system."""

from neo4j import GraphDatabase


class GraphStore:
    """Handles all Neo4j operations (read + write)."""

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        if self.driver:
            self.driver.close()

    def verify_connection(self) -> bool:
        try:
            self.driver.verify_connectivity()
            return True
        except Exception:
            return False

    # =====================================
    # WRITE OPERATIONS
    # =====================================

    def create_entity(self, entity: dict, source_name: str):
        """Create or update an entity node."""
        query = """
        MERGE (e:Entity {name: $name})
        SET e.type = $type,
            e.source = $source_name,
            e.updated_at = timestamp()
        """

        with self.driver.session() as session:
            session.run(
                query,
                name=entity["name"],
                type=entity.get("type", "UNKNOWN"),
                source_name=source_name,
            )

    def create_relationship(self, rel: dict, source_name: str):
        """Create relationship between entities."""

        rel_type = rel.get("relation", "RELATED_TO")
        safe_type = "".join(c if c.isalnum() or c == "_" else "_" for c in rel_type)

        query = f"""
        MATCH (a:Entity {{name: $source}})
        MATCH (b:Entity {{name: $target}})
        MERGE (a)-[r:{safe_type}]->(b)
        SET r.source = $source_name,
            r.updated_at = timestamp()
        """

        with self.driver.session() as session:
            session.run(
                query,
                source=rel["source"],
                target=rel["target"],
                source_name=source_name,
            )

    def store_extraction(self, entities: list[dict], relationships: list[dict], source_name: str):
        """Store entities + relationships."""
        entity_count = 0
        rel_count = 0

        for e in entities:
            self.create_entity(e, source_name)
            entity_count += 1

        for r in relationships:
            self.create_relationship(r, source_name)
            rel_count += 1

        return entity_count, rel_count

    # =====================================
    # READ OPERATIONS (FOR GRAPH RAG)
    # =====================================

    def query_graph(self, term: str):
        """Core GraphRAG traversal query."""

        query = """
        MATCH (n:Entity)-[r]-(m:Entity)
        WHERE toLower(n.name) CONTAINS toLower($term)
        RETURN 
            n { .name, .type } AS n,
            type(r) AS rel_type,
            m { .name, .type } AS m
        LIMIT 10
        """

        with self.driver.session() as session:
            result = session.run(query, term=term)

            records = []
            for record in result:
                records.append({
                    "n": record["n"],
                    "r": {"type": record["rel_type"]},
                    "m": record["m"]
                })

            return records

    # =====================================
    # OPTIONAL UTILITY FUNCTIONS
    # =====================================

    def get_all_entities(self, limit: int = 100):
        query = """
        MATCH (e:Entity)
        RETURN e.name AS name, e.type AS type
        LIMIT $limit
        """

        with self.driver.session() as session:
            result = session.run(query, limit=limit)
            return [dict(record) for record in result]

    def get_stats(self):
        with self.driver.session() as session:
            total_entities = session.run(
                "MATCH (e:Entity) RETURN count(e) AS c"
            ).single()["c"]

            total_relationships = session.run(
                "MATCH ()-[r]->() RETURN count(r) AS c"
            ).single()["c"]

        return {
            "total_entities": total_entities,
            "total_relationships": total_relationships,
        }

    def clear_graph(self):
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")