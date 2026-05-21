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

    def create_constraints(self):
        """
        Create uniqueness constraints for each node label.
        Safe to run multiple times.
        """
        print("Creating uniqueness constraints (if not exists)...")

        with self.driver.session() as session:
            # Get all node labels from kg_data
            for label in self.kg_data['nodes'].keys():
                constraint_name = f"{label.lower()}_id"
                
                query = f"""
                CREATE CONSTRAINT {constraint_name} IF NOT EXISTS
                FOR (n:{label})
                REQUIRE n.id IS UNIQUE
                """
                
                session.run(query)
                print(f"   Constraint for {label} ensured.")

        print("   All constraints ensured.")

    # 2. NODE LOADING

    def load_nodes(self):
        """
        Load all nodes into Neo4j using MERGE on indexed id.
        Each node gets its specific label(s).
        """

        print("Loading nodes into Neo4j...")

        with self.driver.session() as session:

            for label, nodes in self.kg_data['nodes'].items():

                if not nodes:
                    continue

                print(f"   Loading {label} ({len(nodes)})")

                # Use only the specific label, not BaseNode
                query = f"""
                UNWIND $batch AS node
                MERGE (n:{label} {{id: node.id}})
                SET n += node
                """

                session.run(query, batch=nodes)

        print("   Node loading complete.")

    # 3. RELATIONSHIP LOADING

    def load_relationships(self):
        """
        Load all relationships using indexed MATCH on node id.
        Matches any node type (no label restriction needed).
        """

        print("Loading relationships into Neo4j...")

        # Define the labels for source and target of each relationship type
        relationship_schemas = {
            'ORIGIN_FROM':    ('Order', 'City'),
            'DESTINATION_TO': ('Order', 'City'),
            'SHIPPED_VIA':    ('Order', 'Route'),
            'TRANSPORTS':     ('Order', 'ProductCategory'),
            'USES_MODE':      ('Order', 'TransportMode'),
            'AFFECTED_BY':    ('Order', 'DisruptionType'),
            'MITIGATED_WITH': ('Order', 'MitigationAction'),
            'HAS_RISK':       ('Order', 'RiskAssessment'),
            'LOCATED_IN':     ('City', 'Country'),
            'CONNECTS':       ('Route', 'City'),
            'VULNERABLE_TO':  ('Route', 'DisruptionType'),
            'CITY_FLOW':      ('City',  'City'),
        }

        with self.driver.session() as session:

            for rel_type, rels in self.kg_data['relationships'].items():

                if not rels:
                    continue

                print(f"   Loading {rel_type} ({len(rels)})")

                # Get the correct labels for this relationship type
                from_label, to_label = relationship_schemas[rel_type]

                query = f"""
                UNWIND $batch AS rel
                MATCH (a:{from_label} {{id: rel.from}})
                MATCH (b:{to_label} {{id: rel.to}})
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

        self.create_constraints()
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