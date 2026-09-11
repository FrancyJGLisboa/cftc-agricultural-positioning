# Methodology

## Official sources

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

Category: Legacy **Non-Commercial**, not Disaggregated Managed Money. Report mode: `FutOnly`.

## Fields and validation

Let L = `noncomm_positions_long_all`, S = `noncomm_positions_short_all`, P = `noncomm_postions_spread_all` (the misspelling is in the API), and OI = `open_interest_all`. Store source S positive; display it as -S. Net N = L - S. Spreading P is kept separately and excluded from the position curves. Contract quantities remain distinct by market; each detailed chart has its own scale.

Reject empty data, unknown codes, duplicate date/code keys, invalid dates, missing counts, fractional/negative/nonfinite counts, mixed report types, and incomplete latest coverage. Check both identities for every record:

- L + P + `comm_positions_long_all` + `nonrept_positions_long_all` = OI.
- S + P + `comm_positions_short_all` + `nonrept_positions_short_all` = OI.

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
