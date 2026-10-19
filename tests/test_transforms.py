import numpy as np
import pytest

from growthlab.transforms import geometric_adstock, hill


def test_adstock_steady_state_equals_input():
    out = geometric_adstock(np.full((2, 500), 3.0), decay=0.8)
    assert np.allclose(out[:, -1], 3.0, atol=1e-6)


def test_adstock_carries_over_after_pulse():
    x = np.zeros((1, 10)); x[0, 0] = 1.0
    out = geometric_adstock(x, decay=0.5)[0]
    assert out[0] == pytest.approx(0.5) and out[1] == pytest.approx(0.25)


def test_adstock_rejects_bad_decay():
    with pytest.raises(ValueError):
        geometric_adstock(np.ones((1, 3)), decay=1.0)


def test_hill_half_saturation_and_monotonic():
    assert hill(2.0, k=2.0, s=1.5) == pytest.approx(0.5)
    xs = np.linspace(0, 10, 50)
    assert np.all(np.diff(hill(xs, 2.0, 1.5)) > 0) and hill(1e9, 2.0, 1.5) < 1.0
