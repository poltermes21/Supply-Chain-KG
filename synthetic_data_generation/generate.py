import numpy as np
import pandas as pd
from uuid import uuid4
from config import *

rng = np.random.default_rng(SEED)


# HELPERS
def weighted_choice(options: list, weights: list):
    """Return a single element sampled from options according to weights."""
    w = np.array(weights, dtype=float)
    w /= w.sum()
    return options[rng.choice(len(options), p=w)]


def clip01(x: float) -> float:
    return float(np.clip(x, 0.0, 1.0))


def clip_range(x: float, lo: float, hi: float) -> float:
    return float(np.clip(x, lo, hi))


# STEP 1: SAMPLE OD PAIRS

def sample_od_pairs(n: int) -> list:
    """
    Sample n origin-destination pairs according to OD_WEIGHTS.
    Pairs not listed in OD_WEIGHTS default to weight 1.0.
    """
    pairs  = list(OD_ROUTES.keys())
    w      = np.array([OD_WEIGHTS.get(p, 1.0) for p in pairs], dtype=float)
    w     /= w.sum()
    idx    = rng.choice(len(pairs), size=n, p=w)
    return [pairs[i] for i in idx]


# STEP 2: ASSIGN ROUTE

def assign_route(origin: str, destination: str) -> str:
    """
    For a given OD pair, sample the route according to its probability weights.
    Enables alternative-route what-if analysis in the Knowledge Graph.
    """
    opts   = OD_ROUTES[(origin, destination)]
    routes = [r for r, _ in opts]
    w      = [wt for _, wt in opts]
    return weighted_choice(routes, w)


# STEP 3: ASSIGN PRODUCT

def assign_product(origin: str) -> str:
    """
    Sample product category based on origin city's export specialisation.
    Falls back to the first city in PRODUCT_BY_ORIGIN if origin not found.
    """
    dist = PRODUCT_BY_ORIGIN.get(origin, list(PRODUCT_BY_ORIGIN.values())[0])
    return weighted_choice(list(dist.keys()), list(dist.values()))


# STEP 4: ASSIGN TRANSPORT MODE

def assign_mode(product: str, route: str) -> str:
    """
    Determine Sea/Air based on product value density and route length modifier.
    High-value, time-sensitive products (Pharma, Semiconductors) favour Air.
    Long routes (Commodity, Suez) slightly reduce the Air probability.
    """
    p_air = AIR_PROB_BY_PRODUCT[product] * AIR_ROUTE_MODIFIER[route]
    p_air = min(p_air, 0.95)
    return "Air" if rng.random() < p_air else "Sea"


# STEP 5: ASSIGN WEIGHT

WEIGHT_MEANS = {
    "Pharmaceuticals":      1500,
    "Semiconductors":       1200,
    "Consumer Electronics": 3000,
    "Auto Parts":           6000,
    "Textiles":             5500,
    "Raw Materials":        8000,
    "Perishable Foods":     4000,
}

def assign_weight(product: str) -> int:
    """
    Sample shipment weight (kg) from a normal distribution centred on the
    typical weight for each product category.
    Raw Materials and Auto Parts are bulkier; Pharma and Semiconductors lighter.
    """
    mu = WEIGHT_MEANS[product]
    return int(np.clip(rng.normal(mu, mu * 0.35), 100, 10_000))


# STEP 6: ASSIGN RISK INDICES

def assign_risk(route: str) -> tuple:
    """
    Sample geopolitical and weather risk indices from route-specific
    normal distributions. Returns (geo_risk, weather_risk, inflation,
    combined_risk, risk_level).

    combined_risk = 0.6 * geo + 0.4 * (weather / 10)
    Weights reflect that geopolitical disruptions tend to be more severe
    and longer-lasting than meteorological events.
    """
    gm, gs, wm, ws = RISK_BY_ROUTE[route]
    geo     = clip01(rng.normal(gm, gs))
    weather = clip_range(rng.normal(wm, ws), 0.0, 10.0)
    infl    = clip_range(rng.normal(3.5, 1.2), -1.5, 8.5)

    combined = 0.6 * geo + 0.4 * (weather / 10.0)
    if combined < 0.25:   level = "low"
    elif combined < 0.50: level = "medium"
    elif combined < 0.75: level = "high"
    else:                 level = "critical"

    return geo, weather, infl, combined, level


