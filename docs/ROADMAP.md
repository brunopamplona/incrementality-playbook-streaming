# Roadmap

| Stage | Module | Status | Deliverable |
|---|---|---|---|
| 1. Simulator | `simulator.py`, `truth.py` | done | Panel with known incremental effect per channel, confounded on purpose |
| 2. Naive attribution | `attribution.py` | done | Last-click and panel regression vs truth: bias table + chart |
| 3. Geo-experiment | `geo_experiment.py` | next | Use `Intervention` to go dark in matched geos; estimate lift with diff-in-diff and synthetic control; show recovery of true incremental subs with CIs; power analysis (how many geos / weeks?) |
| 4. Calibrated MMM | `mmm.py` | planned | Bayesian MMM (PyMC-Marketing or Meridian): uncalibrated vs calibrated with stage-3 lift; parameter recovery plots for beta, decay, k, s |
| 5. Budget optimisation | `optimize.py` | done (on ground truth) | Demonstrated on true response curves: +1.9% contribution value / R$ 1.6M/year. Stages 3–4 replace assumed curves with experimentally validated ones for a defensible real-world result. |
| 6. LTV bridge | `ltv.py` | planned | Plan-level survival curves from `plan_price` / `plan_avg_lifetime_months`; incremental CAC vs incremental LTV and payback, with content-cost margins per plan (input needed) |

## Failure scenarios to include (what makes the repo senior-level)
- MMM with low spend variation or collinear channels (TV and YouTube both chase events): show wide posteriors / wrong ROI.
- Geo-experiment with too few geos or contaminated controls (spillover): show bias.
- Calibration with a biased lift test: show how bad priors propagate.

## Extensions
- Channel-specific plan mix (does Meta bring more Telecine, TV more Premiere?) and football seasonality in churn (Brasileirão calendar).
- Price changes and promotions as additional causal drivers.
- Live-channel (120 FAST/linear channels) retention effects as a separate incrementality module.
