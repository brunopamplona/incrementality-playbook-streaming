"""Stages 1-2: simulate, then show how far naive attribution is from the truth."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from growthlab import calibrated_config, compare_to_truth, run_simulation

ROOT = Path(__file__).resolve().parents[1]
cfg = calibrated_config(80_000, monthly_budget_brl=3_250_000)
df = run_simulation(cfg)
(ROOT / "data").mkdir(exist_ok=True)

tbl = compare_to_truth(df, cfg)
pd.set_option("display.width", 160, "display.float_format", "{:,.1f}".format)
print(f"Panel: {df['geo'].nunique()} geos x {df['date'].nunique()} days, "
      f"{df['new_subs'].sum():,} new subs, R$ {tbl['spend'].sum()/1e6:,.0f}M media spend")
print(f"Marketing-driven share of subs: {tbl['share_of_all_subs'].sum():.0%}\n")
print(tbl[["spend", "true_incr_subs", "true_incr_cac", "true_marginal_cac",
           "lastclick_cac", "regression_cac"]].to_string())
print("\nBias (estimated CAC / true incremental CAC; 1.0 = correct):")
print(tbl[["lastclick_cac_bias", "regression_cac_bias"]].round(2).to_string())

# Plot: incremental subs, truth vs naive methods
img = ROOT / "docs" / "img"
img.mkdir(parents=True, exist_ok=True)
fig, ax = plt.subplots(figsize=(8, 4.2))
x, w = np.arange(len(tbl)), 0.27
ax.bar(x - w, tbl["true_incr_subs"] / 1e3, w, label="Truth (counterfactual)", color="#1f4e79")
ax.bar(x, tbl["lastclick_subs"] / 1e3, w, label="Last-click", color="#e08a1e")
ax.bar(x + w, tbl["regression_subs"].clip(lower=0) / 1e3, w, label="Naive regression", color="#9aa5b1")
ax.set_xticks(x, tbl.index)
ax.set_ylabel("Attributed subscribers (thousands)")
ax.set_title("Who really drove subscribers? Truth vs naive attribution")
ax.legend(frameon=False)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(img / "stage2_truth_vs_naive.png", dpi=150)
print(f"\nSaved {img / 'stage2_truth_vs_naive.png'}")
