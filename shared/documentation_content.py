"""Shared documentation content for the Streamlit platform."""

DOCUMENTATION_PAGES = [
    {
        "page_title": "1. Operational Baseline",
        "page_file": "01_1._Operational_Baseline.py",
        "summary": "Normal operating conditions: volumes, delays, traffic mix and lane resilience.",
        "sections": [
            {
                "title": "1 · KPIs baseline",
                "summary": "Shows the core operating baseline: KPI cards, temporal performance trends and the transport mode split for the network.",
            },
            {
                "title": "2 · Traffic distribution",
                "summary": "Shows how traffic is distributed across routes, route profiles and product composition",
            },
            {
                "title": "3 · Operational Risk",
                "summary": "Shows the delay severity breakdown and compares product categories by cost, delay rate and volume.",
            },
            {
                "title": "4 · OD Lane Resilience",
                "summary": "Compares origin-destination lanes to expose concentrated flows and fragile links.",
            },
        ],
    },
    {
        "page_title": "2. Risk Analysis",
        "page_file": "02_2._Risk_Analysis.py",
        "summary": "Multidimensional risk exposure by level, geography, route and critical lane.",
        "sections": [
            {
                "title": "1 · Global risk profile",
                "summary": "Summarises the network-wide risk classes and checks whether higher risk maps to worse outcomes.",
            },
            {
                "title": "2 · Risk Concentration",
                "summary": "Shows how geopolitical and weather exposure combine across routes and products.",
            },
            {
                "title": "3 · Risk by geographic node",
                "summary": "Compares outbound and inbound risk exposure for each city.",
            },
            {
                "title": "4 · Joint Exposure — risk overlap",
                "summary": "Finds routes where multiple risk conditions overlap and create compounded exposure.",
            },
            {
                "title": "5 · Critical lanes by risk and volume",
                "summary": "Ranks lanes by volume, disruption rate and combined risk, with controls to highlight the most critical lanes.",
            },
        ],
    },
    {
        "page_title": "3. Structural Vulnerability",
        "page_file": "03_3._Structural_Vulnerability.py",
        "summary": "Graph topology, bridge cities, hubs and route fragility in the CITY_FLOW layer.",
        "sections": [
            {
                "title": "1 · Topology and functional roles",
                "summary": "Maps cities by flow balance and volume to identify importers, exporters and hubs.",
            },
            {
                "title": "2 · Structural bridges — critical risk nodes",
                "summary": "Flags bridge cities with high betweenness and limited alternative connections, so their failure can break connectivity.",
            },
            {
                "title": "3 · Strategic hubs — volume vs. influence",
                "summary": "Shows which cities combine large throughput with high structural influence.",
            },
            {
                "title": "4 · Detailed Metrics",
                "summary": "Provides the underlying centrality metrics used in the structural analysis.",
            },
            {
                "title": "5 · Route vulnerability",
                "summary": "Visualises how disruption types affect routes across the network.",
            },
        ],
    },
    {
        "page_title": "4. Logistics Communities & Structural Exposure",
        "page_file": "04_4._Communities_and_Exposure.py",
        "summary": "Logistics communities, flow exposure per node and critical inter-community bridges.",
        "sections": [
            {
                "title": "1 · Flow exposure per node",
                "summary": "Compares inbound and outbound orders by city or country to show where activity concentrates.",
            },
            {
                "title": "2 · Logistics communities",
                "summary": "Detects community structure in the geography of flows and highlights cluster composition.",
            },
            {
                "title": "3 · Inter-community dependencies",
                "summary": "Shows how communities depend on each other through bridge lanes and shared traffic.",
            },
            {
                "title": "4 · Intra-community analysis",
                "summary": "Lets you inspect internal cohesion, risk and route concentration inside one logistics community.",
            },
        ],
    },
    {
        "page_title": "5. Cost & Mitigation Efficiency",
        "page_file": "05_5._Cost_Efficiency.py",
        "summary": "Economic impact of disruptions and how effective mitigation actions are in practice.",
        "sections": [
            {
                "title": "1 · Economic impact of disruptions",
                "summary": "Compares disrupted and non-disrupted cases to show the cost and time penalty of disruptions.",
            },
            {
                "title": "2 · Disruption cost profile",
                "summary": "Profiles each disruption type by cost increase, delay severity and volume of orders.",
            },
            {
                "title": "3 · Global mitigation effectiveness",
                "summary": "Summarises which mitigation actions recover service, reduce cost and shorten delays.",
            },
            {
                "title": "4 · Mitigation by disruption type",
                "summary": "Compares mitigation effectiveness across disruption types.",
            },
            {
                "title": "5 · Full context mitigation",
                "summary": "Breaks mitigation performance down by disruption, route and risk level.",
            },
            {
                "title": "6 · Expedited air usage",
                "summary": "Shows when emergency air freight is used most often and what cost premium it carries.",
            },
        ],
    },
    {
        "page_title": "6. What-If Scenarios",
        "page_file": "06_6._What_If_Simulation.py",
        "summary": "Scenario testing for blocked routes, failed cities and route optimisation.",
        "sections": [
            {
                "title": "1 · Route Shock Simulation",
                "summary": "Simulates route blockages and estimates the affected volume, reroutability and penalty.",
            },
            {
                "title": "2 · Node Failure Simulation",
                "summary": "Simulates the failure of one or more cities and measures the resulting network impact.",
            },
            {
                "title": "3 · Emergency Path Optimization",
                "summary": "Finds the best path between two cities under different optimisation goals.",
            },
        ],
    },
    {
        "page_title": "7. KG Chat",
        "page_file": "07_7._KG_Chat.py",
        "summary": "Ask a natural-language question, inspect the generated Cypher, review the grounded answer and generate charts when a visual summary helps.",
        "sections": [
            {
                "title": "KG Chat",
                "summary": "Ask a natural-language question, inspect the generated Cypher and review the grounded answer.",
            },
        ],
    },
]


def get_section_help(title: str) -> str:
    for page in DOCUMENTATION_PAGES:
        for section in page["sections"]:
            if section["title"] == title:
                return section["summary"]
    return ""
