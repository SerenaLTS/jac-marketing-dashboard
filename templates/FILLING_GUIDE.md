# Agency daily reporting template

Please supply one consolidated UTF-8 CSV using `agency_daily_template.csv`.

**One row = one calendar day × one channel × one campaign ID.** Include explicit zero-activity rows for campaigns in scope. Do not add totals/subtotals, overlapping exports, ad-set rows or weekly summaries. Supply a complete historical file on each refresh; upload replaces the current report, rather than appending it.

| Field | Required | Definition / format |
|---|---|---|
| date | Yes | Reporting date, YYYY-MM-DD |
| channel | Yes | Exactly META, TikTok or SEM. SEM means Google Ads paid search; agree a separate mapping before adding other Google inventory. |
| campaign_id | Yes | Stable platform campaign ID; keep as text |
| campaign_name | Yes | Readable campaign name |
| currency | Yes | AUD only; do not mix currencies |
| timezone | Yes | Agreed reporting timezone, e.g. Australia/Sydney; consistent across all channels |
| spend | Yes | Daily media spend in AUD, numeric; no currency symbol or thousands separators. Agree whether GST/fees are included. |
| impressions | Yes | Daily impressions, nonnegative count |
| link_clicks | Yes | Destination/link clicks, not all interactions. Agree the matching platform metric. |
| landing_page_views | Yes | Daily measured landing page views. If a channel cannot provide an equivalent, flag that gap before submission; do not invent zeros. |
| leads | Optional | Measured lead count; blank = unavailable, 0 = measured zero. Currently retained in raw detail only. |
| conversion_definition | With leads | E.g. completed enquiry form; landing page views must not be called leads |
| attribution_window | With leads | Platform attribution setting; record click/view windows explicitly |
| extracted_at | Recommended | Actual export timestamp with offset, e.g. 2026-11-02T09:00:00+11:00 |

CPC, CPM, CTR and cost per landing page view are calculated by the dashboard from summed numerators/denominators. Do not type these into the CSV.

Please confirm which channels can provide landing page views and whether lead definitions/attribution can be aligned. The current dashboard does not aggregate leads across platforms or calculate lead CPA. Targets and budgets should be supplied separately at their agreed campaign/period grain; repeating a monthly target on daily rows would double count it.

The dashboard upload is session-only: it is not a shared submission form, durable database or scheduled refresh. Until persistent storage is added, send the complete CSV to Serena for review/upload. Do not include personal customer details.
