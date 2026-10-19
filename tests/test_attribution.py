import pytest

from growthlab import compare_to_truth, default_config, run_simulation
from growthlab.attribution import last_click_attribution


@pytest.fixture(scope="module")
def cfg():
    return default_config(n_days=364)


@pytest.fixture(scope="module")
def df(cfg):
    return run_simulation(cfg)


def test_last_click_credit_never_exceeds_total_subs(cfg, df):
    assert last_click_attribution(df, cfg)["lastclick_subs"].sum() < df["new_subs"].sum()


def test_last_click_massively_flatters_brand_search(cfg, df):
    t = compare_to_truth(df, cfg)
    assert t.loc["search_brand", "lastclick_cac_bias"] < 0.2   # claims >5x better than reality


def test_naive_methods_are_materially_wrong_somewhere(cfg, df):
    t = compare_to_truth(df, cfg)
    for col in ["lastclick_cac_bias", "regression_cac_bias"]:
        assert ((t[col] > 1.5) | (t[col] < 0.67)).any()
