"""Configuration: weights, thresholds, factor definitions."""

FACTOR_WEIGHTS = {
    "valuation":     0.20,
    "growth":        0.25,
    "profitability": 0.20,
    "momentum":      0.20,
    "revisions":     0.15,
}

FILTERS = {
    "min_market_cap":  500_000_000,
    "min_price":       5.0,
    "require_pos_eps": True,
    "min_avg_volume":  500_000,
}

QUALITY_BOOST = True
SECTOR_CAP = 0.30
MAX_POSITIONS = 25
MAX_SINGLE_WEIGHT = 0.05

STOP_LOSS_PCT = 0.25
TRIM_THRESHOLD = 2.0
QUANT_DOWNGRADE_EXIT = True

ALPHA_PICKS_THEMES = {
    "ai_infrastructure":  ["NVDA", "AMD", "AVGO", "MRVL", "MU", "CRDO", "LITE", "CLS", "APP", "ANET"],
    "power_grid":         ["POWL", "GEV", "ETN", "VRT", "PWR", "AGX", "STRL", "MYRG", "PRIM"],
    "data_center_reit":   ["EQIX", "DLR", "IRM"],
    "reshoring":          ["TTMI", "JBL", "FLEX", "SANM"],
    "precious_metals":    ["NEM", "KGC", "B", "AEM", "GOLD", "CDE", "SSRM", "NEXA"],
    "cyclical_recovery":  ["RCL", "CCL", "NCLH", "EAT", "DRI"],
}