# STEP 7: ASSIGN DISRUPTION

def assign_disruption(route: str, mode: str, risk_level: str) -> str:
    """
    Determine whether a disruption occurs and which type.

    Mechanism:
      1. Base probability depends on route + mode (Sea always higher than Air).
      2. Risk level multiplies the base probability (causal chain:
         high risk → higher P(disruption) → higher delays).
      3. If disruption occurs, type is sampled from the route's conditional
         distribution (e.g., Geopolitical Conflict is exclusive to Suez).
    """
    base = DISRUPTION_BASE_PROB[(route, mode)]
    adj  = min(base * RISK_DISRUPTION_MULTIPLIER[risk_level], 0.45)

    if rng.random() < adj:
        dist = DISRUPTION_TYPES[route]
        return weighted_choice(list(dist.keys()), list(dist.values()))
    return "No_Disruption"


# STEP 8: ASSIGN LEAD TIMES AND DELAY

def assign_times(route: str, mode: str, disruption: str) -> tuple:
    """
    Clean separation of concerns:

    base_lt   : Deterministic geography (sampled once from route range).
    sched     : Adjusted baseline. Includes operational friction AND 
                weighted anticipation of the specific disruption.
                Represents a risk-adjusted schedule.
    actual    : base + stochastic disruption effect (mitigated if applicable).
                The real-world outcome including random variance.
    delay     : max(0, actual - sched)
                Positive only if the disruption exceeds the buffered 
                and anticipated time.
    """
    cfg     = LEAD_TIME[route][mode]
    base_lt = int(rng.integers(cfg["base"][0], cfg["base"][1] + 1))
    mitigation = assign_mitigation(disruption)

    d_cfg = DELAY_BY_DISRUPTION[disruption]
    if d_cfg["mean"] == 0:
        real_extra = max(0, int(round(rng.normal(0, d_cfg["std"]))))
    else:
        real_extra = int(np.clip(
            rng.normal(d_cfg["mean"], d_cfg["std"]), 0, d_cfg["max"]
        ))

    if real_extra > 0 and mitigation != "Standard Shipping":
        reduction  = MITIGATION_REDUCTION[mitigation]
        real_extra = max(0, int(round(real_extra * (1 - reduction))))

    actual = base_lt + real_extra

    ant           = ANTICIPATION_FACTOR[disruption]
    buffer_days   = base_lt * cfg["buffer"]
    expected_days = d_cfg["mean"] * ant         
    sched = int(round(base_lt + buffer_days + expected_days))

    delay  = max(0, actual - sched)
    status = "Late" if delay > 0 else "On Time"
    return base_lt, sched, actual, delay, mitigation, status

# STEP 9: ASSIGN MITIGATION

def assign_mitigation(disruption: str) -> str:
    """
    Sample mitigation action from the conditional distribution for each
    disruption type.
    - No_Disruption → always Standard Shipping
    - Port Congestion → Re-routing dominant (60%)
    - Geopolitical Conflict → Expedited Air Freight dominant (55%)
    - Severe Weather → Re-routing dominant (50%)
    """
    dist = MITIGATION_BY_DISRUPTION[disruption]
    return weighted_choice(list(dist.keys()), list(dist.values()))


# STEP 10: ASSIGN COST

