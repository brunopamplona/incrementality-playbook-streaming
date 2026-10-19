"""Plan unit economics: price, lifetime, churn, margin and LTV per plan."""
from __future__ import annotations

import pandas as pd

from .config import SimConfig


def plan_economics(cfg: SimConfig) -> pd.DataFrame:
    """Per plan: price, lifetime, churn, gross LTV and contribution LTV.

    Gross LTV        = monthly price x average lifetime (months)
    Contribution LTV = gross LTV x contribution margin
    Monthly churn    = 1 / lifetime (geometric lifetime with that mean).
    Also reports contribution LTV at the business range edges (30% and 55%).
    The 'blended' row weights plans by the organic mix.
    """
    price, life = dict(cfg.plan_price), dict(cfg.plan_avg_lifetime_months)
    margin, mix = dict(cfg.plan_contribution_margin), dict(cfg.plan_mix)
    out = pd.DataFrame({
        "price_month": price,
        "avg_lifetime_months": life,
        "monthly_churn": {p: 1 / life[p] for p in life},
        "margin": margin,
        "gross_ltv": {p: price[p] * life[p] for p in price},
        "organic_mix": mix,
    })
    out["contrib_ltv"] = out["gross_ltv"] * out["margin"]
    out["contrib_ltv_at_30pct"] = out["gross_ltv"] * 0.30
    out["contrib_ltv_at_55pct"] = out["gross_ltv"] * 0.55
    w = out["organic_mix"]
    out.loc["blended"] = [(out[c] * w).sum() if c != "organic_mix" else 1.0 for c in out.columns]
    return out
