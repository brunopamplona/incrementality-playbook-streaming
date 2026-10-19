import numpy as np
import pandas as pd
import pytest

from growthlab import calibrated_config, run_simulation
from growthlab.funnel import FUNNEL, simulate_funnel


@pytest.fixture(scope="module")
def built():
    cfg = calibrated_config(80_000, n_days=182)
    df = run_simulation(cfg)
    return cfg, df, simulate_funnel(df, cfg)


def test_creative_totals_reconcile_with_campaign(built):
    cfg, df, f = built
    camp = f["campaign_daily"].groupby("channel")[["impressions", "clicks", "video_views"]].sum(min_count=1)
    cre = f["creative_daily"].groupby("channel")[["impressions", "clicks", "video_views"]].sum(min_count=1)
    pd.testing.assert_frame_equal(camp.sort_index(), cre.sort_index(), check_dtype=False)
    s1 = f["campaign_daily"].groupby("channel")["spend_brl"].sum()
    s2 = f["creative_daily"].groupby("channel")["spend_brl"].sum()
    assert ((s1 - s2).abs() / s1 < 1e-3).all()


def test_every_channel_day_has_an_active_creative(built):
    cfg, df, f = built
    n = f["creative_daily"].groupby(["channel", "date"]).size()
    assert len(n) == len(cfg.channels) * cfg.n_days and (n >= 1).all()


def test_clicks_and_impressions_are_sane(built):
    cfg, df, f = built
    cre = f["creative_daily"]
    ok = cre["clicks"].dropna() <= cre.loc[cre["clicks"].notna(), "impressions"]
    assert ok.all() and (cre["impressions"] >= 0).all()
    assert f["campaign_daily"].query("channel == 'tv'")["clicks"].isna().all()


def test_aggregate_cpm_ctr_near_assumptions(built):
    cfg, df, f = built
    g = f["campaign_daily"].groupby("channel")[["spend_brl", "impressions", "clicks"]].sum(min_count=1)
    cpm = g["spend_brl"] / g["impressions"] * 1000
    ctr = g["clicks"] / g["impressions"]
    for ch, spec in FUNNEL.items():
        assert 0.8 * spec.cpm < cpm[ch] < 1.5 * spec.cpm       # inflation and event premium push it up
        if spec.ctr:
            assert ctr[ch] == pytest.approx(spec.ctr, rel=0.12)


def test_funnel_does_not_change_causal_truth(built):
    cfg, df, _ = built
    again = run_simulation(cfg)
    assert df["new_subs"].equals(again["new_subs"])
