"""Media response transforms: adstock (carryover) and Hill saturation."""
from __future__ import annotations

import numpy as np


def geometric_adstock(x: np.ndarray, decay: float) -> np.ndarray:
    """Normalized geometric adstock along the last axis.

    a_t = (1 - decay) * x_t + decay * a_{t-1}

    Normalization keeps the steady-state level equal to the input level, so
    `decay` changes *timing* of the effect, not its total scale.
    """
    if not 0 <= decay < 1:
        raise ValueError("decay must be in [0, 1)")
    x = np.asarray(x, dtype=float)
    out = np.empty_like(x)
    carry = np.zeros(x.shape[:-1])
    for t in range(x.shape[-1]):
        carry = (1 - decay) * x[..., t] + decay * carry
        out[..., t] = carry
    return out


def hill(x: np.ndarray, k: float, s: float) -> np.ndarray:
    """Hill saturation in [0, 1). k = half-saturation point, s = shape."""
    x = np.maximum(np.asarray(x, dtype=float), 0.0)
    xs = x**s
    return xs / (xs + k**s)
