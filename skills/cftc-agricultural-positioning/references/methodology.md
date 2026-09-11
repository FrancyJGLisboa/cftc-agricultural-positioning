# Methodology

## Official sources

Edition 2.0 supports two independent report modes. New CLI state directories default to `managed-money`; existing 1.x state stays `legacy`.

| Mode | Dataset | Category |
| --- | --- | --- |
| `managed-money` | [72hh-3qpy](https://publicreporting.cftc.gov/Commitments-of-Traders/Disaggregated-Futures-Only/72hh-3qpy) | Disaggregated Managed Money |
| `legacy` | [6dca-aqww](https://publicreporting.cftc.gov/Commitments-of-Traders/Legacy-Futures-Only/6dca-aqww) | Legacy Non-Commercial |

Managed Money is not a synonym for Non-Commercial. See [CFTC Disaggregated notes](https://www.cftc.gov/MarketReports/CommitmentsofTraders/DisaggregatedExplanatoryNotes/index.htm). Each mode validates its own source schema and open-interest reconciliation. No category splicing or inferred fund identities.

Legacy links:

- API: https://publicreporting.cftc.gov/resource/6dca-aqww.json
- Dataset: https://publicreporting.cftc.gov/Commitments-of-Traders/Legacy-Futures-Only/6dca-aqww
- Release calendar: https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm
- Explanatory notes: https://www.cftc.gov/MarketReports/CommitmentsofTraders/ExplanatoryNotes/index.htm

No credentials or prices are required. Network access to `publicreporting.cftc.gov` is required for collection. The TXT endpoint is not a dependency. An API maximum is availability evidence, not proof of the latest scheduled publication.

## Fixed universe

| CFTC code | Market |
| --- | --- |
| 002602 | Corn |
| 005602 | Soybeans |
| 001602 | Wheat SRW, Chicago |
| 001612 | Wheat HRW, Kansas |
| 026603 | Soybean meal |
| 007601 | Soybean oil |
| 057642 | Live cattle |
| 054642 | Lean hogs |
| 061641 | Feeder cattle |
| 033661 | Cotton No. 2 |
| 080732 | Sugar No. 11 |
| 083731 | Coffee C |
| 073732 | Cocoa |

Report type: `FutOnly` in both categories. Coverage stays at these thirteen codes in edition 2.0; Canola and spring wheat are not included.

## Fields and validation

For Legacy, let L = `noncomm_positions_long_all`, S = `noncomm_positions_short_all`, P = `noncomm_postions_spread_all` (the misspelling is in the API), and OI = `open_interest_all`. Store source S positive; display it as -S. Net N = L - S. Spreading P is kept separately and excluded from the position curves. Contract quantities remain distinct by market; each detailed chart has its own scale.

Reject empty data, unknown codes, duplicate date/code keys, invalid dates, missing counts, fractional/negative/nonfinite counts, mixed report types, and incomplete latest coverage. Check both identities for every record:

- L + P + `comm_positions_long_all` + `nonrept_positions_long_all` = OI.
- S + P + `comm_positions_short_all` + `nonrept_positions_short_all` = OI.

For Managed Money, L/S/P use `m_money_positions_long_all`, `m_money_positions_short_all`, and `m_money_positions_spread`. Reconcile each side of OI by summing Producer/Merchant, Swap Dealers, Managed Money, Other Reportables, and Nonreportables; add Swap, Managed Money and Other Reportables spreading to each side. Preserve the API spellings `swap__positions_short_all` and `swap__positions_spread_all`. Reject wrong-category or mixed-category rows.

Use decimal parsing before conversion to integers. Never replace missing observations with zero. Gaps longer than ten days break plotted lines and interrupt persistence.

## Four measures

1. **Net percentile:** compare N at date t with observations in [t minus five calendar years, t), excluding t. Use `100 * (count below N + 0.5 * count equal to N) / count`. Require at least 208 references and the first reference no more than 14 days after the window start. Otherwise show N/A. Clamp a leap-day cutoff to February 28. Save reference count and first/last dates for each observation.
2. **Net as percent of OI:** `100 * N / OI`, signed. OI = 0 yields N/A.
3. **Change decomposition:** `change in N = change in L - change in S`. Contributions are change in L and minus change in S. Reconcile exactly. A positive short contribution means fewer shorts. Compare each market with its preceding available report and retain that date. Opposing contributions are not percentages of net change.
4. **Persistence:** count consecutive changes with the same nonzero sign. Three increases require four observations. Zero resets to zero; reversal starts at one. A gap over ten days interrupts the streak. A streak whose beginning is outside available uninterrupted history is marked “at least.” Count reports, not calendar weeks.

Collect history from August 2016 for the initial percentile warm-up; display detailed chart history from August 2021. Historical revisions in today's API are not point-in-time publication vintages. No backtested prediction claim is made.

## Descriptive highlights

Flag percentiles >=95 or <=5, or persistence >=4 changes. Rank extreme-percentile flags first, then absolute distance from percentile 50, then absolute net change / previous OI, then market code. Show at most three on the panel. These are explicit review thresholds, not empirically calibrated return forecasts. Interpret positioning levels together with the sign of net exposure; a historically low positive net is not a net short.

A complete new edition still qualifies for delivery if no highlight threshold is reached. Historical-only corrections do not trigger the lightweight check; the next full collection incorporates them.


## Extended measures (methodology 3.0)

- **OI change:** current OI minus preceding available report OI, in contracts. Retain the actual comparison date and interval. A previous-report net change is N/A on the summary when the interval exceeds ten days; the detailed decomposition retains the observed interval explicitly.
- **4/13-week changes:** N(t) minus N(t − 28/91 calendar days), requiring that exact reference date and no intervening observation gap over ten days. Do not substitute the fourth/thirteenth previous row. Save the reference date and validity status; missing reference/gap gives N/A.
- **Five-year extrema:** minimum and maximum net in [t minus five calendar years, t], including t, with the most recent date on ties. Require the same prior-history coverage gate as the percentile; otherwise N/A. These are five-year extrema, not all-time records. The percentile continues to exclude t. Extrema remain in contracts in all views.
- **Physical equivalent:** multiply each contract quantity by verified tonnes per contract; divide by 1,000,000 for MMT. Preserve source contracts and conversion status in the CSV. Never convert an unrecognized `contract_units` value. No cross-market totals.
- **Percent-of-OI view:** each level uses contemporaneous OI. A displayed change is the difference between the two normalized levels, in percentage points. It differs from the original `net_change_pct_previous_oi`, which remains a separate diagnostic. Zero OI gives N/A.

MMT does not correct for price changes and does not measure investment, cash flow or physical inventory. With a constant conversion factor, net percentile and historical curve shape do not change. Detail extrema and long/short decomposition are explicitly labeled in contracts even when seasonal and history charts use another unit.

## Physical conversion registry

Source contract sizes are checked against the CFTC `contract_units` field on every row. Reference: [official CFTC agricultural futures-only report](https://www.cftc.gov/dea/futures/ag_lf.htm). Exact pound-to-tonne factor: 0.00045359237. Soybean meal uses US short tons (2,000 lb), not metric tons. Grain bushel weights: corn 56 lb, soybeans and wheat 60 lb. See [USDA feed-grain conversions](https://www.ers.usda.gov/data-products/feed-grains-database/documentation) [USDA wheat conversions](https://www.ers.usda.gov/data-products/wheat-data/documentation), and [CME soybean conversion](https://www.cmegroup.com/education/articles-and-reports/cme-globex-defined-spread-between-cbot-brazilian-soybean-sas-futures-and-cbot-soybean-zs-futures).

| Market | Contract quantity | Metric tonnes per contract |
| --- | --- | --- |
| Corn | 5,000 bushels × 56 lb | 127.0058636 |
| Soybeans; SRW wheat; HRW wheat | 5,000 bushels × 60 lb | 136.077711 |
| Soybean meal | 100 short tons | 90.718474 |
| Soybean oil | 60,000 lb | 27.2155422 |
| Live cattle; lean hogs | 40,000 lb | 18.1436948 |
| Feeder cattle; cotton | 50,000 lb | 22.6796185 |
| Sugar No. 11 | 112,000 lb | 50.80234544 |
| Coffee C | 37,500 lb | 17.009713875 |
| Cocoa | 10 metric tons | 10 |

The registry is not a claim that contract specifications never change. An unexpected source size blocks MMT until the source and registry are reviewed. The current supported histories use a fixed verified size per code; do not infer exposure continuity across a specification change.

## Seasonality

For position year Y, compare Y-to-date and Y−1 against the five calendar years Y−5 through Y−1. Map each date to a non-leap calendar; map February 29 to February 28. Split into fixed seven-day bins starting January 1 (bin 53 contains December 31). Keep the last observed report within each year/bin. Do not interpolate or forward-fill empty bins. Plot min/max and median only where at least three prior years have a nonmissing value; save each bin's reference count and actual current/prior-year dates in `seasonality.json`. Never include year Y in its own historical band or include observations after the requested as-of date.

The summary shows three seasonal charts, prioritizing the existing descriptive highlight ranking and filling unused slots in fixed market order. A seasonal range shows historical dispersion, not a confidence interval or price forecast. The detail view exposes the selected commodity's seasonality, five-year history, decomposition, extrema, OI and persistence.
