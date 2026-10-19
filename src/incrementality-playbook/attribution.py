"""Stage 2: the *naive* measurement methods most teams start with.

Both are deliberately realistic, not strawmen:
  * last-click / platform-reported attribution
  * per-capita panel regression with geo fixed effects (no time controls)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import SimConfig
from .truth import true_channel_summary

# Stylised "how likely is this channel to be the last touch" weights.
# Lower-funnel channels get more credit per unit of exposure; TV rarely gets a click.
LAST_TOUCH_WEIGHT = {"tv": 0.4, "youtube": 0.8, "meta_advantage": 2.5, "meta_reels_video": 1.2, "meta_remarketing": 4.5, "affiliates": 3.0, "search_brand": 4.0,
                     "search_generic": 3.0, "app_campaigns": 3.5, "pmax": 4.5}  # PMax also harvests brand queries
# Weight of conversions with no trackable touch (direct / organic). Calibrated so that last-click
# credits ~50% of new subs to paid media, matching the ~49% non-organic share of installs reported
# for OTT/live-streaming apps (AppsFlyer benchmark, proxy; not a Brazil subscription figure).
DIRECT_WEIGHT = 44.0


def last_click_credit_rows(df: pd.DataFrame, cfg: SimConfig) -> pd.DataFrame:
    """Row-level (geo, day) subs credited to each channel by the last-click proxy."""
    touch = pd.DataFrame({
        s.name: LAST_TOUCH_WEIGHT.get(s.name, 1.0) * df[f"spend_{s.name}"] / df[f"spend_{s.name}"].mean()
        for s in cfg.channels
    })
    share = touch.div(touch.sum(axis=1) + DIRECT_WEIGHT, axis=0)
    return share.mul(df["new_subs"], axis=0)


def last_click_attribution(df: pd.DataFrame, cfg: SimConfig) -> pd.DataFrame:
    """Allocate every new subscriber to a channel in proportion to touch propensity.

    touch_c = weight_c * (spend_c / mean spend_c). Mimics platform dashboards that
    credit whoever touched last, regardless of whether the touch changed anything.
    """
    credited = last_click_credit_rows(df, cfg).sum()
    spend = pd.Series({s.name: df[f"spend_{s.name}"].sum() for s in cfg.channels})
    return pd.DataFrame({"lastclick_subs": credited, "lastclick_cac": spend / credited})


def naive_panel_regression(df: pd.DataFrame, cfg: SimConfig) -> pd.DataFrame:
    """new_subs per 1k pop ~ spend per 1k pop per channel, with geo fixed effects.

    Ignores adstock, saturation, and time-varying confounders (events, seasonality).
    The coefficient is read as subs per R$, so implied CAC = 1 / coef.
    """
    names = [s.name for s in cfg.channels]
    pop_k = df["population"] / 1000
    y = df["new_subs"] / pop_k
    X = pd.DataFrame({n: df[f"spend_{n}"] / pop_k for n in names})
    y_dm = y - y.groupby(df["geo"]).transform("mean")
    X_dm = X - X.groupby(df["geo"]).transform("mean")
    coef, *_ = np.linalg.lstsq(X_dm.to_numpy(), y_dm.to_numpy(), rcond=None)
    coef = pd.Series(coef, index=names)
    spend = pd.Series({n: df[f"spend_{n}"].sum() for n in names})
    implied_subs = coef * spend
    cac = (spend / implied_subs).where(implied_subs > 0, np.inf)
    return pd.DataFrame({"regression_coef": coef, "regression_subs": implied_subs, "regression_cac": cac})


def compare_to_truth(df: pd.DataFrame, cfg: SimConfig) -> pd.DataFrame:
    """One table: truth vs. every naive method, with bias ratios (estimate / truth)."""
    t = true_channel_summary(df, cfg)
    out = t.join(last_click_attribution(df, cfg)).join(naive_panel_regression(df, cfg))
    out["lastclick_cac_bias"] = out["lastclick_cac"] / out["true_incr_cac"]
    out["regression_cac_bias"] = out["regression_cac"] / out["true_incr_cac"]
    return out


def platform_summary(df: pd.DataFrame, cfg: SimConfig, platform: str = "google") -> pd.DataFrame:
    """Platform view: what its dashboard (last-click proxy) reports vs the true incremental CAC."""
    t = compare_to_truth(df, cfg)
    names = [c.name for c in cfg.channels if c.platform == platform]
    g = t.loc[names]
    total = pd.Series({
        "spend": g["spend"].sum(), "true_incr_subs": g["true_incr_subs"].sum(),
        "lastclick_subs": g["lastclick_subs"].sum(),
    })
    total["true_incr_cac"] = total["spend"] / total["true_incr_subs"]
    total["lastclick_cac"] = total["spend"] / total["lastclick_subs"]
    total["lastclick_cac_bias"] = total["lastclick_cac"] / total["true_incr_cac"]
    g = g[["spend", "true_incr_subs", "lastclick_subs", "true_incr_cac", "lastclick_cac", "lastclick_cac_bias"]]
    return pd.concat([g, total.to_frame(f"TOTAL {platform}").T])