def assign_cost(route: str, mode: str, product: str,
                weight_kg: int, mitigation: str) -> float:
    """
    Compute shipping cost (USD) using a multiplicative model:

        cost = base_route × mode_mult × product_mult
                         × weight_scale × mitigation_mult × noise

    base_route   : scales with distance and canal toll complexity
    mode_mult    : Air = 9× Sea (reflects real ~100× $/kg ratio, dampened
                   by Air selection bias toward lighter high-value cargo)
    product_mult : accounts for special handling, insurance, cold chain
    weight_scale : log-scale (container pricing is not strictly linear)
    mitigation   : Re-routing +30%, Expedited Air +150%
    noise        : Normal(1.0, 0.12) — market price variability
    """
    base        = COST_BASE_SEA[route]
    mode_mult   = AIR_MULTIPLIER if mode == "Air" else 1.0
    prod_mult   = PRODUCT_COST_FACTOR[product]
    weight_sc   = 0.7 + 0.6 * np.log1p(weight_kg) / np.log1p(10_000)
    mit_mult    = MITIGATION_COST_FACTOR[mitigation]
    noise       = max(rng.normal(1.0, 0.12), 0.6)
    return round(base * mode_mult * prod_mult * weight_sc * mit_mult * noise, 2)


# MAIN GENERATION LOOP

def generate_dataset(n: int = N_ORDERS) -> pd.DataFrame:
    """
    Orchestrate the full synthetic dataset generation pipeline.
    Each order is generated independently; all stochastic steps use the
    shared seeded RNG for full reproducibility.
    """
    dates    = pd.date_range(START_DATE, END_DATE, freq="h")
    od_pairs = sample_od_pairs(n)
    rows     = []

    for origin, destination in od_pairs:
        route      = assign_route(origin, destination)
        product    = assign_product(origin)
        mode       = assign_mode(product, route)
        weight_kg  = assign_weight(product)

        geo, weather, infl, combined, risk_level = assign_risk(route)
        disruption = assign_disruption(route, mode, risk_level)

        base_lt, sched_lt, actual_lt, delay, mitigation, status = assign_times(
            route, mode, disruption
        )
        
        cost = assign_cost(route, mode, product, weight_kg, mitigation)

        order_date = str(pd.Timestamp(rng.choice(dates)).date())
        order_id   = f"ORD-{uuid4().hex[:8].upper()}"

        rows.append({
            "Order_ID":                  order_id,
            "Order_Date":                order_date,
            "Origin_City":               origin,
            "Destination_City":          destination,
            "Route_Type":                route,
            "Transportation_Mode":       mode,
            "Product_Category":          product,
            "Base_Lead_Time_Days":       base_lt,
            "Scheduled_Lead_Time_Days":  sched_lt,
            "Actual_Lead_Time_Days":     actual_lt,
            "Delay_Days":                delay,
            "Delivery_Status":           status,
            "Disruption_Event":          disruption if disruption != "No_Disruption" else None,
            "Geopolitical_Risk_Index":   round(geo, 3),
            "Weather_Severity_Index":    round(weather, 2),
            "Inflation_Rate_Pct":        round(infl, 3),
            "Shipping_Cost_USD":         cost,
            "Order_Weight_Kg":           weight_kg,
            "Mitigation_Action_Taken":   mitigation,
        })

    df = pd.DataFrame(rows)
    return df.sample(frac=1, random_state=SEED).reset_index(drop=True)

if __name__ == "__main__":
    df = generate_dataset()
    out = "global_supply_chain_v2.csv"
    df.to_csv(out, index=False)
    print(f"Dataset saved: {out}  ({len(df):,} rows)")

    # Quick validation
    df["Disruption_Event"] = df["Disruption_Event"].fillna("No_Disruption")
    print("\n--- Route distribution ---")
    print(df["Route_Type"].value_counts(normalize=True).round(3))
    print("\n--- Mode distribution ---")
    print(df["Transportation_Mode"].value_counts(normalize=True).round(3))
    print("\n--- Disruption distribution ---")
    print(df["Disruption_Event"].value_counts(normalize=True).round(3))
    print("\n--- Avg delay by disruption ---")
    print(df.groupby("Disruption_Event")["Delay_Days"].mean().round(2))
    print("\n--- Risk-delay correlation ---")
    print(df[["Geopolitical_Risk_Index", "Weather_Severity_Index",
              "Delay_Days"]].corr().round(3))