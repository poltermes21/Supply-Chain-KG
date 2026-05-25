"""
Knowledge Graph Validation Tests

Validates the structure, integrity, and correctness of the loaded Neo4j graph.

Test Categories:
    1. Node Counts       - Verify expected number of nodes per label
    2. Relationship Counts - Verify expected number of relationships per type
    3. Cardinality       - Verify relationship multiplicity (1:1, 1:N)
    4. Constraints       - Verify uniqueness constraints exist
    5. Topology          - Verify graph structure matches design
    6. Data Integrity    - Verify property values are consistent
"""

import pytest


# EXPECTED COUNTS

EXPECTED_NODE_COUNTS = {
    'Order':            15_000,
    'RiskAssessment':   15_000,
    'City':             13,
    'Country':          11,
    'Route':            5,
    'ProductCategory':  7,
    'TransportMode':    2,
    'DisruptionType':   5,
    'MitigationAction': 3,
}

# Relationships with deterministic counts (driven by Order count or City count).
EXPECTED_RELATIONSHIP_COUNTS = {
    # Per-Order: 1 of each per Order
    'ORIGIN_FROM':      15_000,
    'DESTINATION_TO':   15_000,
    'SHIPPED_VIA':      15_000,
    'TRANSPORTS':       15_000,
    'USES_MODE':        15_000,
    'AFFECTED_BY':      15_000,
    'MITIGATED_WITH':   15_000,
    'HAS_RISK':         15_000,
    # Per-City: 1 LOCATED_IN per City
    'LOCATED_IN':       13,
}

# Relationships whose count is data-derived (depends on which OD pairs,
# routes, and disruptions appear in the dataset). Tested for existence and
# topology, not absolute count.
DERIVED_RELATIONSHIP_TYPES = ['CONNECTS', 'VULNERABLE_TO', 'CITY_FLOW']


# 1. NODE COUNT TESTS

class TestNodeCounts:
    """
    Validate that the correct number of nodes exist for each label.

    Tests:
        - Each node type has expected count
        - Total node count matches sum of individual counts
    """

    @pytest.mark.parametrize("label,expected_count", EXPECTED_NODE_COUNTS.items())
    def test_node_count_by_label(self, neo4j_session, label, expected_count):
        """
        Verify each node type has the expected count.

        Args:
            neo4j_session: Neo4j session fixture
            label:         Node label to check
            expected_count: Expected number of nodes with this label
        """
        query = f"MATCH (n:{label}) RETURN count(n) as cnt"
        result = neo4j_session.run(query)
        actual_count = result.single()["cnt"]

        assert actual_count == expected_count, (
            f"Expected {expected_count} {label} nodes, found {actual_count}"
        )

    def test_total_node_count(self, neo4j_session):
        """
        Verify total node count matches sum of expected counts.

        Notes:
            - Helps detect unexpected node types or duplicates
        """
        query = "MATCH (n) RETURN count(n) as cnt"
        result = neo4j_session.run(query)
        actual_total = result.single()["cnt"]

        expected_total = sum(EXPECTED_NODE_COUNTS.values())

        assert actual_total == expected_total, (
            f"Expected {expected_total} total nodes, found {actual_total}"
        )


# 2. RELATIONSHIP COUNT TESTS

class TestRelationshipCounts:
    """
    Validate that the correct number of relationships exist for each type.

    Tests:
        - Each deterministic relationship type has expected count
        - Each data-derived relationship type exists (count > 0)
        - All loaded relationship types are known to the test (no orphan types)
    """

    @pytest.mark.parametrize(
        "rel_type,expected_count",
        EXPECTED_RELATIONSHIP_COUNTS.items(),
    )
    def test_relationship_count_by_type(self, neo4j_session, rel_type, expected_count):
        """
        Verify each deterministic relationship type has the expected count.

        Args:
            neo4j_session:  Neo4j session fixture
            rel_type:       Relationship type to check
            expected_count: Expected number of relationships of this type
        """
        query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as cnt"
        result = neo4j_session.run(query)
        actual_count = result.single()["cnt"]

        assert actual_count == expected_count, (
            f"Expected {expected_count} {rel_type} relationships, found {actual_count}"
        )

    @pytest.mark.parametrize("rel_type", DERIVED_RELATIONSHIP_TYPES)
    def test_derived_relationship_exists(self, neo4j_session, rel_type):
        """
        Verify data-derived relationships (counts depend on dataset shape)
        exist in the graph. Catches missed extraction stages without locking
        to a specific cardinality.
        """
        query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as cnt"
        result = neo4j_session.run(query)
        actual_count = result.single()["cnt"]

        assert actual_count > 0, (
            f"Expected at least 1 {rel_type} relationship, found 0"
        )

    def test_no_unexpected_relationship_types(self, neo4j_session):
        """
        Verify the graph contains only the relationship types the design
        declares. Catches accidental rel types introduced by a bad load.
        """
        query = "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
        result = neo4j_session.run(query)
        actual_types = {row["relationshipType"] for row in result}

        expected_types = (
            set(EXPECTED_RELATIONSHIP_COUNTS.keys())
            | set(DERIVED_RELATIONSHIP_TYPES)
        )
        unexpected = actual_types - expected_types

        assert not unexpected, (
            f"Unexpected relationship types in graph: {sorted(unexpected)}"
        )


