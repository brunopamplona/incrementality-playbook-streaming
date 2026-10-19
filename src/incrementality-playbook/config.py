"""Simulation configuration: geos, channels, demand and plan parameters."""
from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

# Approximate 2022 population (millions) of the 27 Brazilian UFs.
BR_UF_POP_M = {
    "SP": 44.4, "MG": 20.5, "RJ": 16.0, "BA": 14.1, "PR": 11.4, "RS": 10.9,
    "PE": 9.0, "CE": 8.8, "PA": 8.1, "SC": 7.6, "GO": 7.0, "MA": 6.8,
    "PB": 4.0, "AM": 3.9, "ES": 3.8, "MT": 3.6, "RN": 3.3, "PI": 3.3,
    "AL": 3.1, "DF": 2.8, "MS": 2.8, "SE": 2.2, "RO": 1.6, "TO": 1.5,
    "AC": 0.8, "AP": 0.8, "RR": 0.6,
}


@dataclass(frozen=True)
class ChannelSpec:
    """One marketing channel's true data-generating process.

    Incremental subs per day in a geo =
        pop_k * beta * Hill(Adstock(spend / pop_k; decay); k, s)
    where pop_k is population in thousands and k = hill_k_mult * (avg spend per 1k pop).
    """
    name: str
    daily_budget: float          # national average daily spend (R$)
    beta: float                  # max incremental subs / 1k pop / day at saturation
    decay: float                 # adstock carryover
    hill_k_mult: float           # half-saturation as a multiple of average spend
    hill_s: float = 1.3          # Hill shape
    national_buy: bool = False   # same flighting in every geo (e.g. TV)
    flight_on_prob: float = 0.65 # P(a given geo-week is "on air")
    flight_depth: float = 0.8    # spend drop when "off" (0 = flat, 1 = fully dark)
    geo_variation: float = 0.3   # lognormal sd of geo-week spend noise
    event_sensitivity: float = 0.0  # spend uplift during demand events (confounding!)
    demand_driven: bool = False  # spend chases organic demand (e.g. brand search)
    # ASSUMPTION: share of this channel's incremental subs landing in each plan.
    # This is a *hypothesis the lab then tries to recover*, not an observed fact.
    plan_mix: tuple = (("premiere_futebol", 0.45), ("telecine", 0.25), ("claro_tv_bundle", 0.30))
    platform: str = "other"      # ad platform that sells/reports the channel ("google", "other")


@dataclass(frozen=True)
class SimConfig:
    geo_pop_m: dict = field(default_factory=lambda: dict(BR_UF_POP_M))
    n_days: int = 3 * 364
    start_date: str = "2023-01-02"
    seed: int = 42
    base_rate: float = 0.030     # organic new subs / 1k pop / day
    trend: float = 0.15          # total organic growth over the horizon
    n_events: int = 12           # demand events: sports season starts, launches, Black Friday
    geo_shock_sd: float = 0.04   # AR(1) idiosyncratic demand shocks
    channels: tuple = ()
    # Plans being measured. Prices: public list prices, Oct 2026 (see docs/ASSUMPTIONS.md).
    plan_price: tuple = (("premiere_futebol", 59.90), ("telecine", 29.90), ("claro_tv_bundle", 99.90))
    # Average subscriber lifetime in months (given by the business). Monthly churn = 1 / lifetime.
    plan_avg_lifetime_months: tuple = (("premiere_futebol", 12), ("telecine", 18), ("claro_tv_bundle", 18))
    # Contribution margin per plan, within the business range of 30%-55%.
    # ASSUMPTION by cost-structure reasoning, not sourced: replace with finance figures.
    plan_contribution_margin: tuple = (("premiere_futebol", 0.38), ("telecine", 0.45), ("claro_tv_bundle", 0.33))
    # Plan mix of ORGANIC new subs (no marketing). ASSUMPTION.
    plan_mix: tuple = (("premiere_futebol", 0.45), ("telecine", 0.25), ("claro_tv_bundle", 0.30))

    @property
    def geos(self) -> list[str]:
        return list(self.geo_pop_m)

    @property
    def pop_k(self) -> np.ndarray:
        return np.array([self.geo_pop_m[g] * 1000.0 for g in self.geos])


# Budget shares, as shares of the TOTAL media budget (given by the business):
#   Google Ads (campaigns other than YouTube) 30%, YouTube 20%, Meta 25%, rest split equally
#   among the remaining channels (TV, affiliates: 12.5% each).
# The 30% Google Ads block is split across its campaign types using the business's inner mix
# (brand 10 : generic 30 : app 20 : PMax 20), renormalised once YouTube is taken out of it.
GOOGLE_ADS_INNER_MIX = (("search_brand", 10), ("search_generic", 30), ("app_campaigns", 20), ("pmax", 20))
GOOGLE_ADS_SHARE = 0.30
YOUTUBE_SHARE = 0.20
META_SHARE = 0.25
# Meta Ads budget split across campaign types: ASSUMED CURRENT split (reference point that defines each
# channel's saturation). No streaming-specific public benchmark exists. Types:
#   Advantage+ conversion campaigns (app/sales, optimised for the subscription event, broad audience)
#   Reels/Stories video reach (trailers, football highlights)
#   Remarketing / win-back (site, app and lapsed-subscriber audiences)
# The recommended split comes from growthlab.optimize.optimal_split, not from this constant.
META_SPLIT = (("meta_advantage", 0.50), ("meta_reels_video", 0.30), ("meta_remarketing", 0.20))
TOTAL_DAILY_BUDGET = 250_000


