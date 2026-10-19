import pandas as pd
import pytest

from growthlab import calibrated_config, run_simulation
from growthlab.export import export_datasets


def test_export_shapes_and_consistency(tmp_path):
    cfg = calibrated_config(80_000, n_days=120)
    df = run_simulation(cfg)
    paths = export_datasets(df, cfg, tmp_path)
    camp = pd.read_csv(paths["campaign_daily"][0]); out = pd.read_csv(paths["outcomes_daily"][0])
    truth = pd.read_csv(paths["ground_truth"][0])
    assert len(camp) == len(df) * len(cfg.channels) and len(out) == len(df) == len(truth)
    assert {"impressions", "clicks", "video_views"} <= set(camp.columns)
    assert {"creative_daily", "creative_catalog", "creative_truth"} <= set(paths)
    assert camp["spend_brl"].sum() == pytest.approx(sum(df[f"spend_{c.name}"].sum() for c in cfg.channels), rel=1e-4)
    assert camp["platform_reported_subs"].sum() < out["new_subs"].sum()
    assert not any(c.startswith("true_") for c in camp.columns) and not any(c.startswith("true_") for c in out.columns)