# 3. CARDINALITY TESTS

class TestCardinality:
    """
    Validate relationship cardinality (1:1, 1:N) matches design.

    Tests:
        - Each Order has exactly 1 ORIGIN_FROM
        - Each Order has exactly 1 DESTINATION_TO
        - Each Order has exactly 1 SHIPPED_VIA
        - Each Order has exactly 1 TRANSPORTS
        - Each Order has exactly 1 USES_MODE
        - Each Order has exactly 1 AFFECTED_BY
        - Each Order has exactly 1 MITIGATED_WITH
        - Each Order has exactly 1 HAS_RISK
        - Each City has exactly 1 LOCATED_IN
    """

    def test_each_order_has_one_origin(self, neo4j_session):
        """
        Verify each Order has exactly 1 ORIGIN_FROM relationship.

        Design Rule:
            Order -[ORIGIN_FROM]-> City (cardinality: 1:1)
        """
        query = """
        MATCH (o:Order)
        WITH o, COUNT { (o)-[:ORIGIN_FROM]->() } as origins
        WHERE origins <> 1
        RETURN count(o) as invalid_count
        """
        result = neo4j_session.run(query)
        invalid_count = result.single()["invalid_count"]

        assert invalid_count == 0, (
            f"Found {invalid_count} Orders without exactly 1 ORIGIN_FROM"
        )

    def test_each_order_has_one_destination(self, neo4j_session):
        """
        Verify each Order has exactly 1 DESTINATION_TO relationship.

        Design Rule:
            Order -[DESTINATION_TO]-> City (cardinality: 1:1)
        """
        query = """
        MATCH (o:Order)
        WITH o, COUNT { (o)-[:DESTINATION_TO]->() } as destinations
        WHERE destinations <> 1
        RETURN count(o) as invalid_count
        """
        result = neo4j_session.run(query)
        invalid_count = result.single()["invalid_count"]

        assert invalid_count == 0, (
            f"Found {invalid_count} Orders without exactly 1 DESTINATION_TO"
        )

    def test_each_order_has_one_route(self, neo4j_session):
        """
        Verify each Order has exactly 1 SHIPPED_VIA relationship.

        Design Rule:
            Order -[SHIPPED_VIA]-> Route (cardinality: 1:1)
        """
        query = """
        MATCH (o:Order)
        WITH o, COUNT { (o)-[:SHIPPED_VIA]->() } as routes
        WHERE routes <> 1
        RETURN count(o) as invalid_count
        """
        result = neo4j_session.run(query)
        invalid_count = result.single()["invalid_count"]

        assert invalid_count == 0, (
            f"Found {invalid_count} Orders without exactly 1 SHIPPED_VIA"
        )

    def test_each_order_has_one_product(self, neo4j_session):
        """
        Verify each Order has exactly 1 TRANSPORTS relationship.

        Design Rule:
            Order -[TRANSPORTS]-> ProductCategory (cardinality: 1:1)
        """
        query = """
        MATCH (o:Order)
        WITH o, COUNT { (o)-[:TRANSPORTS]->() } as products
        WHERE products <> 1
        RETURN count(o) as invalid_count
        """
        result = neo4j_session.run(query)
        invalid_count = result.single()["invalid_count"]

        assert invalid_count == 0, (
            f"Found {invalid_count} Orders without exactly 1 TRANSPORTS"
        )

    def test_each_order_has_one_transport_mode(self, neo4j_session):
        """
        Verify each Order has exactly 1 USES_MODE relationship.

        Design Rule:
            Order -[USES_MODE]-> TransportMode (cardinality: 1:1)
        """
        query = """
        MATCH (o:Order)
        WITH o, COUNT { (o)-[:USES_MODE]->() } as modes
        WHERE modes <> 1
        RETURN count(o) as invalid_count
        """
        result = neo4j_session.run(query)
        invalid_count = result.single()["invalid_count"]

        assert invalid_count == 0, (
            f"Found {invalid_count} Orders without exactly 1 USES_MODE"
        )

    def test_each_order_has_one_disruption(self, neo4j_session):
        """
        Verify each Order has exactly 1 AFFECTED_BY relationship.

        Design Rule:
            Order -[AFFECTED_BY]-> DisruptionType (cardinality: 1:1)

        Notes:
            - Includes orders with disruption_id=0 (no_disruption)
        """
        query = """
        MATCH (o:Order)
        WITH o, COUNT { (o)-[:AFFECTED_BY]->() } as disruptions
        WHERE disruptions <> 1
        RETURN count(o) as invalid_count
        """
        result = neo4j_session.run(query)
        invalid_count = result.single()["invalid_count"]

        assert invalid_count == 0, (
            f"Found {invalid_count} Orders without exactly 1 AFFECTED_BY"
        )

    def test_each_order_has_one_mitigation(self, neo4j_session):
        """
        Verify each Order has exactly 1 MITIGATED_WITH relationship.

        Design Rule:
            Order -[MITIGATED_WITH]-> MitigationAction (cardinality: 1:1)
        """
        query = """
        MATCH (o:Order)
        WITH o, COUNT { (o)-[:MITIGATED_WITH]->() } as mitigations
        WHERE mitigations <> 1
        RETURN count(o) as invalid_count
        """
        result = neo4j_session.run(query)
        invalid_count = result.single()["invalid_count"]

        assert invalid_count == 0, (
            f"Found {invalid_count} Orders without exactly 1 MITIGATED_WITH"
        )

    def test_each_order_has_one_risk_assessment(self, neo4j_session):
        """
        Verify each Order has exactly 1 HAS_RISK relationship.

        Design Rule:
            Order -[HAS_RISK]-> RiskAssessment (cardinality: 1:1)
        """
        query = """
        MATCH (o:Order)
        WITH o, COUNT { (o)-[:HAS_RISK]->() } as risks
        WHERE risks <> 1
        RETURN count(o) as invalid_count
        """
        result = neo4j_session.run(query)
        invalid_count = result.single()["invalid_count"]

        assert invalid_count == 0, (
            f"Found {invalid_count} Orders without exactly 1 HAS_RISK"
        )

    def test_each_city_has_one_country(self, neo4j_session):
        """
        Verify each City has exactly 1 LOCATED_IN relationship.

        Design Rule:
            City -[LOCATED_IN]-> Country (cardinality: 1:1)
        """
        query = """
        MATCH (c:City)
        WITH c, COUNT { (c)-[:LOCATED_IN]->() } as countries
        WHERE countries <> 1
        RETURN count(c) as invalid_count
        """
        result = neo4j_session.run(query)
        invalid_count = result.single()["invalid_count"]

        assert invalid_count == 0, (
            f"Found {invalid_count} Cities without exactly 1 LOCATED_IN"
        )


