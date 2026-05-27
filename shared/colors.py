"""
Centralised colour palettes for categorical fields shared across the platform
pages and the chat agent's chart rendering. Same hue always represents the
same value (a given route, risk level, shock status, community, etc.).
"""


# Routes
ROUTE_COLORS = {
    "Suez":       "#1D4ED8",
    "Pacific":    "#10B981",
    "Intra-Asia": "#F59E0B",
    "CoGH":       "#EF4444",
    "Atlantic":   "#8B5CF6",
}

# Risk levels
RISK_LEVEL_COLORS = {
    "low":      "#10B981",
    "medium":   "#F59E0B",
    "high":     "#EF4444",
    "critical": "#7C3AED",
}

# Shock status
SHOCK_STATUS_COLORS = {
    "fully_blocked": "#EF4444",
    "primary_loss":  "#F59E0B",
    "partial_loss":  "#3B82F6",
}

# Disruption types
DISRUPTION_PALETTE = [
    "#1D4ED8", "#10B981", "#F59E0B", "#EF4444",
    "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16",
]

# Redundancy profile
REDUNDANCY_PROFILE_COLORS = {
    "single_route":            "#EF4444",
    "Single Route":            "#EF4444",
    "highly_concentrated":     "#F59E0B",
    "Highly Concentrated":     "#F59E0B",
    "moderately_concentrated": "#3B82F6",
    "Moderately Concentrated": "#3B82F6",
    "well_diversified":        "#10B981",
    "Well Diversified":        "#10B981",
}

# Communities and any other unmapped categorical — palette assigned in order.
COMMUNITY_PALETTE = [
    "#F59E0B", "#3B82F6", "#10B981", "#EF4444",
    "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16",
]
DEFAULT_PALETTE = COMMUNITY_PALETTE


def _lookup(canonical: dict, value) -> str | None:
    """Case-insensitive lookup that tries lower / title / capitalize variants
    — column data is not always normalised by the source query."""
    if value in canonical:
        return canonical[value]
    s = str(value)
    for variant in (s.lower(), s.title(), s.capitalize()):
        if variant in canonical:
            return canonical[variant]
    return None


def _build_map(values, canonical: dict) -> dict:
    """Build ``{value: color}`` using canonical colours; values not in the
    canonical map fall back to ``DEFAULT_PALETTE`` (cycled), so the result
    always covers every input value."""
    result: dict = {}
    fallback_idx = 0
    for v in values:
        color = _lookup(canonical, v)
        if color is None:
            color = DEFAULT_PALETTE[fallback_idx % len(DEFAULT_PALETTE)]
            fallback_idx += 1
        result[v] = color
    return result


def infer_color_map(column_name: str, values) -> dict | None:
    """Return a ``{value: color}`` mapping aligned with the rest of the app,
    or ``None`` if ``column_name`` does not map to a known categorical.

    Matching is by column-name keyword (case-insensitive). For columns that
    look related to routes / profiles but whose values are not in the
    canonical maps, returns ``None`` so the caller can use a generic palette
    instead of a misleading mapping.
    """
    if not column_name:
        return None
    col = str(column_name).lower()

    # Routes — only if at least one observed value is a known route name.
    if "route" in col:
        if any(_lookup(ROUTE_COLORS, v) for v in values):
            return _build_map(values, ROUTE_COLORS)
        return None

    # Risk level.
    if "risk_level" in col:
        return _build_map(values, RISK_LEVEL_COLORS)

    # Shock status (Route Shock simulation).
    if "shock_status" in col or "shock" in col:
        return _build_map(values, SHOCK_STATUS_COLORS)

    # Disruption types — stable palette for any disruption category label.
    if "disruption" in col:
        sorted_vals = sorted({v for v in values if v is not None}, key=lambda v: str(v))
        return {
            v: DISRUPTION_PALETTE[i % len(DISRUPTION_PALETTE)]
            for i, v in enumerate(sorted_vals)
        }

    # Redundancy profile — only if at least one observed value is known.
    if "redundancy" in col or "profile" in col:
        if any(_lookup(REDUNDANCY_PROFILE_COLORS, v) for v in values):
            return _build_map(values, REDUNDANCY_PROFILE_COLORS)
        return None

    # Communities — palette assigned to sorted unique values (matches
    # smallest community_id gets the first palette colour).
    if "community" in col:
        sorted_vals = sorted({v for v in values if v is not None}, key=lambda v: str(v))
        return {v: DEFAULT_PALETTE[i % len(DEFAULT_PALETTE)]
                for i, v in enumerate(sorted_vals)}

    return None
