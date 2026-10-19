"""Which CAC does a real monthly budget imply, for a known volume of 80k new subs/month?"""
import pandas as pd

from growthlab import calibrated_config, plan_ltv_cac, run_simulation, true_channel_summary
from growthlab.calibration import DAYS_PER_MONTH

pd.set_option("display.width", 200, "display.float_format", "{:,.1f}".format)
cac, plans = {}, {}
for budget in (2_500_000, 3_250_000, 4_000_000):
    cfg = calibrated_config(80_000, monthly_budget_brl=budget)
    df = run_simulation(cfg)
    t = true_channel_summary(df, cfg)
    spend_m = t["spend"].sum() / cfg.n_days * DAYS_PER_MONTH
    incr_m = t["true_incr_subs"].sum() / cfg.n_days * DAYS_PER_MONTH
    cac[f"R$ {budget/1e6:.2f}M"] = t["true_incr_cac"]
    p = plan_ltv_cac(df, cfg)[["cac", "marginal_cac", "ltv_cac", "ltv_marginal_cac", "payback_months"]]
    plans[f"R$ {budget/1e6:.2f}M"] = p
    print(f"Budget R$ {budget/1e6:.2f}M -> realised spend R$ {spend_m/1e6:.2f}M/month, "
          f"incremental subs {incr_m:,.0f}/month, blended incremental CAC R$ {spend_m/incr_m:,.0f}")
print("\nIncremental CAC by channel (R$):"); print(pd.DataFrame(cac))
for k, v in plans.items():
    print(f"\nPlan-level economics at budget {k}:"); print(v)

# Google Ads: what the platform dashboard (last-click proxy) reports vs the truth, mid budget
from growthlab import channel_value_roi, platform_summary
cfg = calibrated_config(80_000, monthly_budget_brl=3_250_000)
df = run_simulation(cfg)
print("\nGoogle Ads at R$ 3.25M/month (dashboard proxy vs truth):")
print(platform_summary(df, cfg, "google"))
roi = channel_value_roi(df, cfg)
print("\nContribution value per R$ 1 (average / marginal):")
print(roi[["contrib_roi", "marginal_contrib_roi"]].sort_values("marginal_contrib_roi", ascending=False))
