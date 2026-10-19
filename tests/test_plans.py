import pytest

from growthlab import channel_value_roi, default_config, plan_economics, plan_ltv_cac, run_simulation


def test_inputs_from_business():
    t = plan_economics(default_config())
    assert t.loc["premiere_futebol", "avg_lifetime_months"] == 12
    assert t.loc["telecine", "avg_lifetime_months"] == 18
    assert t.loc["claro_tv_bundle", "avg_lifetime_months"] == 18
    assert t.loc["telecine", "monthly_churn"] == pytest.approx(1 / 18)


def test_margins_within_business_range():
    t = plan_economics(default_config())
    assert t.loc[["premiere_futebol", "telecine", "claro_tv_bundle"], "margin"].between(0.30, 0.55).all()


def test_ltv_math():
    t = plan_economics(default_config())
    assert t.loc["claro_tv_bundle", "gross_ltv"] == pytest.approx(99.90 * 18)
    assert t.loc["telecine", "contrib_ltv"] == pytest.approx(29.90 * 18 * 0.45)
    assert (t["contrib_ltv_at_30pct"] <= t["contrib_ltv_at_55pct"]).all()


def test_plan_ltv_cac_and_channel_roi():
    cfg = default_config(n_days=364)
    df = run_simulation(cfg)
    ltv = plan_ltv_cac(df, cfg)
    assert (ltv["marginal_cac"] > ltv["cac"]).all()
    assert (ltv["ltv_cac"] > ltv["ltv_marginal_cac"]).all()
    roi = channel_value_roi(df, cfg)
    assert (roi["contrib_roi"] > 0).all()
