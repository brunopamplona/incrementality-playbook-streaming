import pytest

from growthlab import calibrated_config, optimal_split, run_simulation


def test_optimal_split_conserves_budget_and_improves_value():
    cfg = calibrated_config(80_000, n_days=364)
    df = run_simulation(cfg)
    meta = [c.name for c in cfg.channels if c.platform == "meta"]
    out = optimal_split(df, cfg, meta)
    assert out["current_share"].sum() == pytest.approx(1.0)
    assert out["optimal_share"].sum() == pytest.approx(1.0)
    assert out.attrs["value_gain_pct"] >= -1e-9
    assert (out["spend_multiplier"].between(0.2, 3.0)).all()
