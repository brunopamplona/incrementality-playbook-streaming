"""Creative layer: funnel specs, creative catalog and the CAUSAL effect of creatives.

Each creative has a hidden causal lift (theme, format, noise), a CTR/CPM quality (correlated 0.3 with
the lift, and *higher* for price-offer creatives that attract clicks but little incrementality) and
fatigue. A channel's daily effectiveness multiplier is the spend-weighted average effect of its active
creatives, normalised to mean 1 so channel-level CACs keep their calibration.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import SimConfig

THEMES = ("futebol_ao_vivo", "filmes_telecine", "bundle_streamings", "oferta_preco", "lancamento")
THEME_PLAN = {"futebol_ao_vivo": "premiere_futebol", "filmes_telecine": "telecine",
              "bundle_streamings": "claro_tv_bundle"}
HOOKS = ("gol_decisivo", "trailer", "comparativo_preco", "depoimento", "contagem_regressiva", "catalogo")


@dataclass(frozen=True)
class FunnelSpec:
    cpm: float                  # R$ per 1,000 impressions at the start of the period
    ctr: float | None           # clicks / impressions (None = no clicks, e.g. TV)
    view_rate: float | None     # video views / impressions (None = not a video channel)
    auction: bool               # CPM rises when demand events raise competition
    formats: tuple              # creative formats used on the channel
    launch_every_days: int      # a new creative every N days
    life_mult: tuple            # creative lifetime as a multiple of launch interval (min, max)
    duration_sec: dict          # creative length by format (None = not applicable)


FUNNEL = {
    "tv": FunnelSpec(18, None, None, False, ("spot_30s", "spot_15s"), 70, (1.5, 2.2),
                     {"spot_30s": 30, "spot_15s": 15}),
    "affiliates": FunnelSpec(12, 0.005, None, False, ("banner", "email", "partner_page"), 56, (1.5, 2.2),
                             {}),
    "youtube": FunnelSpec(28, 0.004, 0.28, True, ("video_15s", "video_30s", "bumper_6s"), 28, (1.6, 2.4),
                          {"video_15s": 15, "video_30s": 30, "bumper_6s": 6}),
    "search_brand": FunnelSpec(180, 0.18, None, True, ("responsive_search_ad",), 84, (1.5, 2.0), {}),
    "search_generic": FunnelSpec(99, 0.045, None, True, ("responsive_search_ad",), 42, (1.5, 2.2), {}),
    "app_campaigns": FunnelSpec(28, 0.010, None, True, ("video_15s", "static_image", "html5"), 21, (1.6, 2.4),
                                {"video_15s": 15}),
    "pmax": FunnelSpec(35, 0.009, 0.15, True, ("asset_group_video", "asset_group_image"), 35, (1.6, 2.4),
                       {"asset_group_video": 20}),
    "meta_advantage": FunnelSpec(22, 0.011, 0.20, True, ("reels_video", "static_image", "carousel"), 14, (1.6, 2.6),
                                 {"reels_video": 15}),
    "meta_reels_video": FunnelSpec(14, 0.007, 0.35, True, ("reels_video_15s", "reels_video_30s", "stories_video"), 21,
                                   (1.6, 2.4), {"reels_video_15s": 15, "reels_video_30s": 30, "stories_video": 10}),
    "meta_remarketing": FunnelSpec(30, 0.018, None, True, ("dynamic_carousel", "static_image", "reels_video"), 28,
                                   (1.6, 2.4), {"reels_video": 15}),
}

CPM_ANNUAL_INFLATION = 0.08



THEME_EFFECT = {"futebol_ao_vivo": 0.10, "bundle_streamings": 0.05, "filmes_telecine": 0.0,
                "oferta_preco": -0.10, "lancamento": 0.05}
FORMAT_EFFECT = {"reels_video": 0.05, "reels_video_15s": 0.05, "reels_video_30s": 0.07, "stories_video": 0.0,
                 "video_15s": 0.03, "video_30s": 0.06, "bumper_6s": -0.03, "spot_30s": 0.05, "spot_15s": 0.0,
                 "static_image": -0.05, "carousel": 0.0, "dynamic_carousel": 0.03, "html5": -0.02,
                 "asset_group_video": 0.04, "asset_group_image": -0.04, "banner": -0.05, "email": 0.02,
                 "partner_page": 0.04, "responsive_search_ad": 0.0}


def build_catalog(cfg: SimConfig) -> pd.DataFrame:
    """Deterministic creative catalog (own RNG stream, seed + 2). Hidden columns: quality, causal_lift, fatigue_days."""
    rng = np.random.default_rng(cfg.seed + 2)
    plans = [p for p, _ in cfg.plan_mix]
    rows = []
    for c in cfg.channels:
        f = FUNNEL[c.name]
        plan_w = dict(c.plan_mix)
        theme_w = np.array([0.8 * plan_w[THEME_PLAN[th]] if th in THEME_PLAN else 0.1 for th in THEMES])
        theme_w = theme_w / theme_w.sum()
        k, launch = 0, -int(1.2 * f.launch_every_days)
        while launch < cfg.n_days:
            life = int(f.launch_every_days * rng.uniform(*f.life_mult))
            theme = str(rng.choice(THEMES, p=theme_w))
            fmt = str(rng.choice(f.formats))
            z1, z2 = rng.standard_normal(2)
            lift = np.exp(THEME_EFFECT[theme] + FORMAT_EFFECT.get(fmt, 0.0) + 0.12 * (0.3 * z1 + np.sqrt(0.91) * z2))
            quality = np.exp(0.25 * z1) * (1.2 if theme == "oferta_preco" else 1.0)
            rows.append({
                "creative_id": f"{c.name}_{k:03d}", "channel": c.name, "platform": c.platform,
                "format": fmt, "theme": theme, "plan_promoted": THEME_PLAN.get(theme) or str(rng.choice(plans)),
                "hook": str(rng.choice(HOOKS)), "duration_sec": f.duration_sec.get(fmt),
                "launch_day": launch, "end_day": launch + life,
                "quality": float(quality), "causal_lift": float(lift),
                "fatigue_days": float(life * rng.uniform(0.8, 1.6)),
            })
            k += 1
            launch += int(f.launch_every_days * rng.uniform(0.8, 1.2))
    return pd.DataFrame(rows)


def creative_effect(lift, football, fatigue_days, age, event_t):
    """True causal effectiveness of a creative: lift x slow causal fatigue x football-event boost."""
    fat = np.maximum(0.5, np.exp(-age / (2.0 * fatigue_days)))
    return lift * fat * (1 + 0.4 * event_t * football)


def creative_effect_multiplier(cfg: SimConfig, channel: str, event_t: np.ndarray,
                               catalog: pd.DataFrame | None = None) -> np.ndarray:
    """Daily effectiveness multiplier of a channel (length T, mean 1) from its active creatives."""
    cat = build_catalog(cfg) if catalog is None else catalog
    cc = cat[cat["channel"] == channel]
    t = np.arange(cfg.n_days)[:, None]
    launch, end = cc["launch_day"].to_numpy()[None, :], cc["end_day"].to_numpy()[None, :]
    age = t - launch
    active = (age >= 0) & (t < end)
    w = cc["quality"].to_numpy()[None, :] * (1 + 0.5 * (age < 14)) * active
    tot = w.sum(1)
    share = np.where(tot[:, None] > 0, w / np.where(tot > 0, tot, 1)[:, None], 0.0)
    e = creative_effect(cc["causal_lift"].to_numpy()[None, :], (cc["theme"] == "futebol_ao_vivo").to_numpy()[None, :],
                        cc["fatigue_days"].to_numpy()[None, :], age, event_t[:, None])
    raw = np.where(tot > 0, (share * e).sum(1), 1.0)
    return raw / raw.mean()
