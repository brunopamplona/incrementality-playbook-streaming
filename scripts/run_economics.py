"""Channel x plan truth and plan-level LTV/CAC."""
import pandas as pd

from growthlab import (calibrated_config, channel_value_roi, plan_economics, plan_ltv_cac,
                       run_simulation, true_channel_plan_summary)

pd.set_option("display.width", 200, "display.max_columns", 20, "display.float_format", "{:,.2f}".format)
cfg = calibrated_config(80_000, monthly_budget_brl=3_250_000)
df = run_simulation(cfg)

print("== Plan economics ==")
print(plan_economics(cfg)[["price_month", "avg_lifetime_months", "monthly_churn", "margin",
                           "gross_ltv", "contrib_ltv", "contrib_ltv_at_30pct", "contrib_ltv_at_55pct"]])
cp = true_channel_plan_summary(df, cfg)
print("\n== Incremental subs by channel x plan (truth) ==")
print(cp["incr_subs"].unstack().round(0))
print("\n== Incremental subs per R$ 1M spend ==")
print(cp["incr_subs_per_R$1M"].unstack())
print("\n== Contribution value per R$ 1 spent, by channel ==")
print(channel_value_roi(df, cfg)[["spend", "incr_subs", "contrib_ltv_per_sub", "contrib_roi", "marginal_contrib_roi"]])
print("\n== Plan-level LTV/CAC (contribution LTV) ==")
print(plan_ltv_cac(df, cfg))
