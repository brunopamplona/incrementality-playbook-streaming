"""Export the simulated panel as analyst-friendly datasets.

campaign_daily : what a media/BI team sees (spend, impressions, clicks, video views, platform-reported subs
                 per channel, geo, day)
creative_daily / creative_catalog : the same funnel at creative level, plus creative attributes
outcomes_daily : what the business sees (new subscribers and new MRR per geo, day, plan)
ground_truth   : what nobody sees in real life (true causal effect of each channel); for benchmarking only
creative_truth : hidden creative quality and fatigue parameters; for benchmarking only
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .funnel import simulate_funnel
from .config import SimConfig


def export_datasets(df: pd.DataFrame, cfg: SimConfig, out_dir: str | Path) -> dict:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    chans = [c.name for c in cfg.channels]
    platform = {c.name: c.platform for c in cfg.channels}
    plans = [p for p, _ in cfg.plan_mix]
    key = ["date", "geo"]

    funnel = simulate_funnel(df, cfg)
    campaign = funnel["campaign_daily"]

    outcomes = df[key + ["population", "event_intensity", "new_subs", *[f"new_subs_{p}" for p in plans], "new_mrr"]].copy()
    outcomes["event_intensity"] = outcomes["event_intensity"].round(4)
    outcomes["new_mrr"] = outcomes["new_mrr"].round(2)

    truth_cols = key + ["true_organic"] + [f"true_incr_{c}" for c in chans] + \
        [f"true_incr_{c}__{p}" for c in chans for p in plans]
    truth = df[truth_cols].copy()
    truth[truth.columns[2:]] = truth[truth.columns[2:]].round(4)

    paths = {}
    frames = {"campaign_daily": campaign, "creative_daily": funnel["creative_daily"],
              "creative_catalog": funnel["creative_catalog"], "outcomes_daily": outcomes,
              "ground_truth": truth, "creative_truth": funnel["creative_truth"],
              "creative_truth_daily": funnel["creative_truth_daily"]}
    for name, frame in frames.items():
        path = out / f"{name}.csv.gz"
        frame.to_csv(path, index=False, compression="gzip")
        paths[name] = (path, len(frame))
    return paths
