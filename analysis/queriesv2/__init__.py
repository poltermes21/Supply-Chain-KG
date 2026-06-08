"""
queriesv2/__init__.py
===================
Punt d'entrada centralitzat per a totes les consultes d'anàlisi.

Ús des de la app Streamlit:
    from analysis.queriesv2 import Bloc1kQueries
    from analysis.queriesv2 import Bloc1kQueries, Bloc2Qkueries   # múltiples
    from analysis.queriesv2.base import get_driver, run_query   # utilitats

Ús per executar tots els blocs:
    from analysis.queriesv2 import Bloc1Queries
    data = Bloc1kQueries.run_all(driver)
"""

from analysis.queriesv2.base import get_driver, run_query

from analysis.queriesv2.block1_operational import Block1Queries
from analysis.queriesv2.block2_risk import Block2Queries
from analysis.queriesv2.block3_vulnerability import Block3Queries
from analysis.queriesv2.block4_communities import Block4Queries
from analysis.queriesv2.block5_costs import Block5Queries
from analysis.queriesv2.block6_what_if import Block6Queries


__all__ = [
    "get_driver",
    "run_query",
    "Block1Queries",
    "Block2Queries",
    "Block3Queries",
    "Block4Queries",
    "Block5Queries",
    "Block6Queries",
]