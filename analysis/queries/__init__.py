"""
queries/__init__.py
===================
Centralised entry point for all analysis queries.

Usage from the Streamlit app:
    from analysis.queries import Block1Queries
    from analysis.queries import Block1Queries, Block2Queries   # multiple
    from analysis.queries.base import get_driver, run_query   # utilities

Usage to run all blocks:
    from analysis.queries import Block1Queries
    data = Block1Queries.run_all(driver)
"""

from analysis.queries.base import get_driver, run_query

from analysis.queries.block1_operational import Block1Queries
from analysis.queries.block2_risk import Block2Queries
from analysis.queries.block3_vulnerability import Block3Queries
from analysis.queries.block4_communities import Block4Queries
from analysis.queries.block5_costs import Block5Queries
from analysis.queries.block6_what_if import Block6Queries


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