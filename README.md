# Supply Chain Knowledge Graph

A Knowledge Graph-based architecture for supply chain resilience analysis and semantic risk modeling. The system ingests synthetic global shipment data, models it as a property graph in Neo4j, runs six blocks of graph analytics (including GDS algorithms), and exposes the results through an interactive Streamlit dashboard with a LangGraph ReAct agent capable of answering natural-language questions over the graph.

---

## Architecture

```
┌─────────────────────┐     ┌──────────────────────────┐     ┌───────────────────────┐     ┌──────────────────────────┐
│  synthetic_data_    │────▶│  data_pipeline/          │────▶│  kg_builder/          │────▶│  platform/               │
│  generation/        │     │  Load → Clean → Transform │     │  Extract → Load Neo4j │     │  Streamlit + ReAct Agent │
│  (CSV generation)   │     │  (pandas, derived fields) │     │  (nodes + rels)       │     │  (6 analysis blocks)     │
└─────────────────────┘     └──────────────────────────┘     └───────────────────────┘     └──────────────────────────┘
                                                                        │
                                                              ┌─────────▼────────────┐
                                                              │  analysis/           │
                                                              │  scheduler + queries │
                                                              │  → Parquet cache     │
                                                              └──────────────────────┘
```

---

## Knowledge Graph Schema

### Node types

| Label | Key properties |
|---|---|
| `Order` | `id`, `order_date`, `actual_lead_time_days`, `delay_days`, `shipping_cost_usd`, `is_delayed`, `is_disrupted`, `delay_severity`, `combined_risk_score`, `mitigation_effectiveness` |
| `City` | `id`, `role` (O/D/H), `outbound_degree`, `inbound_degree` |
| `Country` | `id` (ISO code), `name`, `region` |
| `Route` | `id` (route type, e.g. Pacific) |
| `ProductCategory` | `id`, `name` |
| `TransportMode` | `id` (Air / Sea / Rail / Truck) |
| `DisruptionType` | `id`, `name`, `full_name` |
| `MitigationAction` | `id`, `name`, `avg_cost_vs_baseline_pct`, `avg_delay_days` |
| `RiskAssessment` | `id`, `geopolitical_risk_index`, `weather_severity_index`, `inflation_rate_pct`, `combined_risk_score`, `risk_level` |

### Relationship types

| Relationship | From → To | Key properties |
|---|---|---|
| `ORIGIN_FROM` | Order → City | — |
| `DESTINATION_TO` | Order → City | — |
| `SHIPPED_VIA` | Order → Route | — |
| `USES_MODE` | Order → TransportMode | — |
| `TRANSPORTS` | Order → ProductCategory | `weight_kg` |
| `HAS_RISK` | Order → RiskAssessment | — |
| `AFFECTED_BY` | Order → DisruptionType | — |
| `MITIGATED_WITH` | Order → MitigationAction | — |
| `LOCATED_IN` | City → Country | — |
| `CONNECTS` | Route → City | `role` (origin / destination / both) |
| `VULNERABLE_TO` | Route → DisruptionType | `frequency`, `severity` |
| `CITY_FLOW` | City → City | `orders`, `avg_cost_usd`, `delay_rate_pct`, `disruption_rate_pct`, `route_concentration`, `avg_combined_risk_score` |

---

## Project Structure

```
Supply-Chain-KG/
├── synthetic_data_generation/   # Configurable synthetic CSV generator
│   ├── config.py                # OD pairs, weights, disruption profiles
│   └── generate.py              # Generation logic
│
├── data_pipeline/               # ETL pipeline (Load → Clean → Transform)
│   ├── loader.py
│   ├── cleaner.py
│   ├── transformer.py           # Derives risk scores, severity, KG-ready IDs
│   └── pipeline.py              # Orchestrator entry point
│
├── kg_builder/                  # Knowledge Graph construction (Extract → Load)
│   ├── extractor.py             # Extracts nodes and relationships from CSV
│   ├── loader_neo4j.py          # Batched MERGE writes to Neo4j
│   └── graph_builder.py         # Orchestrator entry point
│
├── analysis/                    # Cypher query packs + caching scheduler
│   ├── scheduler.py             # Runs all blocks and writes Parquet cache
│   └── queries/
│       ├── block1_operational.py
│       ├── block2_risk.py
│       ├── block3_vulnerability.py
│       ├── block4_communities.py
│       ├── block5_costs.py
│       └── block6_what_if.py
│
├── agent/                       # LangGraph ReAct conversational agent
│   ├── graph.py                 # Main agent entry point (run())
│   ├── tools.py                 # query_graph tool with Cypher validation
│   ├── prompts.py               # System prompts (ReAct, chitchat, classifier)
│   ├── llm.py                   # Gemini Flash / Pro model factories
│   ├── memory.py                # Per-session conversation memory
│   ├── state.py                 # AgentInput / AgentOutput schemas
│   ├── schema.py                # KG schema description for the agent prompt
│   └── charts.py                # Auto-chart generation from tool results
│
├── platform/                    # Streamlit multi-page application
│   ├── Home.py                  # Landing page with global KPIs
│   └── pages/
│       ├── 01_1._Operational_Baseline.py
│       ├── 02_2._Risk_Analysis.py
│       ├── 03_3._Structural_Vulnerability.py
│       ├── 04_4._Communities_and_Exposure.py
│       ├── 05_5._Cost_and_Mitigation_Efficiency.py
│       ├── 06_6._What_If_Simulation.py
│       ├── 07_7._KG_Chat.py
│       └── 08_8._Documentation.py
│
├── shared/                      # Shared utilities
│   ├── connection.py            # Neo4j driver singleton
│   ├── analysis_store.py        # Parquet cache reader
│   ├── colors.py                # Consistent color palette
│   ├── pyvis_helpers.py         # Interactive graph rendering
│   └── ui_helpers.py            # Streamlit UI components
│
├── data/
│   ├── raw/                     # Source CSV files
│   ├── data_cleaned.csv
│   ├── data_transformed.csv
│   └── analysis/                # Parquet cache (block → query → latest.parquet)
│
├── tests/
│   ├── conftest.py
│   └── test_graph.py
│
├── settings.py                  # Centralized config loaded from .env
├── requirements.txt
└── .env.example
```

