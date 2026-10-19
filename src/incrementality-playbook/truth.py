"""Ground-truth economics of each channel, computed from the true response curves."""
from __future__ import annotations

import pandas as pd

from .config import SimConfig
from .simulator import channel_response, creative_multipliers, event_series_from_df


def spend_matrix(df: pd.DataFrame, col: str, cfg: SimConfig):
    """(G, T) matrix in cfg.geos order from the long panel."""
    return df.pivot(index="geo", columns="date", values=col).loc[cfg.geos].to_numpy()


def true_channel_summary(df: pd.DataFrame, cfg: SimConfig, bump: float = 0.10) -> pd.DataFrame:
    """Per channel: spend, true incremental subs, incremental CAC, marginal CAC.

    Incremental CAC = spend / subs that would vanish if the channel were switched off.
    Marginal CAC    = cost of the *next* subscriber: extra spend / extra subs for +`bump` spend.
    """
    pop_k, total = cfg.pop_k, cfg.pop_k.sum()
    mult = creative_multipliers(cfg, event_series_from_df(df, cfg))
    rows = []
    for spec in cfg.channels:
        spend = spend_matrix(df, f"spend_{spec.name}", cfg)
        base = channel_response(spend, pop_k, spec, total, mult[spec.name]).sum()
        up = channel_response(spend * (1 + bump), pop_k, spec, total, mult[spec.name]).sum()
        total_spend = spend.sum()
        rows.append({
            "channel": spec.name,
            "spend": total_spend,
            "true_incr_subs": base,
            "true_incr_cac": total_spend / base,
            "true_marginal_cac": bump * total_spend / (up - base),
        })
    out = pd.DataFrame(rows).set_index("channel")
    out["share_of_all_subs"] = out["true_incr_subs"] / df["new_subs"].sum()
    return out