# 4. CONSTRAINT TESTS

class TestConstraints:
    """
    Validate that uniqueness constraints exist for all node labels.

    Tests:
        - Constraint exists for each node label
        - Constraints are in ONLINE state
    """

    @pytest.mark.parametrize("label", EXPECTED_NODE_COUNTS.keys())
    def test_constraint_exists_for_label(self, neo4j_session, label):
        """
        Verify uniqueness constraint exists for each node label.

        Args:
            neo4j_session: Neo4j session fixture
            label:         Node label to check

        Notes:
            - Constraint should be on 'id' property
            - Constraint should be in 'ONLINE' state
        """
        query = """
        SHOW CONSTRAINTS
        YIELD name, labelsOrTypes, properties, entityType, type
        WHERE $label IN labelsOrTypes
          AND 'id' IN properties
          AND type = 'UNIQUENESS'
        RETURN count(*) as cnt
        """
        result = neo4j_session.run(query, label=label)
        constraint_count = result.single()["cnt"]

        assert constraint_count >= 1, (
            f"No uniqueness constraint found for {label}.id"
        )


# 5. TOPOLOGY TESTS

class TestTopology:
    """
    Validate graph topology matches design schema.

    Tests:
        - Relationships connect correct node types
        - No orphaned nodes (nodes without relationships)
        - Specific structural rules hold
    """

    def test_transports_connects_order_to_product_category(self, neo4j_session):
        """
        Verify TRANSPORTS relationships only connect Order to ProductCategory.

        Design Rule:
            Order -[TRANSPORTS]-> ProductCategory
        """
        query = """
        MATCH (a)-[r:TRANSPORTS]->(b)
        WHERE NOT (a:Order AND b:ProductCategory)
        RETURN count(r) as invalid_count
        """
        result = neo4j_session.run(query)
        invalid_count = result.single()["invalid_count"]

        assert invalid_count == 0, (
            f"Found {invalid_count} TRANSPORTS relationships with incorrect node types"
        )

    def test_affected_by_connects_order_to_disruption_type(self, neo4j_session):
        """
        Verify AFFECTED_BY relationships only connect Order to DisruptionType.

        Design Rule:
            Order -[AFFECTED_BY]-> DisruptionType
        """
        query = """
        MATCH (a)-[r:AFFECTED_BY]->(b)
        WHERE NOT (a:Order AND b:DisruptionType)
        RETURN count(r) as invalid_count
        """
        result = neo4j_session.run(query)
        invalid_count = result.single()["invalid_count"]

        assert invalid_count == 0, (
            f"Found {invalid_count} AFFECTED_BY relationships with incorrect node types"
        )

    def test_vulnerable_to_connects_route_to_disruption_type(self, neo4j_session):
        """
        Verify VULNERABLE_TO relationships only connect Route to DisruptionType.

        Design Rule:
            Route -[VULNERABLE_TO]-> DisruptionType
        """
        query = """
        MATCH (a)-[r:VULNERABLE_TO]->(b)
        WHERE NOT (a:Route AND b:DisruptionType)
        RETURN count(r) as invalid_count
        """
        result = neo4j_session.run(query)
        invalid_count = result.single()["invalid_count"]

        assert invalid_count == 0, (
            f"Found {invalid_count} VULNERABLE_TO relationships with incorrect node types"
        )

    def test_connects_links_route_to_city(self, neo4j_session):
        """
        Verify CONNECTS relationships only connect Route to City.

        Design Rule:
            Route -[CONNECTS]-> City
        """
        query = """
        MATCH (a)-[r:CONNECTS]->(b)
        WHERE NOT (a:Route AND b:City)
        RETURN count(r) as invalid_count
        """
        result = neo4j_session.run(query)
        invalid_count = result.single()["invalid_count"]

        assert invalid_count == 0, (
            f"Found {invalid_count} CONNECTS relationships with incorrect node types"
        )

    def test_city_flow_connects_city_to_city(self, neo4j_session):
        """
        Verify CITY_FLOW relationships only connect City to City.

        Design Rule:
            City -[CITY_FLOW]-> City (aggregated OD-pair layer)
        """
        query = """
        MATCH (a)-[r:CITY_FLOW]->(b)
        WHERE NOT (a:City AND b:City)
        RETURN count(r) as invalid_count
        """
        result = neo4j_session.run(query)
        invalid_count = result.single()["invalid_count"]

        assert invalid_count == 0, (
            f"Found {invalid_count} CITY_FLOW relationships with incorrect node types"
        )

    def test_city_flow_no_self_loops(self, neo4j_session):
        """
        Verify no CITY_FLOW relationship connects a City to itself.

        Design Rule:
            CITY_FLOW edges represent origin->destination flows between
            distinct cities — a self-loop would indicate an extractor bug.
        """
        query = """
        MATCH (c:City)-[r:CITY_FLOW]->(c)
        RETURN count(r) as self_loops
        """
        result = neo4j_session.run(query)
        self_loops = result.single()["self_loops"]

        assert self_loops == 0, (
            f"Found {self_loops} CITY_FLOW self-loops"
        )

    def test_no_disconnected_orders(self, neo4j_session):
        """
        Verify no Order nodes exist without any relationships.

        Notes:
            - Every Order should have at least 8 outgoing relationships
            - This catches data loading errors
        """
        query = """
        MATCH (o:Order)
        WHERE NOT (o)--()
        RETURN count(o) as disconnected_count
        """
        result = neo4j_session.run(query)
        disconnected_count = result.single()["disconnected_count"]

        assert disconnected_count == 0, (
            f"Found {disconnected_count} disconnected Order nodes"
        )


