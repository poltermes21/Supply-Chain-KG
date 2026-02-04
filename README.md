# Supply Chain Knowledge Graph

Design and implementation of a Knowledge Graph-based architecture for Supply Chain resilience analysis and semantic risk modeling using Neo4j.

## Overview

This project provides a complete data pipeline for building and analyzing a Supply Chain Knowledge Graph. The system enables:

- **Data Integration**: Clean and transform CSV data into graph structures
- **Knowledge Modeling**: Represent products, suppliers, routes, and risks as connected entities
- **Resilience Analysis**: Identify single points of failure and assess supply chain vulnerabilities
- **What-If Scenarios**: Simulate disruptions and evaluate alternative strategies
- **Risk Assessment**: Analyze and prioritize risks across the supply chain

## Architecture

```
Supply-Chain-KG/
├── data_pipeline/       # Data loading and transformation
│   ├── loader.py        # CSV data loading and cleaning
│   └── transformer.py   # Transform data to nodes/edges
├── kg_model/            # Neo4j knowledge graph model
│   ├── connection.py    # Database connection utilities
│   ├── schema.py        # Schema and constraints
│   ├── product.py       # Product entity queries
│   ├── supplier.py      # Supplier entity queries
│   ├── route.py         # Route entity queries
│   ├── risk.py          # Risk entity queries
│   └── relationships.py # Relationship queries
├── analysis/            # Analysis and visualization
│   └── resilience_analysis.ipynb  # Jupyter notebook for analysis
├── data/                # Sample CSV data files
│   ├── products.csv
│   ├── suppliers.csv
│   ├── routes.csv
│   ├── risks.csv
│   ├── supplier_products.csv
│   ├── supplier_routes.csv
│   └── entity_risks.csv
├── pipeline.py          # Main pipeline script
└── requirements.txt     # Python dependencies
```

## Prerequisites

- Python 3.8 or higher
- Neo4j Database 5.0+ (local or remote instance)
- pip (Python package manager)

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Pallofa04/Supply-Chain-KG.git
   cd Supply-Chain-KG
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Neo4j**:
   - Install Neo4j Desktop or use Neo4j Aura (cloud)
   - Create a new database
   - Note your connection credentials (URI, username, password)

4. **Configure environment variables** (optional):
   Create a `.env` file in the project root:
   ```
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password
   ```

## Usage

### 1. Run the Data Pipeline

Execute the main pipeline to load data into Neo4j:

```bash
python pipeline.py
```

This script will:
1. Connect to Neo4j database
2. Create schema and constraints
3. Load CSV data files
4. Transform data into nodes and edges
5. Populate the knowledge graph
6. Verify the data was loaded correctly

### 2. Explore the Knowledge Graph

Open Neo4j Browser (usually at http://localhost:7474) and run sample queries:

```cypher
// View all products
MATCH (p:Product) RETURN p LIMIT 10

// Find suppliers for a product
MATCH (s:Supplier)-[r:SUPPLIES]->(p:Product {product_id: 'P001'})
RETURN s, r, p

// Find products with high risks
MATCH (p:Product)-[hr:HAS_RISK]->(risk:Risk)
WHERE risk.severity >= 7
RETURN p, hr, risk
```

### 3. Run Resilience Analysis

Launch Jupyter Notebook to perform resilience analysis:

```bash
jupyter notebook analysis/resilience_analysis.ipynb
```

The notebook includes:
- **Single Points of Failure**: Identify critical suppliers and products
- **What-If Scenarios**: Simulate supplier or route disruptions
- **Risk Assessment**: Prioritize risks using severity and probability
- **Supply Chain Optimization**: Find cost savings and diversification opportunities

## Data Model

### Node Types

1. **Product**: Items in the supply chain
   - Properties: `product_id`, `product_name`, `category`, `unit_price`

2. **Supplier**: Organizations providing products
   - Properties: `supplier_id`, `supplier_name`, `location`, `reliability_score`

3. **Route**: Logistics routes for transportation
   - Properties: `route_id`, `origin`, `destination`, `distance`, `lead_time`

4. **Risk**: Potential disruptions or issues
   - Properties: `risk_id`, `risk_type`, `severity`, `probability`, `description`

### Relationship Types

1. **SUPPLIES**: Supplier → Product
   - Properties: `capacity`, `cost`

2. **USES_ROUTE**: Supplier → Route

3. **HAS_RISK**: Any entity → Risk
   - Properties: `impact_level`

## Example Analyses

### Find Single Points of Failure

```python
from kg_model.connection import Neo4jConnection

conn = Neo4jConnection()
conn.connect()

query = """
MATCH (p:Product)<-[:SUPPLIES]-(s:Supplier)
WITH p, count(s) as supplier_count
WHERE supplier_count = 1
RETURN p.product_name as product, supplier_count
"""

results = conn.execute_query(query)
print(results)
```

### Simulate Supplier Loss

```python
def analyze_supplier_loss(supplier_id):
    query = """
    MATCH (s:Supplier {supplier_id: $supplier_id})-[:SUPPLIES]->(p:Product)
    MATCH (p)<-[:SUPPLIES]-(alt:Supplier)
    WHERE alt.supplier_id <> s.supplier_id
    WITH p, count(alt) as alternatives
    WHERE alternatives = 0
    RETURN p.product_name as at_risk_product
    """
    return conn.execute_query(query, {'supplier_id': supplier_id})
```

## Sample Data

The project includes sample CSV files in the `data/` directory:
- 10 products across Electronics, Materials, and Chemicals
- 10 suppliers from different global locations
- 10 logistics routes
- 10 risk types (geopolitical, natural disasters, quality, etc.)

You can replace these with your own data following the same CSV structure.

## Customization

### Adding New Data

1. Place CSV files in the `data/` directory
2. Ensure column names match expected format (see existing files)
3. Run `python pipeline.py` to reload data

### Extending the Model

1. Add new node types in `data_pipeline/transformer.py`
2. Create corresponding Cypher scripts in `kg_model/`
3. Update `pipeline.py` to include new entities

### Custom Queries

Add custom analysis queries in:
- `kg_model/*.py` for reusable Cypher queries
- `analysis/resilience_analysis.ipynb` for interactive analysis

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is open source and available under the MIT License.

## Contact

For questions or support, please open an issue on GitHub.