---

## Analysis Blocks

| Block | Analytical question | Key outputs |
|---|---|---|
| **1 — Operational Baseline** | How does the supply chain perform under normal and observed conditions? | Global KPIs, delay severity distribution, OD redundancy profile |
| **2 — Risk Analysis** | Where is risk concentrated and which lanes are most exposed? | Risk level breakdown, critical lanes, inbound / outbound city exposure |
| **3 — Structural Vulnerability** | Which nodes and routes are structurally critical? | PageRank, betweenness centrality, weighted degree, route vulnerability map |
| **4 — Communities & Geography** | How does the network self-organise geographically? | Community detection, inter-community flows, country-level exposure |
| **5 — Cost & Mitigation** | What is the financial cost of disruptions and which mitigations work? | Disruption cost baseline, mitigation effectiveness, expedited air usage |
| **6 — What-If Simulation** | What happens to the network if a city or route is disabled? | Simulated flow rerouting, cost delta, redundancy impact |

Block 3 and Block 4 require Neo4j GDS write-back steps (centrality projections, community detection) before their read queries run. The scheduler handles this automatically.

---

## AI Agent

The `agent/` module implements a **LangGraph ReAct agent** that answers natural-language questions directly over the Knowledge Graph.

**Execution flow:**
1. **Chitchat classifier** (Gemini Flash) — routes trivial messages away from Neo4j.
2. **History fast-path** (Gemini Flash) — answers from conversation context when no new query is needed.
3. **ReAct loop** (Gemini Pro) — iteratively calls `query_graph` to fetch data, then synthesises a natural-language answer.

**`query_graph` tool** executes read-only Cypher with a built-in validation firewall:
- Blocks all write operations (`MERGE`, `CREATE`, `DELETE`, `SET`, `REMOVE`, `DROP`).
- Enforces a whitelist of allowed node labels and relationship types.
- Caps results at 30 records to keep the ReAct context bounded.
- Auto-injects a `LIMIT` clause if absent.

The agent supports multilingual questions (answers in the same language as the query) and optionally generates charts from tabular tool results.

---

## Prerequisites

- Python 3.12
- Neo4j 5.x with the **Graph Data Science (GDS)** plugin enabled
- A Google **Gemini API key** (models: `gemini-2.5-flash` and `gemini-2.5-pro`)
- LangSmith account (optional, for tracing)

---

## Setup

```bash
# 1. Clone the repository
git clone https://github.com/poltermes21/Supply-Chain-KG.git
cd Supply-Chain-KG

# 2. Create and activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your Neo4j credentials and Gemini API key
```

### Run the data pipeline

```bash
python -m data_pipeline.pipeline
```

Outputs `data/data_cleaned.csv` and `data/data_transformed.csv`.

### Build the Knowledge Graph

```bash
python -m kg_builder.graph_builder
```

Connects to Neo4j, creates all nodes and relationships via batched MERGE writes.

### Run the analysis cache

```bash
python -m analysis.scheduler
```

Executes all six query blocks and writes results to `data/analysis/` as Parquet files.

### Launch the Streamlit platform

```bash
streamlit run platform/Home.py
```

---

## Configuration

All settings are read from `.env` (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `DATA_DIRECTORY` | `data` | Root data directory |
| `RAW_DATA` | `raw/global_supply_chain_v2.csv` | Source CSV path (relative to `DATA_DIRECTORY`) |
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j Bolt connection URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | — | Neo4j password |
| `INTERFACE_GEMINI_MODEL` | `gemini-2.5-flash` | Fast model for chitchat and history routing |
| `REASONING_GEMINI_MODEL` | `gemini-2.5-pro` | Reasoning model for the ReAct loop |
| `GEMINI_API_KEY` | — | Google AI API key |
| `LANGSMITH_TRACING` | `true` | Enable LangSmith tracing (optional) |
| `LANGSMITH_API_KEY` | — | LangSmith API key (optional) |
| `LANGSMITH_PROJECT` | — | LangSmith project name (optional) |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Graph database | Neo4j 5.x + Graph Data Science (GDS) |
| Graph query language | Cypher |
| Agent framework | LangGraph + LangChain |
| LLM | Google Gemini 2.5 Flash / Pro |
| Data processing | Pandas, NumPy |
| Serialisation / cache | Apache Parquet (PyArrow) |
| Visualisation | Plotly, PyVis, Matplotlib |
| Dashboard | Streamlit |
| Testing | pytest |
