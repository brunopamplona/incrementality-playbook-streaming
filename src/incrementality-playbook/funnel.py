"""Media funnel and creative layer on top of the simulated panel.

Adds impressions, clicks and video views per channel x UF x day, plus creative-level data
(catalog, daily metrics with creative fatigue). It is DESCRIPTIVE realism: creatives change CPM and
CTR but not the causal truth of the simulator (true incremental subs per channel are unchanged).

All unit prices (CPM) and click rates (CTR) are assumptions. Meta values are placed inside the Brazilian
ranges found for 2026 (feed CPM R$ 15-35, Reels/Stories CPM R$ 8-20, CPC R$ 0.40-6.00); the other channels
have no public streaming benchmark and are stylised. See docs/ASSUMPTIONS.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .attribution import last_click_credit_rows
from .config import SimConfig
from .creatives import CPM_ANNUAL_INFLATION, FUNNEL, build_catalog, creative_effect

def simulate_funnel(df: pd.DataFrame, cfg: SimConfig, seed: int | None = None) -> dict:
    """Return dict(campaign_daily, creative_daily, creative_catalog, creative_truth)."""
    rng = np.random.default_rng(cfg.seed + 1 if seed is None else seed)
    credit = last_click_credit_rows(df, cfg)
    day = (df["date"] - df["date"].min()).dt.days.to_numpy()
    geo_factor = dict(zip(cfg.geos, rng.lognormal(0, 0.12, len(cfg.geos))))
    gf = df["geo"].map(geo_factor).to_numpy()
    ev = np.minimum(df["event_intensity"].to_numpy(), 1.0)
    infl = (1 + CPM_ANNUAL_INFLATION) ** (day / 365)
    n = len(df)

    parts = []
    for c in cfg.channels:
        f = FUNNEL[c.name]
        spend = df[f"spend_{c.name}"].to_numpy()
        cpm = f.cpm * gf * infl * (1 + 0.25 * ev * f.auction) * rng.lognormal(0, 0.10, n)
        imp = np.rint(spend / cpm * 1000).astype(np.int64)
        clicks = (rng.binomial(imp, np.clip(f.ctr * rng.lognormal(0, 0.08, n), 0, 0.9)).astype(float)
                  if f.ctr else np.full(n, np.nan))
        views = (rng.binomial(imp, np.clip(f.view_rate * rng.lognormal(0, 0.08, n), 0, 0.95)).astype(float)
                 if f.view_rate else np.full(n, np.nan))
        parts.append(pd.DataFrame({
            "date": df["date"], "geo": df["geo"], "platform": c.platform, "channel": c.name,
            "spend_brl": spend.round(2), "impressions": imp, "clicks": clicks, "video_views": views,
            "platform_reported_subs": credit[c.name].to_numpy().round(3),
        }))
    campaign = pd.concat(parts, ignore_index=True).sort_values(["date", "geo", "channel"]).reset_index(drop=True)

    # ---- creative layer: allocate national channel-day totals to the active creatives ----
    cat = build_catalog(cfg)
    event_t = df[df['geo'] == cfg.geos[0]].sort_values('date')['event_intensity'].to_numpy()
    true_nat = df.groupby('date')[[f'true_incr_{c.name}' for c in cfg.channels]].sum()
    truth_rows = []
    dates = pd.date_range(df["date"].min(), periods=cfg.n_days, freq="D")
    nat = campaign.groupby(["channel", "date"], as_index=False).agg(
        spend=("spend_brl", "sum"), imp=("impressions", "sum"), clicks=("clicks", "sum"),
        views=("video_views", "sum"), reported=("platform_reported_subs", "sum"))
    rows = []
    for ch, g in nat.groupby("channel"):
        f = FUNNEL[ch]
        cc = cat[cat["channel"] == ch].reset_index(drop=True)
        g = g.sort_values("date").reset_index(drop=True)
        for t, r in g.iterrows():
            act = cc[(cc["launch_day"] <= t) & (cc["end_day"] > t)]
            if act.empty:                      # safety: keep the last-launched creative alive
                act = cc[cc["launch_day"] <= t].tail(1)
            age = t - act["launch_day"].to_numpy()
            q = act["quality"].to_numpy()
            fat = np.maximum(0.45, np.exp(-age / act["fatigue_days"].to_numpy()))
            w = q * (1 + 0.5 * (age < 14))                      # fresh creatives get exploration budget
            sp = r["spend"] * w / w.sum()
            p_imp = sp * q ** 0.3; p_imp = p_imp / p_imp.sum()  # better creatives are cheaper to deliver
            imp = rng.multinomial(int(r["imp"]), p_imp)
            if f.ctr:
                p_clk = imp * q * fat; p_clk = p_clk / p_clk.sum() if p_clk.sum() > 0 else p_imp
                clk = rng.multinomial(int(r["clicks"]), p_clk).astype(float)
                p_rep = clk / clk.sum() if clk.sum() > 0 else p_imp
            else:
                clk, p_rep = np.full(len(act), np.nan), imp / max(imp.sum(), 1)
            if f.view_rate:
                p_v = imp * q; p_v = p_v / p_v.sum()
                vw = rng.multinomial(int(r["views"]), p_v).astype(float)
            else:
                vw = np.full(len(act), np.nan)
            e = creative_effect(act["causal_lift"].to_numpy(), (act["theme"] == "futebol_ao_vivo").to_numpy(),
                                act["fatigue_days"].to_numpy(), age, event_t[t])
            wt = w * e
            tru = true_nat.loc[r["date"], f"true_incr_{ch}"] * wt / wt.sum()
            for i, cid in enumerate(act["creative_id"]):
                truth_rows.append((r["date"], cid, round(float(tru[i]), 4)))
                rows.append((r["date"], ch, cid, int(age[i]), round(float(sp[i]), 2), int(imp[i]), clk[i], vw[i],
                             round(float(r["reported"] * p_rep[i]), 3)))
    creative = pd.DataFrame(rows, columns=["date", "channel", "creative_id", "age_days", "spend_brl", "impressions",
                                           "clicks", "video_views", "platform_reported_subs"])
    creative.insert(2, "platform", creative["channel"].map({c.name: c.platform for c in cfg.channels}))

    start = df["date"].min()
    catalog = cat.drop(columns=["quality", "causal_lift", "fatigue_days"]).copy()
    catalog["launch_date"] = (start + pd.to_timedelta(catalog["launch_day"], unit="D")).dt.date
    catalog["end_date"] = (start + pd.to_timedelta(catalog["end_day"], unit="D")).dt.date
    catalog = catalog.drop(columns=["launch_day", "end_day"])
    truth = cat[["creative_id", "quality", "causal_lift", "fatigue_days"]].round(4)
    truth_daily = pd.DataFrame(truth_rows, columns=["date", "creative_id", "true_incr_subs"])
    return {"campaign_daily": campaign, "creative_daily": creative, "creative_catalog": catalog,
            "creative_truth": truth, "creative_truth_daily": truth_daily}
