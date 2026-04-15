import numpy as np

N_ORDERS = 15000
START_DATE = "2024-01-01"
END_DATE   = "2026-01-31"
SEED       = 42

# ── OD PAIRS ─────────────────────────────────────────────────────────────────
# Routes: Suez | Pacific | Atlantic | Intra-Asia | CoGH (Cape of Good Hope)
# "Commodity" replaced by "CoGH" (correct geographical corridor)
# "Pacific" removed from all Asia→Europe pairs (geographically impossible)
OD_ROUTES = {
    # SUEZ — Asia/India → Europe via Red Sea + Suez Canal
    ("Shenzhen, CN",  "Rotterdam, NL"):  [("Suez", 0.75), ("CoGH", 0.25)],
    ("Shanghai, CN",  "Rotterdam, NL"):  [("Suez", 0.70), ("CoGH", 0.30)],
    ("Mumbai, IN",    "Felixstowe, UK"): [("Suez", 0.85), ("CoGH", 0.15)],
    ("Mumbai, IN",    "Antwerp, BE"):    [("Suez", 0.85), ("CoGH", 0.15)],
    ("Shanghai, CN",  "Hamburg, DE"):    [("Suez", 0.70), ("CoGH", 0.30)],
    ("Busan, KR",     "Rotterdam, NL"):  [("Suez", 0.65), ("CoGH", 0.35)],
    ("Singapore, SG", "Hamburg, DE"):    [("Suez", 0.80), ("CoGH", 0.20)],
    ("Singapore, SG", "Rotterdam, NL"):  [("Suez", 0.80), ("CoGH", 0.20)],
    ("Busan, KR",     "Hamburg, DE"):    [("Suez", 0.70), ("CoGH", 0.30)],
    # PACIFIC — Asia → North America West Coast
    ("Shanghai, CN",  "Los Angeles, US"):[("Pacific", 0.95), ("CoGH", 0.05)],
    ("Tokyo, JP",     "Los Angeles, US"):[("Pacific", 1.00)],
    ("Busan, KR",     "Los Angeles, US"):[("Pacific", 0.95), ("CoGH", 0.05)],
    ("Shenzhen, CN",  "Los Angeles, US"):[("Pacific", 1.00)],
    # PACIFIC + Panama — Asia → US East Coast
    ("Shanghai, CN",  "New York, US"):   [("Pacific", 0.80), ("Suez", 0.20)],
    # ATLANTIC — Europe ↔ Americas
    ("Hamburg, DE",   "New York, US"):   [("Atlantic", 1.00)],
    ("Rotterdam, NL", "New York, US"):   [("Atlantic", 1.00)],
    ("Hamburg, DE",   "Santos, BR"):     [("Atlantic", 1.00)],
    ("Santos, BR",    "Rotterdam, NL"):  [("Atlantic", 0.60), ("CoGH", 0.40)],
    # INTRA-ASIA — within Asia
    ("Tokyo, JP",     "Singapore, SG"):  [("Intra-Asia", 1.00)],
    ("Shanghai, CN",  "Singapore, SG"):  [("Intra-Asia", 1.00)],
    ("Busan, KR",     "Singapore, SG"):  [("Intra-Asia", 1.00)],
    ("Shenzhen, CN",  "Tokyo, JP"):      [("Intra-Asia", 1.00)],
    ("Mumbai, IN",    "Shanghai, CN"):   [("Intra-Asia", 0.70), ("CoGH", 0.30)],
    # CoGH — South America bulk → Asia
    ("Santos, BR",    "Shanghai, CN"):   [("CoGH", 1.00)],
    # Europe → Asia (Rotterdam as bidirectional hub)
    ("Rotterdam, NL", "Singapore, SG"):  [("Suez", 0.80), ("CoGH", 0.20)],
}

OD_WEIGHTS = {
    ("Shenzhen, CN",  "Rotterdam, NL"):  2.5,
    ("Shanghai, CN",  "Rotterdam, NL"):  2.0,
    ("Mumbai, IN",    "Felixstowe, UK"): 1.8,
    ("Shanghai, CN",  "Los Angeles, US"):2.2,
    ("Tokyo, JP",     "Los Angeles, US"):1.5,
    ("Hamburg, DE",   "New York, US"):   1.5,
    ("Santos, BR",    "Shanghai, CN"):   1.2,
    ("Tokyo, JP",     "Singapore, SG"):  1.3,
    ("Shanghai, CN",  "Singapore, SG"):  1.4,
    ("Singapore, SG", "Rotterdam, NL"):  1.3,
    ("Busan, KR",     "Hamburg, DE"):    1.2,
    ("Shanghai, CN",  "New York, US"):   1.4,
    ("Rotterdam, NL", "Singapore, SG"):  1.1,
}

