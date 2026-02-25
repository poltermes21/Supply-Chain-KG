"""
KG Loader Module

Loads extracted nodes and relationships into Neo4j.

"""

from neo4j import GraphDatabase
from typing import Dict
import os
from settings import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


class KGLoaderNeo4j:
    """
    Load nodes and relationships into Neo4j.

    Args:
        kg_data: Dict output from KGExtractor.extract()
    """

    def __init__(self, kg_data: Dict):
        self.kg_data = kg_data
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    # 1. CONSTRAINTS

    def create_constraint(self):
        """
        Create single universal uniqueness constraint on BaseNode.id.
        Safe to run multiple times.
        """
        print("Creating universal ID constraint (if not exists)...")

        query = """
        CREATE CONSTRAINT node_id IF NOT EXISTS
        FOR (n:BaseNode)
        REQUIRE n.id IS UNIQUE
        """

        with self.driver.session() as session:
            session.run(query)

        print("   Constraint ensured.")

    # 2. NODE LOADING

    def load_nodes(self):
        """
        Load all nodes into Neo4j using MERGE on indexed id.
        """

        print("Loading nodes into Neo4j...")

        with self.driver.session() as session:

            for label, nodes in self.kg_data['nodes'].items():

                if not nodes:
                    continue

                print(f"   Loading {label} ({len(nodes)})")

                query = f"""
                UNWIND $batch AS node
                MERGE (n:BaseNode:{label} {{id: node.id}})
                SET n += node
                """

                session.run(query, batch=nodes)

        print("   Node loading complete.")

    # 3. RELATIONSHIP LOADING

    def load_relationships(self):
        """
        Load all relationships using indexed MATCH on BaseNode.id.
        """

        print("Loading relationships into Neo4j...")

        with self.driver.session() as session:

            for rel_type, rels in self.kg_data['relationships'].items():

                if not rels:
                    continue

                print(f"   Loading {rel_type} ({len(rels)})")

                query = f"""
                UNWIND $batch AS rel
                MATCH (a:BaseNode {{id: rel.from}})
                MATCH (b:BaseNode {{id: rel.to}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET r += rel
                """

                session.run(query, batch=rels)

        print("   Relationship loading complete.")

    # MAIN PIPELINE

    def load(self):
        """
        Execute the complete loading pipeline:
        1. Create constraints
        2. Load nodes
        3. Load relationships
        """
        print("=" * 60)
        print("STARTING KG LOADING PIPELINE")
        print("=" * 60)

        self.create_constraint()
        self.load_nodes()
        self.load_relationships()

        print("\n" + "=" * 60)
        print("LOADING COMPLETE")
        print("=" * 60)

    def close(self):
        """Close Neo4j driver connection."""
        self.driver.close()


if __name__ == "__main__":
    from .extractor import KGExtractor
    import pandas as pd
    from settings import DATA_DIR

    df = pd.read_csv(os.path.join(DATA_DIR, "data_transformed.csv"))
    extractor = KGExtractor(df)
    kg_data = extractor.extract()

    loader = KGLoaderNeo4j(kg_data)
    loader.load()
    loader.close()