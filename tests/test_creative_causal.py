import numpy as np
import pytest

from growthlab import calibrated_config, run_simulation
from growthlab.creatives import build_catalog, creative_effect_multiplier
from growthlab.funnel import simulate_funnel
from growthlab.simulator import event_series_from_df


@pytest.fixture(scope="module")
def built():
    cfg = calibrated_config(80_000, n_days=364)
    df = run_simulation(cfg)
    return cfg, df, simulate_funnel(df, cfg)


def test_multiplier_has_mean_one_and_varies(built):
    cfg, df, _ = built
    ev = event_series_from_df(df, cfg)
    for c in cfg.channels:
        m = creative_effect_multiplier(cfg, c.name, ev)
        assert m.mean() == pytest.approx(1.0) and m.std() > 0.001


def test_creative_truth_adds_up_to_channel_truth(built):
    cfg, df, f = built
    cre = f["creative_truth_daily"].merge(f["creative_catalog"][["creative_id", "channel"]], on="creative_id")
    got = cre.groupby("channel")["true_incr_subs"].sum()
    for c in cfg.channels:
        assert got[c.name] == pytest.approx(df[f"true_incr_{c.name}"].sum(), rel=0.01)


def test_price_offer_creatives_get_clicks_but_less_causal_lift():
    cat = build_catalog(calibrated_config(80_000))
    oferta, rest = cat[cat.theme == "oferta_preco"], cat[cat.theme != "oferta_preco"]
    assert oferta.quality.mean() > rest.quality.mean()
    assert oferta.causal_lift.mean() < rest.causal_lift.mean()
    assert np.corrcoef(np.log(rest.quality), np.log(rest.causal_lift))[0, 1] == pytest.approx(0.3, abs=0.2)
