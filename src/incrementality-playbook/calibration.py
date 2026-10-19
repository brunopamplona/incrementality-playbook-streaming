"""Calibrate the simulator: volume, organic/paid split, CAC levels and budget."""
from __future__ import annotations

from dataclasses import replace

from .config import SimConfig, default_config

DAYS_PER_MONTH = 365 / 12

# Incremental CAC (R$) per channel at the structural budget. ASSUMPTIONS: relative levels are
# stylised, pending geo-experiments; the absolute level is then set by the real budget.
TARGET_INCREMENTAL_CAC = {
    "tv": 136, "affiliates": 81,
    "meta_advantage": 110, "meta_reels_video": 150, "meta_remarketing": 190,
    "search_brand": 176, "search_generic": 100, "youtube": 95, "app_campaigns": 125, "pmax": 150,
}


def scale_config(cfg: SimConfig, factor: float, paid_factor: float | None = None) -> SimConfig:
    """Scale organic demand by `factor` and paid media (betas and budgets) by `paid_factor`.

    Hill half-saturation points are defined relative to each channel's budget, so scaling beta and
    budget together scales paid subs and spend equally and leaves every CAC, marginal CAC and
    saturation level unchanged.
    """
    pf = factor if paid_factor is None else paid_factor
    channels = tuple(replace(c, beta=c.beta * pf, daily_budget=c.daily_budget * pf) for c in cfg.channels)
    return replace(cfg, base_rate=cfg.base_rate * factor, channels=channels)


def monthly_budget(cfg: SimConfig) -> float:
    """Configured media budget per month (R$)."""
    return sum(c.daily_budget for c in cfg.channels) * DAYS_PER_MONTH


def with_monthly_budget(cfg: SimConfig, target: float) -> SimConfig:
    """Same volume of subscribers, different media budget, i.e. a different CAC level.

    Budgets scale by g = target / current while betas stay fixed. Saturation levels and
    incremental subs are unchanged; every CAC and marginal CAC scales by exactly g.
    """
    g = target / monthly_budget(cfg)
    channels = tuple(replace(c, daily_budget=c.daily_budget * g) for c in cfg.channels)
    return replace(cfg, channels=channels)


def set_incremental_cac(cfg: SimConfig, targets: dict | None = None) -> SimConfig:
    """Retune each channel's beta so its true incremental CAC equals the target.

    Incremental subs are exactly linear in beta, so one pass is exact for the simulated spend path.
    """
    from .simulator import run_simulation
    targets = targets or TARGET_INCREMENTAL_CAC
    df = run_simulation(cfg)
    channels = []
    for c in cfg.channels:
        cac_now = df[f"spend_{c.name}"].sum() / df[f"true_incr_{c.name}"].sum()
        channels.append(replace(c, beta=c.beta * cac_now / targets[c.name]))
    return replace(cfg, channels=tuple(channels))


def calibrated_config(target_monthly_subs: float = 80_000, monthly_budget_brl: float | None = None,
                      incremental_share: float = 0.23, **overrides) -> SimConfig:
    """Config matching the business: volume, organic/paid split, CAC structure and (optionally) budget.

    1. Retune betas to the target incremental CACs.
    2. Scale organic demand and paid media separately so that total new subs = `target_monthly_subs`
       and marketing-incremental subs = `incremental_share` of them (default 23%: roughly half of the
       ~49% non-organic share seen in a streaming-app install benchmark, see docs/ASSUMPTIONS.md).
    3. If `monthly_budget_brl` is given, set the media budget to it (volume unchanged, CAC rescaled).
    """
    from .simulator import run_simulation
    cfg = set_incremental_cac(default_config(**overrides))
    df = run_simulation(cfg)
    per_month = DAYS_PER_MONTH / cfg.n_days
    organic = df["true_organic"].sum() * per_month
    paid = sum(df[f"true_incr_{c.name}"].sum() for c in cfg.channels) * per_month
    f_o = target_monthly_subs * (1 - incremental_share) / organic
    f_p = target_monthly_subs * incremental_share / paid
    cfg = scale_config(cfg, f_o, f_p)
    return with_monthly_budget(cfg, monthly_budget_brl) if monthly_budget_brl else cfg