# ── LEAD TIMES ────────────────────────────────────────────────────────────────
LEAD_TIME = {
    "Intra-Asia": {
        "Sea": {"base": (5,  14), "buffer": 0.05},
        "Air": {"base": (1,   2), "buffer": 0.00},
    },
    "Atlantic": {
        "Sea": {"base": (8,  18), "buffer": 0.07},
        "Air": {"base": (1,   3), "buffer": 0.00},
    },
    "Pacific": {
        "Sea": {"base": (14, 24), "buffer": 0.08},
        "Air": {"base": (2,   4), "buffer": 0.00},
    },
    "Suez": {
        "Sea": {"base": (18, 32), "buffer": 0.10},
        "Air": {"base": (2,   4), "buffer": 0.00},
    },
    "CoGH": {
        "Sea": {"base": (25, 45), "buffer": 0.08},
        "Air": {"base": (3,   5), "buffer": 0.00},
    },
}

DELAY_BY_DISRUPTION = {
    "No_Disruption":                           {"mean": 0,  "std": 0.3, "max": 2},
    "Port Congestion":                         {"mean": 4,  "std": 2.0, "max": 12},
    "Severe Weather (Typhoon/Storm)":          {"mean": 7,  "std": 2.5, "max": 18},
    "Severe Weather (Cape Storms)":            {"mean": 6,  "std": 2.0, "max": 15},
    "Geopolitical Conflict (Route Diversion)": {"mean": 14, "std": 3.5, "max": 28},
}

MITIGATION_REDUCTION = {
    "Standard Shipping":     0.00,
    "Re-routing":            0.25,
    "Expedited Air Freight": 0.55,
}

# ── DISRUPTIONS ───────────────────────────────────────────────────────────────
DISRUPTION_BASE_PROB = {
    ("Suez",       "Sea"):  0.16,
    ("Suez",       "Air"):  0.04,
    ("Pacific",    "Sea"):  0.14,
    ("Pacific",    "Air"):  0.04,
    ("Atlantic",   "Sea"):  0.10,
    ("Atlantic",   "Air"):  0.03,
    ("Intra-Asia", "Sea"):  0.12,
    ("Intra-Asia", "Air"):  0.03,
    ("CoGH",       "Sea"):  0.13,
    ("CoGH",       "Air"):  0.03,
}

# Geopolitical Conflict → Suez ONLY
# Severe Weather (Typhoon/Storm) → Pacific, Intra-Asia, Atlantic
# Severe Weather (Cape Storms) → CoGH ONLY
# Port Congestion → all Sea routes
DISRUPTION_TYPES = {
    "Suez": {
        "Geopolitical Conflict (Route Diversion)": 0.55,
        "Port Congestion":                         0.40,
        "Severe Weather (Typhoon/Storm)":          0.05,
    },
    "Pacific": {
        "Severe Weather (Typhoon/Storm)": 0.50,
        "Port Congestion":                0.50,
    },
    "Atlantic": {
        "Port Congestion":                0.70,
        "Severe Weather (Typhoon/Storm)": 0.30,
    },
    "Intra-Asia": {
        "Severe Weather (Typhoon/Storm)": 0.55,
        "Port Congestion":                0.45,
    },
    "CoGH": {
        "Severe Weather (Cape Storms)": 0.55,
        "Port Congestion":              0.45,
    },
}

ANTICIPATION_FACTOR = {
    "No_Disruption":                           0.0,
    "Port Congestion":                         0.50,
    "Severe Weather (Typhoon/Storm)":          0.40,
    "Severe Weather (Cape Storms)":            0.40,
    "Geopolitical Conflict (Route Diversion)": 0.25,
}

RISK_DISRUPTION_MULTIPLIER = {
    "low":      0.5,
    "medium":   1.0,
    "high":     1.6,
    "critical": 2.2,
}

# ── RISK BY ROUTE ─────────────────────────────────────────────────────────────
# (geo_mean, geo_std, weather_mean, weather_std)
RISK_BY_ROUTE = {
    "Suez":       (0.65, 0.18, 3.5, 2.0),
    "Pacific":    (0.35, 0.15, 7.0, 2.0),
    "Atlantic":   (0.30, 0.15, 4.5, 2.2),
    "Intra-Asia": (0.35, 0.15, 6.0, 2.2),
    "CoGH":       (0.22, 0.12, 6.5, 2.3),
}

# ── COSTS ─────────────────────────────────────────────────────────────────────
COST_BASE_SEA = {
    "Intra-Asia": 1800,
    "Atlantic":   2800,
    "Pacific":    3500,
    "Suez":       4200,  # includes Suez Canal toll
    "CoGH":       4800,  # longer distance, no canal toll
}
AIR_MULTIPLIER = 9.0

