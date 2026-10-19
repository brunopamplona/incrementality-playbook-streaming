import numpy as np
import pytest

from growthlab import Intervention, default_config, run_simulation, true_channel_summary


@pytest.fixture(scope="module")
def cfg():
    return default_config(n_days=240)


@pytest.fixture(scope="module")
def df(cfg):
    return run_simulation(cfg)


def test_shape_and_nonnegative(cfg, df):
    assert len(df) == len(cfg.geos) * cfg.n_days
    assert (df.filter(like="spend_") >= 0).all().all()
    assert (df["new_subs"] >= 0).all()


def test_deterministic_given_seed(cfg, df):
    assert run_simulation(cfg).equals(df)
    assert not run_simulation(default_config(n_days=240, seed=7)).equals(df)


def test_plans_sum_to_total(df):
    cols = ["new_subs_premiere_futebol", "new_subs_telecine", "new_subs_claro_tv_bundle"]
    assert (df[cols].sum(axis=1) == df["new_subs"]).all()
    assert (df[cols] >= 0).all().all()


def test_all_plan_mixes_sum_to_one(cfg):
    assert sum(w for _, w in cfg.plan_mix) == pytest.approx(1.0)
    for ch in cfg.channels:
        assert sum(w for _, w in ch.plan_mix) == pytest.approx(1.0)


def test_budget_mix_adds_to_target(cfg):
    assert sum(c.daily_budget for c in cfg.channels) == pytest.approx(250_000)


def test_channel_plan_truth_adds_up(cfg, df):
    for c in cfg.channels:
        by_plan = sum(df[f"true_incr_{c.name}__{p}"].sum() for p, _ in cfg.plan_mix)
        assert by_plan == pytest.approx(df[f"true_incr_{c.name}"].sum())


def test_realized_plan_mix_reflects_channel_mixes(cfg, df):
    """Affiliates skew to the bundle, so the bundle share of incr subs must exceed the organic one."""
    from growthlab import true_channel_plan_summary
    cp = true_channel_plan_summary(df, cfg)
    assert cp.loc[("affiliates", "claro_tv_bundle"), "share_of_channel"] == pytest.approx(0.70)
    assert cp.loc[("meta_advantage", "telecine"), "share_of_channel"] > cp.loc[("tv", "telecine"), "share_of_channel"]


def test_new_mrr_matches_plan_prices(cfg, df):
    expected = sum(df[f"new_subs_{n}"] * p for n, p in cfg.plan_price)
    assert (df["new_mrr"] - expected).abs().max() < 1e-6


def test_poisson_mean_matches_true_lambda(cfg, df):
    lam = df["true_organic"] + sum(df[f"true_incr_{c.name}"] for c in cfg.channels)
    z = (df["new_subs"].sum() - lam.sum()) / np.sqrt(lam.sum())
    assert abs(z) < 4


def test_average_spend_matches_budget(cfg, df):
    days = cfg.n_days
    for spec in cfg.channels:
        daily = df[f"spend_{spec.name}"].sum() / days
        assert daily == pytest.approx(spec.daily_budget, rel=0.10)


def test_intervention_only_changes_target_window(cfg, df):
    iv = Intervention("youtube", ("SP", "RJ"), 100, 130, 0.0)
    d2 = run_simulation(cfg, [iv])
    win = (d2["geo"].isin(["SP", "RJ"])) & (d2["date"] >= d2["date"].min() + np.timedelta64(100, "D")) \
        & (d2["date"] < d2["date"].min() + np.timedelta64(130, "D"))
    assert (d2.loc[win, "spend_youtube"] == 0).all()
    assert d2.loc[~win, "spend_youtube"].equals(df.loc[~win, "spend_youtube"])
    assert d2["true_incr_youtube"].sum() < df["true_incr_youtube"].sum()


def test_truth_identity_and_saturation(cfg, df):
    t = true_channel_summary(df, cfg)
    for spec in cfg.channels:
        assert t.loc[spec.name, "true_incr_subs"] == pytest.approx(df[f"true_incr_{spec.name}"].sum())
    # concave response: next subscriber always costs more than the average one
    assert (t["true_marginal_cac"] > t["true_incr_cac"]).all()
