"""
Chart Spec Generation Module

Given the user's question, the agent's final answer, and the DataFrames
produced by the agent's tool calls, asks Gemini Flash to propose up to three
chart specifications that would add genuine analytical value beyond the text
answer. Returns validated `ChartSpec` objects (specs that reference missing
columns or wrong indices are dropped before returning).

This step runs ON DEMAND — only when the user clicks the "Visualize" button
on a chartable answer. The chartable flag is precomputed deterministically in
`agent/graph.py` from the shape of the tool results, so this expensive step
never runs unless the user opts in.
"""

from typing import Literal, Optional

import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage
from prompts import CHART_GENERATION_SYSTEM
from pydantic import BaseModel, Field

from .llm import get_interface_llm


class ChartSpec(BaseModel):
    """One chart suggestion from the Flash chart-generation step."""
    df_index: int = Field(
        description="0-based index into the list of dataframes this chart should use",
    )
    chart_type: Literal["bar", "line", "scatter", "pie"] = Field(
        description="Plotly Express chart type that fits the data shape",
    )
    x_col: str = Field(description="Exact column name to use on the x-axis (or labels for pie)")
    y_col: str = Field(description="Exact column name to use on the y-axis (or values for pie)")
    color_col: Optional[str] = Field(
        default=None,
        description="Optional exact column name to use for color grouping",
    )
    title: str = Field(
        description="Short chart title in the same language as the user's question",
    )
    rationale: str = Field(
        description="One sentence explaining why this chart adds insight",
    )


class ChartPlan(BaseModel):
    """Wrapper so Flash can return zero, one, or several charts."""
    charts: list[ChartSpec] = Field(default_factory=list)


def _summarise_dataframes(dataframes: list[pd.DataFrame]) -> str:
    """Produce a compact textual summary of every DataFrame so Flash sees
    column names, dtypes, row count, and a short sample without using too
    many tokens."""
    parts = []
    for i, df in enumerate(dataframes):
        if df is None or df.empty:
            continue
        dtypes = {col: str(dt) for col, dt in df.dtypes.items()}
        sample = df.head(5).to_dict("records")
        parts.append(
            f"DataFrame {i}:\n"
            f"  rows: {len(df)}\n"
            f"  columns: {list(df.columns)}\n"
            f"  dtypes: {dtypes}\n"
            f"  sample (first 5 rows): {sample}"
        )
    return "\n\n".join(parts)


def _validate_specs(specs: list[ChartSpec], dataframes: list[pd.DataFrame]) -> list[ChartSpec]:
    """Drop specs that reference missing dataframes or columns. Drop invalid
    color_col references but keep the chart."""
    valid: list[ChartSpec] = []
    for spec in specs:
        if spec.df_index < 0 or spec.df_index >= len(dataframes):
            continue
        df = dataframes[spec.df_index]
        if df is None or df.empty:
            continue
        cols = set(df.columns)
        if spec.x_col not in cols or spec.y_col not in cols:
            continue
        if spec.color_col and spec.color_col not in cols:
            spec.color_col = None
        valid.append(spec)
    return valid[:3]


def generate_chart_specs(
    question: str,
    dataframes: list[pd.DataFrame],
    answer: str,
) -> list[ChartSpec]:
    """Ask Flash to propose up to 3 chart specs for the given answer + data.

    Returns an empty list if no DataFrames are chartable or if Flash decides
    no chart adds value.
    """
    if not dataframes:
        return []

    df_summary = _summarise_dataframes(dataframes)
    if not df_summary:
        return []

    llm = get_interface_llm(temperature=0)
    structured = llm.with_structured_output(ChartPlan)

    user_msg = HumanMessage(
        content=(
            f"## User question\n{question}\n\n"
            f"## Agent's answer\n{answer}\n\n"
            f"## Available dataframes\n{df_summary}\n\n"
            "Propose 0-3 charts (empty list if no chart genuinely adds value)."
        )
    )
    # Let exceptions propagate so the caller can surface a user-friendly
    # error (and distinguish a real failure from "Flash returned no charts").
    plan: ChartPlan = structured.invoke([
        SystemMessage(content=CHART_GENERATION_SYSTEM),
        user_msg,
    ])
    return _validate_specs(plan.charts or [], dataframes)
