# Streaming Growth Lab

**Can your marketing measurement recover the truth?**
A synthetic streaming platform where the *true* incremental effect of every marketing channel, on every plan, is known. Measurement methods (last-click, regression, geo-experiments, MMM) are benchmarked against that truth instead of against each other.

![Truth vs naive attribution](docs/img/stage2_truth_vs_naive.png)

## Datasets
`make data` writes six synthetic datasets to `data/` (3 years, daily, 27 UFs, 10 channels): campaign-level spend, impressions, clicks, video views and platform-reported conversions; creative-level metrics and catalog (format, theme, promoted plan, hook, fatigue); business outcomes by plan; and the hidden ground truth. See [data/README.md](data/README.md). They are included in the repository so you can start analysing without running the simulator.

## Plans being measured
| Plan | Price/month | Avg. lifetime | Monthly churn | Margin* | Gross LTV | Contribution LTV |
|---|---|---|---|---|---|---|
| Premiere Futebol (monthly) | R$ 59,90 | 12 months | 8.3% | 38% | R$ 719 | R$ 273 |
| Telecine | R$ 29,90 | 18 months | 5.6% | 45% | R$ 538 | R$ 242 |
| Claro tv+ bundle (120 live channels + Netflix, Prime Video, Disney+, HBO Max) | R$ 99,90 | 18 months | 5.6% | 33% | R$ 1,798 | R$ 593 |

\*Telecine's margin (45%) is given by the business; Premiere (38%) and bundle (33%) are assumed inside the 30-55% range, not sourced. See [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md) for what is data and what is assumption.

## Data-generating process
Per geo (27 Brazilian UFs) and day:
```
organic          = pop * base_rate * trend * season * day_of_week * (1 + event) * geo_shock
incr_c           = pop * beta_c * Hill( Adstock(spend_c / pop; decay_c); k_c, s_c )
new_subs[plan]   ~ Poisson( organic * mix_organic[plan] + sum_c incr_c * mix_c[plan] )
```
Confounding is built in: demand events lift organic demand *and* spend; brand-search spend chases demand; TV is bought nationally while YouTube/Meta/affiliates vary by geo-week.

## Calibration to the business
`calibrated_config(80_000, monthly_budget_brl=3_250_000)` matches volume, organic/paid split, CAC structure and budget.

| Item | Per month |
|---|---|
| New subscribers (organic + paid) | 80,000 |
| Baseline organic (would come with zero marketing) | ~61,600 (77%) |
| Truly marketing-incremental | ~18,400 (23%) |
| Credited to paid by last-click | ~40,000 (50%) |
| Active base (steady state, 80k x blended lifetime 15.4 months) | ~1.23M |
| Media budget (given: R$ 2.5M-4M; mid-point used) | R$ 3.25M |

Budget mix (given, shares of total budget): Google Ads campaigns 30%, YouTube 20%, Meta 25%, TV 12.5%, affiliates 12.5%. The 30% Google Ads block is split by the business's inner mix (brand 10 : generic 30 : app 20 : PMax 20, renormalised after taking YouTube out). The 25% Meta block is split across three campaign types, 50% Advantage+ conversion / 30% Reels video reach / 20% remarketing, an assumed current split (see `optimize.optimal_split` for the recommended one).

The 50% last-click share is calibrated to a proxy benchmark (AppsFlyer: ~49% of OTT/live-streaming app installs are non-organic). The 23% incremental share is an assumption derived from it. See docs/ASSUMPTIONS.md.

## Results at R$ 3.25M/month
Estimated CAC / true incremental CAC (1.0 = correct; <1 = the method flatters the channel):

| Channel | Budget share | True incr. CAC | Marginal CAC | Last-click bias | Regression bias |
|---|---|---|---|---|---|
| affiliates | 12.50% | R$ 127 | R$ 275 | 0.7x | 1.7x |
| youtube | 20.00% | R$ 149 | R$ 288 | 3.6x | 2.1x |
| search_generic | 11.25% | R$ 156 | R$ 328 | 0.5x | 1.1x |
| meta_advantage | 12.50% | R$ 172 | R$ 261 | 0.6x | 1.2x |
| app_campaigns | 7.50% | R$ 195 | R$ 322 | 0.2x | 0.9x |
| tv | 12.50% | R$ 213 | R$ 356 | 3.2x | 2.0x |
| meta_reels_video | 7.50% | R$ 235 | R$ 402 | 0.6x | 1.2x |
| pmax | 7.50% | R$ 235 | R$ 414 | 0.2x | 1.1x |
| search_brand | 3.75% | R$ 275 | R$ 780 | 0.1x | 0.0x |
| meta_remarketing | 5.00% | R$ 297 | R$ 715 | 0.1x | 0.0x |

Google platform (Google Ads + YouTube): dashboard proxy ~R$ 69 vs true incremental CAC ~R$ 172 (2.5x). Meta platform: dashboard proxy ~R$ 66 vs true ~R$ 206 (3.1x).

## Recommended Meta split (inside the 25% Meta block)
`optimal_split(df, cfg, meta_channels)` holds Meta's combined spend fixed and moves it along the true response curves:

| Meta campaign type | Assumed current | Recommended |
|---|---|---|
| Advantage+ conversion (app/sales, subscription event) | 50% | **65%** |
| Reels / Stories video reach | 30% | **24%** |
| Remarketing / win-back | 20% | **11%** |

Gain: +3.1% contribution value inside Meta (~R$ 0.5M/year of contribution LTV). Depends on the assumed incremental CACs per type; validate with Meta Conversion Lift tests.

## Real budget scenarios: R$ 2.5M-4M per month
Public benchmarks give media prices (CPM/CPC), not streaming CAC, so the CAC level is **implied by the budget**: same ~18.4k incremental subs/month, higher spend means higher CAC. The relative CAC across channels is the simulator's assumption, to be measured by experiments (roadmap stage 3).

| Incremental CAC (R$) | R$ 2.5M | R$ 3.25M | R$ 4.0M |
|---|---|---|---|
| Blended | 136 | 177 | 217 |
| affiliates | 97 | 127 | 156 |
| youtube | 114 | 149 | 183 |
| search_generic | 120 | 156 | 192 |
| meta_advantage | 132 | 172 | 212 |
| app_campaigns | 150 | 195 | 241 |
| tv | 164 | 213 | 262 |
| meta_reels_video | 180 | 235 | 289 |
| pmax | 180 | 235 | 289 |
| search_brand | 212 | 275 | 339 |
| meta_remarketing | 229 | 297 | 366 |

Plan LTV / marginal CAC (contribution LTV): bundle 2.3x / 1.8x / 1.5x; Premiere 1.1x / 0.8x / 0.7x; Telecine 0.9x / 0.7x / 0.6x. Run `python scripts/run_budget_scenarios.py`.

## Limitations (stated up front)
- Margins, budget mix, channel-to-plan affinity and the organic plan mix are assumptions (see docs/ASSUMPTIONS.md).
- Effects are additive with no cross-channel synergies.
- Last-click weights are a stylised assumption of how dashboards credit channels.
- Plan CAC spreads each channel's spend evenly over its subscribers; it is a convention, not a measurement.

## Roadmap
Simulator -> naive attribution -> **geo-experiment** -> **calibrated MMM** -> **budget optimisation** -> **LTV bridge**. See [docs/ROADMAP.md](docs/ROADMAP.md).