PRODUCT_COST_FACTOR = {
    "Pharmaceuticals":      2.8,
    "Semiconductors":       2.5,
    "Consumer Electronics": 1.2,
    "Auto Parts":           1.0,
    "Textiles":             0.85,
    "Perishable Foods":     1.1,
    "Raw Materials":        0.75,
}

MITIGATION_COST_FACTOR = {
    "Standard Shipping":     1.00,
    "Re-routing":            1.30,
    "Expedited Air Freight": 2.50,
}

# ── PRODUCTS BY ORIGIN ────────────────────────────────────────────────────────
PRODUCT_BY_ORIGIN = {
    "Shanghai, CN":   {"Consumer Electronics": 0.30, "Semiconductors": 0.25,
                       "Auto Parts": 0.20, "Textiles": 0.15,
                       "Pharmaceuticals": 0.05, "Raw Materials": 0.03,
                       "Perishable Foods": 0.02},
    "Shenzhen, CN":   {"Consumer Electronics": 0.35, "Semiconductors": 0.30,
                       "Textiles": 0.15, "Auto Parts": 0.12,
                       "Pharmaceuticals": 0.05, "Raw Materials": 0.02,
                       "Perishable Foods": 0.01},
    "Tokyo, JP":      {"Auto Parts": 0.35, "Consumer Electronics": 0.25,
                       "Semiconductors": 0.20, "Pharmaceuticals": 0.10,
                       "Textiles": 0.05, "Raw Materials": 0.03,
                       "Perishable Foods": 0.02},
    "Busan, KR":      {"Auto Parts": 0.30, "Semiconductors": 0.25,
                       "Consumer Electronics": 0.20, "Textiles": 0.15,
                       "Raw Materials": 0.05, "Pharmaceuticals": 0.03,
                       "Perishable Foods": 0.02},
    "Singapore, SG":  {"Pharmaceuticals": 0.25, "Consumer Electronics": 0.25,
                       "Semiconductors": 0.20, "Auto Parts": 0.15,
                       "Textiles": 0.10, "Raw Materials": 0.03,
                       "Perishable Foods": 0.02},
    "Mumbai, IN":     {"Textiles": 0.35, "Pharmaceuticals": 0.30,
                       "Raw Materials": 0.15, "Consumer Electronics": 0.08,
                       "Auto Parts": 0.06, "Perishable Foods": 0.04,
                       "Semiconductors": 0.02},
    "Rotterdam, NL":  {"Auto Parts": 0.30, "Consumer Electronics": 0.20,
                       "Pharmaceuticals": 0.20, "Textiles": 0.15,
                       "Raw Materials": 0.10, "Semiconductors": 0.03,
                       "Perishable Foods": 0.02},
    "Hamburg, DE":    {"Auto Parts": 0.35, "Consumer Electronics": 0.20,
                       "Pharmaceuticals": 0.15, "Textiles": 0.15,
                       "Raw Materials": 0.10, "Semiconductors": 0.03,
                       "Perishable Foods": 0.02},
    "Santos, BR":     {"Raw Materials": 0.45, "Perishable Foods": 0.25,
                       "Textiles": 0.15, "Auto Parts": 0.08,
                       "Consumer Electronics": 0.04, "Pharmaceuticals": 0.02,
                       "Semiconductors": 0.01},
}

# ── AIR PROBABILITY ───────────────────────────────────────────────────────────
AIR_PROB_BY_PRODUCT = {
    "Pharmaceuticals":      0.45,
    "Semiconductors":       0.38,
    "Perishable Foods":     0.35,
    "Consumer Electronics": 0.15,
    "Auto Parts":           0.10,
    "Textiles":             0.06,
    "Raw Materials":        0.04,
}
AIR_ROUTE_MODIFIER = {
    "Intra-Asia": 0.6,
    "Atlantic":   1.0,
    "Pacific":    1.1,
    "Suez":       0.9,
    "CoGH":       0.6,
}

# ── MITIGATION BY DISRUPTION ──────────────────────────────────────────────────
MITIGATION_BY_DISRUPTION = {
    "No_Disruption": {
        "Standard Shipping": 1.00,
    },
    "Port Congestion": {
        "Standard Shipping":     0.60,
        "Re-routing":            0.25,
        "Expedited Air Freight": 0.15,
        
    },
    "Geopolitical Conflict (Route Diversion)": {
        "Standard Shipping":     0.10,
        "Re-routing":            0.35,
        "Expedited Air Freight": 0.55        
    },
    "Severe Weather (Typhoon/Storm)": {
        "Standard Shipping":     0.35,
        "Re-routing":            0.50,
        "Expedited Air Freight": 0.15,
    },
    "Severe Weather (Cape Storms)": {
        "Standard Shipping":     0.50,
        "Re-routing":            0.40,
        "Expedited Air Freight": 0.10,
    },
}