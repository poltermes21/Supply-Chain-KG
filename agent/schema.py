"""
agent/schema.py
Knowledge Graph schema
"""

KG_SCHEMA_PROMPT = """
## Knowledge Graph Schema — Supply Chain KG

### Environment
- Neo4j with APOC 5.12.0 and GDS 2.6.9
- Use `elementId()` instead of deprecated `id()` for node identity
- All queries must be READ-ONLY (no MERGE, CREATE, DELETE, SET, REMOVE)
- Include LIMIT only if it is requested (default 10)

---

### Node Labels & Properties

**Order** (15000 nodes) — unique constraint on `id`
  - id                        String   — unique shipment identifier e.g "ORD-04F86DAA"
  - order_date                Date     — e.g. date("2023-06-15")
  - order_weight_kg           Long
  - shipping_cost_usd         Double
  - cost_per_kg               Double   — (shipping_cost_per_kg / order_weight_kg)
  - cost_vs_baseline_pct      Double   — % deviation from cost baseline ((cost - avg_normal_cost) / avg_normal_cost * 100)

  - base_lead_time_days       Long     — base lead time
  - scheduled_lead_time_days  Long     — scheduled lead time (includes buffer)
  - actual_lead_time_days     Long     — actual delivery lead time

  - delay_days                Long     — (actual_lead_time_days - scheduled) | 0
  - delay_ratio               Double   — delay as % of scheduled lead time (delay_days / scheduled_lead_time_days * 100)
  - lead_time_deviation_pct   Double   — (actual_lead_time_days - scheduled_lead_time_days) / scheduled_lead_time_days * 100

  - delay_severity            String   — delay classification based on delay_days:
                                         "none" (0 days)
                                         "minor" (≤ 2 days)
                                         "moderate" (≤ 4 days)
                                         "severe" (≤ 7 days)
                                         "critical" (> 7 days)
                                         "unknown" (missing/inconsistent data)

  - delivery_status           String   — "On Time" | "Late"

  - is_delayed                Boolean
  - is_disrupted              Boolean

  - mitigation_effectiveness  String   — effectiveness of mitigation actions:
                                         "not_applicable" → no disruption (is_disrupted = false)
                                         "fully_effective" → disruption but no delay
                                         "partially_effective" → delayed but severity = minor
                                         "not_effective" → delayed and severity ≥ moderate
                                         "unknown" → insufficient data

  - mitigation_effective      Boolean  — true if mitigation_effectiveness ∈ {"fully_effective","partially_effective"}
                                         false otherwise

**RiskAssessment** (15000 nodes)
  - id                        String    — unique shipment identifier e.g "ORD-04F86DAA"
  
  - risk_level                String   — risk category based on combined_risk_score:
                                         "low" (< 0.3)
                                         "medium" (< 0.6)
                                         "high" (< 0.8)
                                         "critical" (≥ 0.8)
                                         "unknown" (missing/inconsistent data)
                                         
  - combined_risk_score       Double   — aggregated risk score ∈ [0,1], (0.6 * geopolitical_risk_index + 0.4 * weather_severity_index)
  - weather_severity_index    Double   — weather-related risk intensity ∈ [0,1], 0 = no impact, 1 = extreme conditions
  - geopolitical_risk_index   Double   — geopolitical instability risk ∈ [0,1], 0 = stable, 1 = highly unstable
  - inflation_rate_pct        Double   — inflation rate (%) (not normalized)

**City** (13 nodes)
  - id                        String   — name of the city e.g. "Shanghai"

  - role                      String   — node role based on connectivity:
                                         "H" (hub: inbound > 0 AND outbound > 0)
                                         "O" (origin: outbound > 0 AND inbound = 0)
                                         "D" (destination: inbound > 0 AND outbound = 0)
                                         "isolated" (no inbound nor outbound connections)

  - outbound_degree           Long     — number of outgoing shipments from the city
  - inbound_degree            Long     — number of incoming shipments to the city
  - community_id              Long     — GDS Louvain community detection result (graph cluster id)

**Country** (11 nodes)
  - id                        String   — ISO country code (e.g. "US", "CN", "DE")
  - country_name              String   — full country name (e.g. "United States")
  - region                    String   — macro region grouping:"Asia" | "Europe" | "Americas"

**Route** (5 nodes)
  - id                        String   — "Suez" | "Pacific" | "Intra-Asia" | "CoGH" | "Atlantic"

**ProductCategory** (7 nodes)
  - id                        Long   — unique category identifier (e.g. 0, 1, 2...)
  - name                      String — "Auto Parts" |" Consumer Electronics" | "Textiles" | "Semiconductors" | "Raw Materials" | "Pharmaceuticals" | "Perishable Foods"

**TransportMode** (2 nodes)
  - id                        String   — "Sea" | "Air"

**DisruptionType** (5 nodes)
  - id                        Long   — unique category identifier (0, 1, 2, 3, 4)
  - name                      String — short label, "no_disruption" | "geopolitical_conflict" | "port_congestion" | "cape_storms" | "typhoon_storm"
  - full_name                 String — human-readable description, "No Disruption" | "Geopolitical Conflict (Route Diversion)" | "Port Congestion" | "Severe Weather (Cape Storms)" | "Severe Weather (Typhoon/Storm)"

**MitigationAction** (3 nodes)
  - id                        Long     — unique category identifier (0, 1, 2)
  - name                      String   — "Expedited Air Freight" | "Re-routing" | "Standard Shipping"
  - avg_cost_impact           Double   — mean shipping_cost_usd grouped by mitigation action
  - avg_delay_reduction       Double   — mean delay_days grouped by mitigation action

---

### Relationship Types & Properties

// Order → RiskAssessment
(:Order)-[:HAS_RISK]->(:RiskAssessment)
  - from   String   — Order.id
  - to     String   — DisruptionType.id

// Order → City (origin)
(:Order)-[:ORIGIN_FROM]->(:City)
  - from   String   — Order.id
  - to     String   — City.id

// Order → City (destination)
(:Order)-[:DESTINATION_TO]->(:City)
  - from   String   — Order.id
  - to     String   — City.id

// Order → Route
(:Order)-[:SHIPPED_VIA]->(:Route)
  - from   String   — Order.id
  - to     String   — Route.id

// Order → ProductCategory (weight on the relationship)
(:Order)-[:TRANSPORTS]->(:ProductCategory)
  - weight_kg  Long     — shipment weight in kg
  - from       String   — Order.id
  - to         Long     — ProductCategory.id

// Order → TransportMode
(:Order)-[:USES_MODE]->(:TransportMode)
  - from   String   — Order.id
  - to     String   — TransportMode.id

// Order → DisruptionType
(:Order)-[:AFFECTED_BY]->(:DisruptionType)
  - from   String   — Order.id
  - to     Long     — DisruptionType.id

// Order → MitigationAction
(:Order)-[:MITIGATED_WITH]->(:MitigationAction)
  - from   String   — Order.id
  - to     Long     — MitigationAction.id

// Route → City (geographic coverage)
(:Route)-[:CONNECTS]->(:City)
  - direction  String   — role of the city, "origin" | "destination
  - from       String   — Route.id
  - to         String   — City.id

// Route → DisruptionType (structural vulnerability)
(:Route)-[:VULNERABLE_TO]->(:DisruptionType)
  - severity   String   — derived from median delay_severity of disruptions per (Route, DisruptionType)
  - frequency  Long     — number of disruption events per (Route, DisruptionType)
  - from       String   — Route.id
  - to         Long     — DisruptionType.id

// City → Country
(:City)-[:LOCATED_IN]->(:Country)
  - from   String   — City.id
  - to     String   — Country.id

// City → City  (aggregated flow layer used for topology/vulnerability analysis)
(:City)-[:CITY_FLOW]->(:City)
  - shipments               Long         — number of orders between origin and destination cities
  - avg_lead_time_days      Double       — mean Actual_Lead_Time_Days per OD pair
  - avg_delay_days          Double       — mean Delay_Days per OD pair
  - avg_cost_usd            Double       — mean Shipping_Cost_USD per OD pair
  - total_weight_kg         Long         — sum of Order_Weight_Kg per OD pair
  - delay_rate_pct          Double       — percentage of delayed shipments (P(is_delayed = true) * 100))
  - disrupted_rate_pct      Double       — percentage of disrupted shipments (P(is_disrupted = true) * 100))
  - route_count             Long         — number of unique Route values on this OD pair
  - routes_used             StringArray  — list of route ids used on this OD pair (['CoGH', 'Suez'])
  - route_concentration     Double       — HHI index (0–1), 1 = single route
  - avg_combined_risk_score Double       — mean combined_risk_score per OD pair
  - air_share_pct           Double       — percentage of shipments using Air mode
  - dominant_mode           String       — most frequent Transportation_Mode in OD pair, "Sea" | "Air"
  - route_share             String       — JSON map of route → share % ("{"Suez": 0.6828, "CoGH": 0.3172}")
  - from                    String       — City.id
  - to                      String       — City.id

---

### Example Queries

// Total orders per route
MATCH (o:Order)-[:SHIPPED_VIA]->(r:Route)
RETURN r.id AS route, count(o) AS total_orders
ORDER BY total_orders DESC
LIMIT 10

// Average delay by transport mode
MATCH (o:Order)-[:USES_MODE]->(m:TransportMode)
WHERE o.is_delayed = true
RETURN m.id AS mode,
       avg(o.delay_days) AS avg_delay_days,
       count(o) AS delayed_orders
ORDER BY avg_delay_days DESC
LIMIT 10

// Top origin cities by shipment volume
MATCH (o:Order)-[:ORIGIN_FROM]->(c:City)
RETURN c.id AS city, count(o) AS shipments
ORDER BY shipments DESC
LIMIT 10

// High-risk orders with disruption type and mitigation
MATCH (o:Order)-[:HAS_RISK]->(r:RiskAssessment)
WHERE r.risk_level = 'critical'
OPTIONAL MATCH (o)-[:AFFECTED_BY]->(d:DisruptionType)
OPTIONAL MATCH (o)-[:MITIGATED_WITH]->(m:MitigationAction)
RETURN o.id AS order_id,
       r.combined_risk_score AS risk_score,
       d.full_name AS disruption,
       m.name AS mitigation
ORDER BY risk_score DESC
LIMIT 20

// City-to-city flows with highest delay rate
MATCH (origin:City)-[f:CITY_FLOW]->(dest:City)
RETURN origin.id AS from_city, dest.id AS to_city,
       f.shipments AS shipments,
       f.delay_rate_pct AS delay_rate,
       f.dominant_mode AS mode
ORDER BY f.delay_rate_pct DESC
LIMIT 10

// Routes most vulnerable to disruptions
MATCH (r:Route)-[v:VULNERABLE_TO]->(d:DisruptionType)
WHERE v.severity = 'high'
RETURN r.id AS route,
       d.full_name AS disruption_type,
       v.frequency AS incidents
ORDER BY v.frequency DESC
LIMIT 10

// Mitigation effectiveness summary
MATCH (o:Order)-[:MITIGATED_WITH]->(m:MitigationAction)
RETURN m.name AS mitigation,
       count(o) AS total_orders,
       sum(CASE WHEN o.mitigation_effective THEN 1 ELSE 0 END) AS effective_count,
       round(100.0 * sum(CASE WHEN o.mitigation_effective THEN 1 ELSE 0 END) / count(o), 2) AS effectiveness_pct,
       avg(m.avg_delay_reduction) AS avg_delay_reduction_days
ORDER BY effectiveness_pct DESC
LIMIT 10

// Product categories ranked by shipping cost
MATCH (o:Order)-[t:TRANSPORTS]->(p:ProductCategory)
RETURN p.name AS product,
       count(o) AS orders,
       avg(o.shipping_cost_usd) AS avg_cost_usd,
       avg(o.cost_per_kg) AS avg_cost_per_kg,
       sum(t.weight_kg) AS total_weight_kg
ORDER BY avg_cost_usd DESC
LIMIT 10

// Delay severity distribution
MATCH (o:Order)
RETURN o.delay_severity AS severity, count(o) AS orders,
       round(100.0 * count(o) / 1071, 2) AS pct_total
ORDER BY orders DESC
LIMIT 10

// Orders with ineffective mitigation and high risk
MATCH (o:Order)-[:HAS_RISK]->(r:RiskAssessment)
WHERE o.mitigation_effective = false
  AND r.risk_level IN ['high', 'critical']
MATCH (o)-[:AFFECTED_BY]->(d:DisruptionType)
MATCH (o)-[:MITIGATED_WITH]->(m:MitigationAction)
RETURN o.id AS order_id, d.full_name AS disruption,
       m.name AS failed_mitigation, r.combined_risk_score AS risk_score
ORDER BY risk_score DESC
LIMIT 20
"""