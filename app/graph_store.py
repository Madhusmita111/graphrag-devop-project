"""Neo4j graph database operations for storing and querying the knowledge graph."""

from neo4j import GraphDatabase
from app.models import Entity, Relationship


class GraphStore:
    """Manages all Neo4j interactions for the knowledge graph."""

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        if self.driver:
            self.driver.close()

    def verify_connection(self) -> bool:
        """Check if Neo4j is reachable."""
        try:
            self.driver.verify_connectivity()
            return True
        except Exception:
            return False

    # ── Write Operations ───────────────────────────────────────────

    def create_entity(self, entity: Entity, source_name: str) -> None:
        """Create or merge an entity node in Neo4j."""
        query = """
        MERGE (e:Entity {name: $name})
        SET e.entity_type = $entity_type,
            e.description = $description,
            e.source = $source_name,
            e.updated_at = timestamp()
        """
        with self.driver.session() as session:
            session.run(
                query,
                name=entity.name,
                entity_type=entity.entity_type,
                description=entity.description,
                source_name=source_name,
            )

    def create_relationship(self, rel: Relationship, source_name: str) -> None:
        """Create a relationship between two existing entity nodes."""
        # Cypher doesn't allow parameterised relationship types,
        # so we sanitise the type string and interpolate it safely.
        safe_type = "".join(c if c.isalnum() or c == "_" else "_" for c in rel.relation_type.upper())
        query = f"""
        MATCH (a:Entity {{name: $source}})
        MATCH (b:Entity {{name: $target}})
        MERGE (a)-[r:{safe_type}]->(b)
        SET r.description = $description,
            r.source = $source_name,
            r.updated_at = timestamp()
        """
        with self.driver.session() as session:
            session.run(
                query,
                source=rel.source,
                target=rel.target,
                description=rel.description,
                source_name=source_name,
            )

    def store_extraction(self, entities: list[Entity], relationships: list[Relationship], source_name: str) -> tuple[int, int]:
        """Store a full extraction result (entities + relationships) and return counts."""
        entity_count = 0
        rel_count = 0

        for entity in entities:
            self.create_entity(entity, source_name)
            entity_count += 1

        for rel in relationships:
            self.create_relationship(rel, source_name)
            rel_count += 1

        return entity_count, rel_count

    # ── Read Operations ────────────────────────────────────────────

    def search_entities(self, term: str, limit: int = 20) -> list[dict]:
        """Search entities whose name contains the given term (case-insensitive)."""
        query = """
        MATCH (e:Entity)
        WHERE toLower(e.name) CONTAINS toLower($term)
        RETURN e.name AS name, e.entity_type AS type, e.description AS description
        LIMIT $limit
        """
        with self.driver.session() as session:
            result = session.run(query, term=term, limit=limit)
            return [dict(record) for record in result]

    def get_entity_context(self, entity_name: str, depth: int = 2) -> dict:
        """Get an entity and its neighbourhood up to `depth` hops.
        
        Returns a subgraph dict with nodes and edges.
        """
        query = """
        MATCH path = (start:Entity {name: $name})-[*1..""" + str(depth) + """]->(connected)
        WITH start, collect(DISTINCT connected) AS neighbours, collect(DISTINCT relationships(path)) AS all_rels
        RETURN start, neighbours, all_rels
        """
        nodes = []
        edges = []

        with self.driver.session() as session:
            # Get the starting entity
            start_result = session.run(
                "MATCH (e:Entity {name: $name}) RETURN e",
                name=entity_name,
            )
            start_record = start_result.single()
            if not start_record:
                return {"nodes": [], "edges": []}

            start_node = dict(start_record["e"])
            nodes.append(start_node)

            # Get connected nodes and relationships
            path_result = session.run(
                """
                MATCH (start:Entity {name: $name})-[r]->(connected:Entity)
                RETURN connected.name AS name, connected.entity_type AS type,
                       connected.description AS description,
                       type(r) AS rel_type, r.description AS rel_desc
                """,
                name=entity_name,
            )
            for record in path_result:
                nodes.append({
                    "name": record["name"],
                    "entity_type": record["type"],
                    "description": record["description"],
                })
                edges.append({
                    "source": entity_name,
                    "target": record["name"],
                    "relation_type": record["rel_type"],
                    "description": record["rel_desc"],
                })

            # Also get incoming relationships
            incoming_result = session.run(
                """
                MATCH (connected:Entity)-[r]->(target:Entity {name: $name})
                RETURN connected.name AS name, connected.entity_type AS type,
                       connected.description AS description,
                       type(r) AS rel_type, r.description AS rel_desc
                """,
                name=entity_name,
            )
            for record in incoming_result:
                nodes.append({
                    "name": record["name"],
                    "entity_type": record["type"],
                    "description": record["description"],
                })
                edges.append({
                    "source": record["name"],
                    "target": entity_name,
                    "relation_type": record["rel_type"],
                    "description": record["rel_desc"],
                })

        # Deduplicate nodes by name
        seen = set()
        unique_nodes = []
        for node in nodes:
            if node["name"] not in seen:
                seen.add(node["name"])
                unique_nodes.append(node)

        return {"nodes": unique_nodes, "edges": edges}

    def get_relevant_context(self, terms: list[str], limit: int = 10) -> dict:
        """Given a list of query terms, find matching entities and their context.
        
        This is the core retrieval function used during question answering.
        """
        all_nodes = []
        all_edges = []

        for term in terms:
            matches = self.search_entities(term, limit=3)
            for match in matches:
                context = self.get_entity_context(match["name"])
                all_nodes.extend(context["nodes"])
                all_edges.extend(context["edges"])

        # Deduplicate
        seen_nodes = set()
        unique_nodes = []
        for node in all_nodes[:limit]:
            if node["name"] not in seen_nodes:
                seen_nodes.add(node["name"])
                unique_nodes.append(node)

        seen_edges = set()
        unique_edges = []
        for edge in all_edges:
            key = (edge["source"], edge["target"], edge["relation_type"])
            if key not in seen_edges:
                seen_edges.add(key)
                unique_edges.append(edge)

        return {"nodes": unique_nodes, "edges": unique_edges}

    def get_all_entities(self, limit: int = 100) -> list[dict]:
        """Return all entities in the graph."""
        query = """
        MATCH (e:Entity)
        RETURN e.name AS name, e.entity_type AS type, e.description AS description
        LIMIT $limit
        """
        with self.driver.session() as session:
            result = session.run(query, limit=limit)
            return [dict(record) for record in result]

    def get_stats(self) -> dict:
        """Get knowledge graph statistics."""
        with self.driver.session() as session:
            # Total entities
            entity_result = session.run("MATCH (e:Entity) RETURN count(e) AS count")
            total_entities = entity_result.single()["count"]

            # Total relationships
            rel_result = session.run("MATCH ()-[r]->() RETURN count(r) AS count")
            total_relationships = rel_result.single()["count"]

            # Entity types breakdown
            type_result = session.run(
                "MATCH (e:Entity) RETURN e.entity_type AS type, count(*) AS count ORDER BY count DESC"
            )
            entity_types = {record["type"]: record["count"] for record in type_result}

            # Relationship types breakdown
            rel_type_result = session.run(
                "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count ORDER BY count DESC"
            )
            relationship_types = {record["type"]: record["count"] for record in rel_type_result}

        return {
            "total_entities": total_entities,
            "total_relationships": total_relationships,
            "entity_types": entity_types,
            "relationship_types": relationship_types,
        }

    def clear_graph(self) -> None:
        """Delete all nodes and relationships. Use with caution."""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
