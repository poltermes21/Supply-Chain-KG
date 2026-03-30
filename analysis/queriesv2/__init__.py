"""
queries/__init__.py
===================
Punt d'entrada centralitzat per a totes les consultes d'anàlisi.

Ús des de la app Streamlit:
    from analysis.queries import Bloc1Queries
    from analysis.queries import Bloc1Queries, Bloc2Queries   # múltiples
    from analysis.queries.base import get_driver, run_query   # utilitats

Ús per executar tots els blocs:
    from analysis.queries import Bloc1Queries
    data = Bloc1Queries.run_all(driver)
"""

from analysis.queries.base import get_driver, run_query

from analysis.queries.block1_operational import Block1Queries


__all__ = [
    "get_driver",
    "run_query",
    "Bloc1Queries",
    "Bloc2Queries",
    "Bloc3Queries",
    "Bloc4Queries",
    "Bloc5Queries",
    "Bloc6Queries",
]