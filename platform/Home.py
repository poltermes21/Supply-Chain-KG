import streamlit as st
import pandas as pd
from shared.analysis_store import load_query_data

# 1. Page Configuration
st.set_page_config(
    page_title="Supply Chain Resilience KG",
    page_icon="🌐",
    layout="wide"
)

# 3. Hero Section (Landing Page Header)
st.title("Knowledge Graph-Based Supply Chain Architecture")
st.subheader("Decision Support System with Resilience Analysis")

st.markdown("""
This platform enables the exploration of global supply chain resilience through 
**Graph Analytics**. Powered by **Neo4j** and the **Graph Data Science (GDS)** library.
""")

st.divider()

# 4. Global Network Status (Data from Block 1)
st.header("Global Network Health")

# We wrap the data fetching in a spinner for better UX
with st.spinner("Fetching operational baseline..."):
    try:
        kpi_data = load_query_data("block1_operational", "global_baseline_kpis")
    except FileNotFoundError:
        kpi_data = pd.DataFrame()
    except Exception:
        kpi_data = pd.DataFrame()

if not kpi_data.empty:
    # Extract the first row of data
    row = kpi_data.iloc[0]
    
    # Create four layout columns for the metrics
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("Total Shipments", f"{int(row['total_orders']):,}")
    col2.metric("Delay Rate", f"{row['delay_rate_pct']}%", delta_color="inverse")
    col3.metric("Disruption Rate", f"{row['disruption_rate_pct']}%")
    col4.metric("Avg. Lead Time", f"{row['avg_actual_lead_time_days']} days")
else:
    st.error("No data found. Please check your Neo4j database content.")

st.info("👈 Use the sidebar to explore specific analysis blocks.")


temp = """
La caché semàntica de 3 nivells (Supabase + pgvector)
La idea era guardar pregunta+embedding+resposta i recuperar segons similitud. Funciona en teoria, però manté-la et menjarà el projecte:

Invalidació per canvi de dades: cada vegada que carregues noves comandes a Neo4j, els resultats cachejats queden obsolets en silenci. Has de mantenir una versió/hash del KG i invalidar el tier 1; si oblides un cop, dones números equivocats al tribunal.
Invalidació per canvi d'esquema: si renomenes una propietat (ja ho has fet, mira els últims commits), tots els Cypher cachejats peten o tornen dades errònies. Necessites versionar la caché per hash de l'esquema.
Similitud d'embedding ≠ equivalència semàntica: "rutes amb més retards" i "rutes amb menys retards" tenen embedding gairebé idèntic però resposta oposada. El mateix amb "top 5" vs "top 10". Per blindar-ho necessites una crida LLM extra de validació, i ja afegeixes una capa més.
Tuning de llindars: els valors d'exact_threshold i similarity_threshold no són evidents. Has de construir un eval set, mesurar falsos positius, ajustar. Feina constant.
Cache poisoning: si l'agent al·lucina una resposta un cop, queda cachejada per a tothom. Necessites flag de "validat" i revisió.
Resultat: tres mecanismes d'invalidació (dades, esquema, qualitat) + tuning empíric + crida extra de validació. Per a un projecte que ha de funcionar sol durant la defensa i després, és massa superfície.
"""