import pytest

from growthlab import (calibrated_config, monthly_budget, with_monthly_budget, default_config, last_click_attribution, run_simulation,
                       scale_config, true_channel_summary)
from growthlab.calibration import DAYS_PER_MONTH


def test_calibrated_volume_hits_target():
    cfg = calibrated_config(80_000, n_days=364)
    df = run_simulation(cfg)
    monthly = df["new_subs"].sum() / cfg.n_days * DAYS_PER_MONTH
    assert monthly == pytest.approx(80_000, rel=0.02)


def test_scaling_preserves_unit_economics():
    base = default_config(n_days=364)
    small = scale_config(base, 0.25)
    t0 = true_channel_summary(run_simulation(base), base)
    t1 = true_channel_summary(run_simulation(small), small)
    assert t1["spend"].sum() == pytest.approx(0.25 * t0["spend"].sum(), rel=1e-6)
    assert (t1["true_incr_cac"] / t0["true_incr_cac"]).between(0.99, 1.01).all()
    assert t1["share_of_all_subs"].sum() == pytest.approx(t0["share_of_all_subs"].sum(), rel=0.02)


def test_set_incremental_cac_hits_targets():
    from growthlab.calibration import TARGET_INCREMENTAL_CAC, set_incremental_cac
    cfg = set_incremental_cac(default_config(n_days=364))
    t = true_channel_summary(run_simulation(cfg), cfg)
    for name, target in TARGET_INCREMENTAL_CAC.items():
        assert t.loc[name, "true_incr_cac"] == pytest.approx(target, rel=0.01)


def test_calibrated_incremental_share_and_budget_anchor():
    cfg = calibrated_config(80_000, incremental_share=0.23, n_days=364)
    df = run_simulation(cfg)
    inc = sum(df[f"true_incr_{c.name}"].sum() for c in cfg.channels)
    assert inc / (inc + df["true_organic"].sum()) == pytest.approx(0.23, abs=0.01)
    cfg2 = calibrated_config(80_000, monthly_budget_brl=3_250_000, n_days=364)
    assert monthly_budget(cfg2) == pytest.approx(3_250_000)


def test_budget_shares_match_business():
    from growthlab.config import budget_shares
    sh = budget_shares()
    assert sum(sh.values()) == pytest.approx(1.0)
    assert sh["youtube"] == pytest.approx(0.20)
    assert sh["meta_advantage"] + sh["meta_reels_video"] + sh["meta_remarketing"] == pytest.approx(0.25)
    assert sh["meta_advantage"] / 0.25 == pytest.approx(0.50)
    assert sh["tv"] == pytest.approx(0.125) and sh["affiliates"] == pytest.approx(0.125)
    google_ads = sh["search_brand"] + sh["search_generic"] + sh["app_campaigns"] + sh["pmax"]
    assert google_ads == pytest.approx(0.30)
    assert sh["search_generic"] / google_ads == pytest.approx(30 / 80)  # inner mix renormalised


def test_default_config_budgets_follow_shares():
    from growthlab.config import budget_shares
    cfg = default_config()
    for c in cfg.channels:
        assert c.daily_budget == pytest.approx(250_000 * budget_shares()[c.name])


def test_last_click_credits_about_half_of_subs():
    cfg = default_config(n_days=364)
    df = run_simulation(cfg)
    share = last_click_attribution(df, cfg)["lastclick_subs"].sum() / df["new_subs"].sum()
    assert 0.45 < share < 0.58


def test_budget_rescaling_keeps_volume_and_scales_cac():
    base = default_config(n_days=364)
    g = 1.6
    big = with_monthly_budget(base, g * monthly_budget(base))
    t0 = true_channel_summary(run_simulation(base), base)
    t1 = true_channel_summary(run_simulation(big), big)
    assert t1["true_incr_subs"].sum() == pytest.approx(t0["true_incr_subs"].sum(), rel=0.03)
    assert (t1["true_incr_cac"] / t0["true_incr_cac"]).between(0.97 * g, 1.03 * g).all()
    assert (t1["true_marginal_cac"] / t0["true_marginal_cac"]).between(0.97 * g, 1.03 * g).all()
