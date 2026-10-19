# What is data, what is assumption

## Given by the business
- Average lifetime (churn): Premiere Futebol 12 months, Telecine 18, Claro tv+ bundle 18. Modelled as geometric lifetime, monthly churn = 1/N.
- Contribution margin range: 30%-55%. Telecine margin: 45%.

## Found online (Oct 2026)
- Premiere Futebol monthly: R$ 59,90 (several 2026 price guides and press).
- Telecine monthly: R$ 29,90 (Claro offer sheet Jun-Aug 2026; trade press).
- Claro tv+ with 120+ live channels and Netflix, Prime Video, Disney+, HBO Max, Apple TV and Globoplay: R$ 99,90 (Olhar Digital, 30 Jun 2026). Other reports cite higher prices for the Claro Box tv+ (R$ 159,90), so treat as an adjustable input.
- Brazil ad market share Q1 2026 (Cenp): internet 38.3%, open TV 31.3%; social = 24.8% of internet spend.

## Given: volume
- 80,000 new subscribers per month, organic + paid (flow, not base).
- Active subscriber base of ~1.23M, consistent with 80k new subs/month x the stated plan lifetimes.

## Given: budget mix
- Shares of the total budget: Google Ads campaigns 30%, YouTube 20%, Meta 25%; the remaining 25% split equally between TV and affiliates.
- Earlier inner Google Ads mix: brand search 10%, generic 30%, YouTube 20%, app 20%, PMax 20%. **Interpretation used:** with YouTube now reported separately, the 30% Google Ads block keeps the inner proportions of the other four campaign types (brand 12.5% / generic 37.5% / app 25% / PMax 25% of the block).

## Meta Ads campaign types (assumption)
- Three types: Advantage+ conversion campaigns (app/sales optimised for the subscription event), Reels/Stories video reach, remarketing/win-back.
- Public evidence found is generic, not streaming-specific: Meta's six objectives include App Promotion, whose Advantage+ App campaigns can optimise for a subscription event; one vendor guide reports Advantage+ Sales campaigns with 17% lower CPA than manual in global tests; Reels CPMs are lower than Feed CPMs, but lower CPM does not guarantee lower CPA. No ranking of types by profitability for streaming was found.
- Assumed current split 50% / 30% / 20%. The recommended split (about 65% / 24% / 11%) is the lab's optimum under *assumed* incremental CACs (structural R$ 110 / 150 / 190), so it is only as good as those assumptions. Remarketing is modelled as demand-driven (audience follows demand), hence low incrementality.

## Given: real media budget
- R$ 2.5M-4M per month. It implies a blended incremental CAC of R$ 136-218 (budget / ~18.4k incremental subs).

## Media price benchmarks found (inputs to a CAC, not CAC itself)
- Meta Ads Brazil 2026 (agency blog, Trafius): CPM R$ 8-50 (feed R$ 15-35, stories/reels R$ 8-20); CPC R$ 0.40-6.00.
- YouTube (global, eCommerce guide): CPM US$ 5-10; CTV US$ 14-18.5.
- Meta all-industry median CPA ~US$ 38 (global, 2026).
- From Jan 2026 Meta passes PIS/Cofins and ISS to advertisers in Brazil, ~12% on top of the media cost (press report).
- **Not found:** streaming-subscription CAC in Brazil, TV CPM, affiliate CPA. Conversion from click to paid subscription is the missing link, so these cannot yield CAC without an assumed conversion rate.

## Proxy benchmark used (not Brazil, not subscriptions)
- AppsFlyer, OTT and live-streaming Android apps (US): 51% organic / 49% non-organic installs. I found no public benchmark of organic vs paid share of *subscriptions* for streaming in Brazil. Installs are not subscriptions, and "non-organic" means attributed to a media source, which includes demand that would have arrived anyway.

## Assumptions (no public source; replace with your data)
| Item | Value used | Why |
|---|---|---|
| Margin per plan (Premiere, bundle) | Premiere 38%, bundle 33% | Inside the 30-55% range. Bundle lowest: wholesale cost of 4+ SVODs and 120 channels. Premiere: sports-rights cost. **Not sourced; exact values need Finance.** |
| Channel -> plan mix | See `default_config()` | Hypotheses: TV/YouTube skew to football, Meta to Telecine (impulse, low ticket), affiliates to the bundle. The lab asks whether measurement methods can *recover* these; they are not findings. |
| Organic plan mix | 45% / 25% / 30% | Placeholder. |
| Response curves (beta, decay, saturation) | See `config.py` | Stylised, chosen to give CACs of R$ 80-180. |
| Share of subs truly incremental to marketing | ~23% | Output of the simulator, not an input. Consistent with "about half of what is attributed to paid would have come anyway". |
| Incremental CAC level (R$ 81-176 by channel) | Stylised | Not calibrated to market data. Real CACs may be several times higher: at R$ 200 / 300 / 400 per incremental sub the monthly budget is R$ 3.7M / 5.5M / 7.3M for the same volume. |
| Last-click weights | `attribution.py` | Calibrated so last-click credits ~50% of subs to paid media. |
| Relative CAC across channels | Simulator structure, scaled to the budget | Needs geo-experiments (stage 3); benchmarks cannot provide incremental CAC. |
| Incremental CAC by channel (structural, before scaling to budget) | tv 136, affiliates 81, Meta Advantage+ 110, Meta Reels video 150, Meta remarketing 190, brand 176, generic search 100, YouTube 95, app 125, PMax 150 | Stylised relative levels in `TARGET_INCREMENTAL_CAC`; no data. Generic search assumed more incremental than brand; PMax assumed to harvest brand demand (low incrementality). |
| Plan mix of the new Google channels | Generic search skews to Premiere (football queries); app and PMax close to organic | Hypotheses to be recovered by the lab, not findings. |

## Funnel and creative layer (assumptions)
CPM (R$ per 1,000 impressions, start of 2023) and CTR per channel, in `funnel.py`. Meta values sit inside the Brazilian 2026 ranges found (feed CPM R$ 15-35, Reels/Stories CPM R$ 8-20, CPC R$ 0.40-6.00): Advantage+ CPM 22 / CTR 1.1%, Reels video 14 / 0.7%, remarketing 30 / 1.8%. All other channels have no public streaming benchmark and are stylised: TV CPM 18 (no clicks), affiliates 12 / 0.5%, YouTube 28 / 0.4% (28% view rate), brand search 180 / 18% (CPC ~R$ 1), generic search 99 / 4.5%, app campaigns 28 / 1.0%, PMax 35 / 0.9%.
- CPM inflates 8% a year, rises up to 25% during demand events on auction channels, and varies by UF and day.
- Creatives (394 over 3 years): launch cadence, formats, themes and promoted plans are assumptions. Themes follow each channel's assumed plan mix. Quality (lognormal) shifts CTR and CPM; CTR decays with creative age (fatigue). Creatives also carry a causal lift (theme +10% football, +5% bundle/launch, -10% price offer; format effects of -5% to +7%; noise sd 12%), with slow fatigue and a football-event boost. These effects are assumptions, normalised to mean 1 per channel so channel CACs keep their calibration.