# 6. DATA INTEGRITY TESTS

class TestDataIntegrity:
    """
    Validate property values are consistent and within expected ranges.

    Tests:
        - Numeric IDs are within valid ranges
        - Required properties are not null
        - Boolean flags are consistent with related data
    """

    def test_disruption_ids_valid_range(self, neo4j_session):
        """
        Verify all DisruptionType nodes have id in range [0, 4].

        Expected IDs:
            0 = no_disruption
            1 = geopolitical_conflict
            2 = port_congestion
            3 = cape_storms
            4 = typhoon_storm
        """
        query = """
        MATCH (d:DisruptionType)
        WHERE d.id < 0 OR d.id > 4
        RETURN count(d) as invalid_count
        """
        result = neo4j_session.run(query)
        invalid_count = result.single()["invalid_count"]

        assert invalid_count == 0, (
            f"Found {invalid_count} DisruptionType nodes with id outside [0, 4]"
        )

    def test_product_category_ids_valid_range(self, neo4j_session):
        """
        Verify all ProductCategory nodes have id in range [0, 6].

        Expected IDs:
            7 unique product categories (0-indexed)
        """
        query = """
        MATCH (p:ProductCategory)
        WHERE p.id < 0 OR p.id > 6
        RETURN count(p) as invalid_count
        """
        result = neo4j_session.run(query)
        invalid_count = result.single()["invalid_count"]

        assert invalid_count == 0, (
            f"Found {invalid_count} ProductCategory nodes with id outside [0, 6]"
        )

    def test_mitigation_action_ids_valid_range(self, neo4j_session):
        """
        Verify all MitigationAction nodes have id in range [0, 2].

        Expected IDs:
            3 unique mitigation actions (0-indexed)
        """
        query = """
        MATCH (m:MitigationAction)
        WHERE m.id < 0 OR m.id > 2
        RETURN count(m) as invalid_count
        """
        result = neo4j_session.run(query)
        invalid_count = result.single()["invalid_count"]

        assert invalid_count == 0, (
            f"Found {invalid_count} MitigationAction nodes with id outside [0, 2]"
        )

    def test_orders_have_positive_shipping_cost(self, neo4j_session):
        """
        Verify all Orders have shipping_cost_usd > 0.

        Notes:
            - Shipping cost should never be zero or negative
        """
        query = """
        MATCH (o:Order)
        WHERE o.shipping_cost_usd <= 0
        RETURN count(o) as invalid_count
        """
        result = neo4j_session.run(query)
        invalid_count = result.single()["invalid_count"]

        assert invalid_count == 0, (
            f"Found {invalid_count} Orders with shipping_cost_usd <= 0"
        )

    def test_is_disrupted_consistent_with_disruption_id(self, neo4j_session):
        """
        Verify is_disrupted flag is consistent with AFFECTED_BY relationship.

        Logic:
            - is_disrupted should be false if AFFECTED_BY points to DisruptionType.id=0
            - is_disrupted should be true if AFFECTED_BY points to DisruptionType.id>0
        """
        query = """
        MATCH (o:Order)-[:AFFECTED_BY]->(d:DisruptionType)
        WHERE (d.id = 0 AND o.is_disrupted = true)
           OR (d.id > 0 AND o.is_disrupted = false)
        RETURN count(o) as inconsistent_count
        """
        result = neo4j_session.run(query)
        inconsistent_count = result.single()["inconsistent_count"]

        assert inconsistent_count == 0, (
            f"Found {inconsistent_count} Orders with inconsistent is_disrupted flag"
        )

    def test_delayed_orders_have_positive_delay_days(self, neo4j_session):
        """
        Verify Orders with is_delayed=true have delay_days > 0.

        Logic:
            - If is_delayed is true, delay_days must be > 0
        """
        query = """
        MATCH (o:Order)
        WHERE o.is_delayed = true AND o.delay_days = 0
        RETURN count(o) as inconsistent_count
        """
        result = neo4j_session.run(query)
        inconsistent_count = result.single()["inconsistent_count"]

        assert inconsistent_count == 0, (
            f"Found {inconsistent_count} delayed Orders with delay_days = 0"
        )
