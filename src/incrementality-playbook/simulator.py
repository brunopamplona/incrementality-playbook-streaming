"""Synthetic streaming-platform simulator with known causal ground truth.

Data-generating process (per geo g, day t):

    organic_{g,t}  = pop_k * base_rate * trend * season * dow * (1 + event_t) * geo_shock * geo_propensity
    incr_{c,g,t}   = pop_k * beta_c * Hill(Adstock(spend_{c,g,t} / pop_k))
    new_subs       ~ Poisson(lambda)           then split across plans

Confounding is built in on purpose:
  * demand events raise organic demand AND channel spend (TV/YouTube/Meta...)
  * brand-search spend chases organic demand while barely causing any of it
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import ChannelSpec, SimConfig
from .creatives import build_catalog, creative_effect_multiplier
from .transforms import geometric_adstock, hill


@dataclass(frozen=True)
class Intervention:
    """Override a channel's spend in some geos/days (for geo-experiments).

    multiplier=0.0 -> go dark; 1.5 -> +50% spend. Days are 0-indexed, end exclusive.
    """
    channel: str
    geos: tuple
    start_day: int
    end_day: int
    multiplier: float


def channel_response(spend: np.ndarray, pop_k: np.ndarray, spec: ChannelSpec,
                     total_pop_k: float, multiplier: np.ndarray | None = None) -> np.ndarray:
    """Expected incremental subs, shape (G, T), from a (G, T) spend matrix.

    `multiplier` (length T, mean 1) is the daily creative effectiveness of the channel.
    """
    x = spend / pop_k[:, None]
    a = geometric_adstock(x, spec.decay)
    k = spec.hill_k_mult * spec.daily_budget / total_pop_k
    out = pop_k[:, None] * spec.beta * hill(a, k, spec.hill_s)
    return out if multiplier is None else out * multiplier[None, :]


def creative_multipliers(cfg: SimConfig, event_t: np.ndarray) -> dict:
    """Creative effectiveness multiplier per channel (deterministic given cfg)."""
    cat = build_catalog(cfg)
    return {c.name: creative_effect_multiplier(cfg, c.name, event_t, cat) for c in cfg.channels}


def event_series_from_df(df: pd.DataFrame, cfg: SimConfig) -> np.ndarray:
    return df[df["geo"] == cfg.geos[0]].sort_values("date")["event_intensity"].to_numpy()


def _event_series(cfg: SimConfig, rng: np.random.Generator) -> np.ndarray:
    T = cfg.n_days
    e = np.zeros(T)
    starts = np.sort(rng.integers(10, T - 20, cfg.n_events))
    for s in starts:
        lift, tau = rng.uniform(0.25, 0.70), rng.uniform(4, 10)
        t = np.arange(T - s)
        e[s:] += lift * np.exp(-t / tau)
    return e


def _organic(cfg: SimConfig, rng: np.random.Generator, event_t: np.ndarray):
    G, T = len(cfg.geos), cfg.n_days
    pop_k = cfg.pop_k
    dates = pd.date_range(cfg.start_date, periods=T, freq="D")

    trend = 1 + cfg.trend * np.arange(T) / T
    season = 1 + 0.10 * np.sin(2 * np.pi * (dates.dayofyear.to_numpy() - 30) / 365)
    dow_w = np.array([1.00, 0.95, 0.95, 0.97, 1.05, 1.20, 1.15])
    dow = dow_w[dates.dayofweek.to_numpy()] / dow_w.mean()

    shock = np.zeros((G, T))
    for t in range(1, T):
        shock[:, t] = 0.9 * shock[:, t - 1] + rng.normal(0, cfg.geo_shock_sd, G)
    propensity = rng.lognormal(0, 0.15, G)

    national = trend * season * dow * (1 + event_t)
    organic = (pop_k * cfg.base_rate * propensity)[:, None] * national[None, :] * np.exp(shock)
    demand_index = national[None, :] * np.exp(shock)
    return dates, organic, demand_index


def _make_spend(spec: ChannelSpec, cfg: SimConfig, rng: np.random.Generator,
                demand_index: np.ndarray, event_t: np.ndarray) -> np.ndarray:
    G, T = demand_index.shape
    weeks = np.arange(T) // 7
    W = weeks.max() + 1
    pop_share = cfg.pop_k / cfg.pop_k.sum()

    if spec.demand_driven:
        raw = demand_index * rng.lognormal(0, spec.geo_variation, (G, T))
    else:
        n_draws = 1 if spec.national_buy else G
        on = rng.random((n_draws, W)) < spec.flight_on_prob
        level = np.broadcast_to(np.where(on, 1.0, 1.0 - spec.flight_depth), (G, W))
        geo_noise = rng.lognormal(0, spec.geo_variation, (G, W))
        weekly = (level * geo_noise)[:, weeks]
        raw = weekly * (1 + spec.event_sensitivity * event_t)[None, :]
        raw = raw * rng.lognormal(0, 0.05, (G, T))
    raw = raw / raw.mean()
    return spec.daily_budget * pop_share[:, None] * raw


def run_simulation(cfg: SimConfig, interventions: tuple | list = ()) -> pd.DataFrame:
    """Simulate the panel. Returns a long DataFrame sorted by (geo, date).

    Columns: date, geo, population, event_intensity, new_subs[, by plan],
    spend_<channel>, plus ground-truth columns true_organic and true_incr_<channel>.
    """
    rng = np.random.default_rng(cfg.seed)
    G, T = len(cfg.geos), cfg.n_days
    pop_k, total_pop_k = cfg.pop_k, cfg.pop_k.sum()

    event_t = _event_series(cfg, rng)
    dates, organic, demand_index = _organic(cfg, rng, event_t)

    spend = {s.name: _make_spend(s, cfg, rng, demand_index, event_t) for s in cfg.channels}

    geo_idx = {g: i for i, g in enumerate(cfg.geos)}
    for iv in interventions:
        rows = [geo_idx[g] for g in iv.geos]
        spend[iv.channel][np.ix_(rows, range(iv.start_day, iv.end_day))] *= iv.multiplier

    mult = creative_multipliers(cfg, event_t)
    incr = {s.name: channel_response(spend[s.name], pop_k, s, total_pop_k, mult[s.name]) for s in cfg.channels}
    # Plan-level demand: organic and each channel land in plans with their own mix.
    org_mix = dict(cfg.plan_mix)
    chan_mix = {sp.name: dict(sp.plan_mix) for sp in cfg.channels}
    plan_names = list(org_mix)
    incr_plan = {(c, pl): incr[c] * chan_mix[c][pl] for c in incr for pl in plan_names}
    lam_plan = {pl: organic * org_mix[pl] + sum(incr_plan[(c, pl)] for c in incr) for pl in plan_names}
    plans = {pl: rng.poisson(lam_plan[pl]) for pl in plan_names}
    new_subs = sum(plans.values())
    price = dict(cfg.plan_price)
    new_mrr = sum(plans[n] * price[n] for n in plans)

    df = pd.DataFrame({
        "date": np.tile(dates, G),
        "geo": np.repeat(cfg.geos, T),
        "population": np.repeat(pop_k * 1000, T),
        "event_intensity": np.tile(event_t, G),
        "new_subs": new_subs.ravel(),
        **{f"new_subs_{p}": v.ravel() for p, v in plans.items()},
        "new_mrr": new_mrr.ravel(),
        **{f"spend_{n}": v.ravel() for n, v in spend.items()},
        "true_organic": organic.ravel(),
        **{f"true_incr_{n}": v.ravel() for n, v in incr.items()},
        **{f"true_incr_{c}__{pl}": v.ravel() for (c, pl), v in incr_plan.items()},
    })
    df.attrs["config_seed"] = cfg.seed
    return df
