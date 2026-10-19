"""Channel x plan truth and plan-level LTV/CAC, computed from the simulator's ground truth."""
from __future__ import annotations

import pandas as pd

from .config import SimConfig
from .plans import plan_economics
from .truth import true_channel_summary


def true_channel_plan_summary(df: pd.DataFrame, cfg: SimConfig) -> pd.DataFrame:
    """True incremental subs per (channel, plan) and each plan's share of the channel's subs."""
    plans = [p for p, _ in cfg.plan_mix]
    spend = {c.name: df[f"spend_{c.name}"].sum() for c in cfg.channels}
    rows = []
    for c in cfg.channels:
        tot = df[f"true_incr_{c.name}"].sum()
        for p in plans:
            n = df[f"true_incr_{c.name}__{p}"].sum()
            rows.append({"channel": c.name, "plan": p, "incr_subs": n, "share_of_channel": n / tot,
                         "incr_subs_per_R$1M": n / spend[c.name] * 1e6})
    return pd.DataFrame(rows).set_index(["channel", "plan"])


def channel_value_roi(df: pd.DataFrame, cfg: SimConfig) -> pd.DataFrame:
    """Contribution value created per R$ 1 of spend, by channel (all plans, LTV-weighted)."""
    pe = plan_economics(cfg)
    cp = true_channel_plan_summary(df, cfg)
    ch = true_channel_summary(df, cfg)
    contrib = cp["incr_subs"] * cp.index.get_level_values("plan").map(pe["contrib_ltv"])
    value = contrib.groupby("channel").sum()
    out = pd.DataFrame({"spend": ch["spend"], "incr_subs": ch["true_incr_subs"],
                        "contrib_value": value.reindex(ch.index)})
    out["contrib_ltv_per_sub"] = out["contrib_value"] / out["incr_subs"]
    out["contrib_roi"] = out["contrib_value"] / out["spend"]
    out["marginal_contrib_roi"] = out["contrib_ltv_per_sub"] / ch["true_marginal_cac"]
    return out


def plan_ltv_cac(df: pd.DataFrame, cfg: SimConfig) -> pd.DataFrame:
    """Plan-level CAC and LTV/CAC.

    Plan CAC = subscriber-weighted average of the CAC of the channels that feed the plan
    (each channel's spend is spread over its subs, so every sub of a channel costs that channel's CAC).
    Marginal version uses each channel's marginal CAC. LTV is contribution LTV.
    """
    pe = plan_economics(cfg)
    cp = true_channel_plan_summary(df, cfg).reset_index()
    ch = true_channel_summary(df, cfg)
    cp["cac"] = cp["channel"].map(ch["true_incr_cac"])
    cp["mcac"] = cp["channel"].map(ch["true_marginal_cac"])
    rows = {}
    for plan, g in cp.groupby("plan"):
        w = g["incr_subs"] / g["incr_subs"].sum()
        cac, mcac = (g["cac"] * w).sum(), (g["mcac"] * w).sum()
        ltv = pe.loc[plan, "contrib_ltv"]
        rows[plan] = {"incr_subs": g["incr_subs"].sum(), "cac": cac, "marginal_cac": mcac,
                      "contrib_ltv": ltv, "ltv_cac": ltv / cac, "ltv_marginal_cac": ltv / mcac,
                      "payback_months": cac / (pe.loc[plan, "price_month"] * pe.loc[plan, "margin"]),
                      "margin_breakeven_at_marginal_cac": mcac / pe.loc[plan, "gross_ltv"]}
    return pd.DataFrame(rows).T
