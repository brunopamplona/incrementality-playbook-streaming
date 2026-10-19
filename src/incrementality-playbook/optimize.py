"""Budget reallocation along the TRUE response curves (stage 5, first cut).

Holds the combined spend of a group of channels fixed and finds the split that maximises
contribution value (incremental subs x contribution LTV of the plans they land in).
Results are only as good as the response curves: on real data they would come from the
calibrated MMM (stage 4), not from ground truth.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .config import SimConfig
from .economics import true_channel_plan_summary
from .plans import plan_economics
from .simulator import channel_response, creative_multipliers, event_series_from_df
from .truth import spend_matrix


def optimal_split(df: pd.DataFrame, cfg: SimConfig, channels: list[str] | None = None,
                  bounds: tuple[float, float] = (0.2, 3.0)) -> pd.DataFrame:
    """Optimal share of the group's budget per channel, with value before/after.

    `bounds` limit how far each channel's spend may move vs. today (multiplier on current spend)
    so the answer stays inside the range the data covers.
    """
    channels = channels or [c.name for c in cfg.channels]
    spec = {c.name: c for c in cfg.channels}
    pop_k, total = cfg.pop_k, cfg.pop_k.sum()
    pe, cp = plan_economics(cfg), true_channel_plan_summary(df, cfg)
    ltv = {n: (cp.loc[n].incr_subs * pe.loc[cp.loc[n].index, "contrib_ltv"]).sum() / cp.loc[n].incr_subs.sum()
           for n in channels}
    mult = creative_multipliers(cfg, event_series_from_df(df, cfg))
    S = {n: spend_matrix(df, f"spend_{n}", cfg) for n in channels}
    base = np.array([S[n].sum() for n in channels])
    budget = base.sum()

    def value(k):
        return sum(channel_response(S[n] * kk, pop_k, spec[n], total, mult[n]).sum() * ltv[n]
                   for n, kk in zip(channels, k)) / 1e6

    res = minimize(lambda k: -value(k), np.ones(len(channels)), bounds=[bounds] * len(channels),
                   constraints={"type": "eq", "fun": lambda k: ((k * base).sum() - budget) / 1e6},
                   method="SLSQP", options={"ftol": 1e-12, "maxiter": 500})
    k = res.x
    years = cfg.n_days / 365
    out = pd.DataFrame({"current_share": base / budget, "optimal_share": k * base / budget,
                        "spend_multiplier": k}, index=channels)
    out.attrs["value_gain_pct"] = value(k) / value(np.ones(len(channels))) - 1
    out.attrs["value_gain_brl_per_year"] = (value(k) - value(np.ones(len(channels)))) * 1e6 / years
    return out