def budget_shares() -> dict:
    """Share of the total media budget per channel (sums to 1)."""
    inner = sum(w for _, w in GOOGLE_ADS_INNER_MIX)
    shares = {n: GOOGLE_ADS_SHARE * w / inner for n, w in GOOGLE_ADS_INNER_MIX}
    shares["youtube"] = YOUTUBE_SHARE
    shares.update({n: META_SHARE * w for n, w in META_SPLIT})
    left = 1 - sum(shares.values())
    shares["tv"] = shares["affiliates"] = left / 2
    return shares


def default_config(**overrides) -> SimConfig:
    """Ten channels: five Google platform campaigns (YouTube included), three Meta campaign types, TV, affiliates.

    Betas here are rough starting values; `calibrated_config` retunes them to target CACs.
    """
    sh = budget_shares()
    b = {n: TOTAL_DAILY_BUDGET * w for n, w in sh.items()}

    channels = (
        # Offline, national buy, slow carryover, big event-driven bursts.
        ChannelSpec("tv", b["tv"], beta=0.0060, decay=0.85, hill_k_mult=1.0,
                    national_buy=True, flight_on_prob=0.6, flight_depth=0.9,
                    geo_variation=0.03, event_sensitivity=1.2,
                    plan_mix=(("premiere_futebol", 0.45), ("telecine", 0.10), ("claro_tv_bundle", 0.45))),
        # --- Meta Ads ---
        # Advantage+ conversion campaigns: broad prospecting optimised for the subscription event.
        ChannelSpec("meta_advantage", b["meta_advantage"], beta=0.0070, decay=0.35, hill_k_mult=1.3,
                    geo_variation=0.35, event_sensitivity=0.5, platform="meta",
                    plan_mix=(("premiere_futebol", 0.40), ("telecine", 0.35), ("claro_tv_bundle", 0.25))),
        # Reels / Stories video reach: cheap impressions, slower and more diffuse effect.
        ChannelSpec("meta_reels_video", b["meta_reels_video"], beta=0.0050, decay=0.60, hill_k_mult=1.0,
                    geo_variation=0.35, event_sensitivity=0.7, platform="meta",
                    plan_mix=(("premiere_futebol", 0.40), ("telecine", 0.35), ("claro_tv_bundle", 0.25))),
        # Remarketing / win-back: audience size follows site and app demand; high reported conversion,
        # low incrementality (people were already coming back).
        ChannelSpec("meta_remarketing", b["meta_remarketing"], beta=0.0020, decay=0.20, hill_k_mult=0.6,
                    geo_variation=0.15, demand_driven=True, platform="meta",
                    plan_mix=(("premiere_futebol", 0.40), ("telecine", 0.25), ("claro_tv_bundle", 0.35))),
        # Affiliates / carrier & retail partnerships: skew to the bundle.
        ChannelSpec("affiliates", b["affiliates"], beta=0.0040, decay=0.30, hill_k_mult=0.7,
                    geo_variation=0.30, event_sensitivity=0.3,
                    plan_mix=(("premiere_futebol", 0.15), ("telecine", 0.15), ("claro_tv_bundle", 0.70))),
        # --- Google Ads ---
        # Brand search: spend tracks demand; converts people who were already coming.
        ChannelSpec("search_brand", b["search_brand"], beta=0.0010, decay=0.20, hill_k_mult=0.5,
                    geo_variation=0.10, demand_driven=True, platform="google",
                    plan_mix=(("premiere_futebol", 0.40), ("telecine", 0.25), ("claro_tv_bundle", 0.35))),
        # Generic search ("assistir futebol ao vivo"): captures in-market intent, spikes with events,
        # limited by search volume (saturates early).
        ChannelSpec("search_generic", b["search_generic"], beta=0.0050, decay=0.20, hill_k_mult=0.7,
                    flight_on_prob=0.80, flight_depth=0.5, geo_variation=0.25, event_sensitivity=1.0,
                    platform="google",
                    plan_mix=(("premiere_futebol", 0.50), ("telecine", 0.20), ("claro_tv_bundle", 0.30))),
        # YouTube video reach (football highlights, trailers), fairly saturated.
        ChannelSpec("youtube", b["youtube"], beta=0.0050, decay=0.70, hill_k_mult=0.8,
                    geo_variation=0.30, event_sensitivity=0.8, platform="google",
                    plan_mix=(("premiere_futebol", 0.55), ("telecine", 0.15), ("claro_tv_bundle", 0.30))),
        # App campaigns (installs -> subscriptions), performance-optimised.
        ChannelSpec("app_campaigns", b["app_campaigns"], beta=0.0040, decay=0.30, hill_k_mult=1.0,
                    flight_on_prob=0.75, flight_depth=0.6, geo_variation=0.30, event_sensitivity=0.6,
                    platform="google",
                    plan_mix=(("premiere_futebol", 0.40), ("telecine", 0.30), ("claro_tv_bundle", 0.30))),
        # Performance Max: automated mix of search/YouTube/display; partly harvests brand demand,
        # so its true incrementality is low relative to what it reports.
        ChannelSpec("pmax", b["pmax"], beta=0.0030, decay=0.35, hill_k_mult=0.9,
                    flight_on_prob=0.80, flight_depth=0.5, geo_variation=0.25, event_sensitivity=0.6,
                    platform="google",
                    plan_mix=(("premiere_futebol", 0.40), ("telecine", 0.25), ("claro_tv_bundle", 0.35))),
    )
    cfg = SimConfig(channels=channels)
    return replace(cfg, **overrides) if overrides else cfg
