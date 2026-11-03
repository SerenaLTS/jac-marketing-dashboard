# Paid Performance dashboard

Local Streamlit dashboard based on the supplied META CSV and report reference.

## Current agency-report view

Supports multi-file uploads of the native META campaign CSV and Google Ads UTF-16 tab-separated report (`.csv`). The latest local META and Google reports are preferred over the older overlapping META extract. Source CSVs remain excluded from Git; hosted viewers must upload their reports.

Channel overview shows each platform's own reporting coverage, with no misleading combined-period total. Google Ads is kept as Google Ads because its export includes Search and Demand Gen without a per-campaign type column. All Google total/subtotal rows are excluded. META `actions:leadgen.other` results are counted separately from landing page views; lead cost uses only the matching LeadGen campaign spend. Google conversions retain decimal attribution. Conversion definitions, timezone and Google attribution settings remain unconfirmed. Exported Google conversion rate is available in raw detail only because its denominator is not supplied.

Each channel has campaign and source-interval filters, comparable-week deltas when available, source-interval charts, campaign summaries and downloadable detail. Google currently has one week, so Google WoW is unavailable. No CPA target, daily allocation or revenue is inferred.

```sh
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

The app loads the CSV beside `app.py` by default. Uploading a CSV replaces that data for the current session; it is not persisted or shared between viewers. Uploads accept either the original META column structure or the daily cross-channel template in `templates/`. Duplicate/overlapping campaign reporting intervals are rejected to prevent double counting. No platform account connection or scheduled refresh is configured. See `DEPLOY.md` for Community Cloud setup.

The default range is the latest seven-day reporting interval. WoW requires one seven-day interval and the immediately preceding seven-day interval with identical campaign coverage. Partial intervals are never prorated. Latest two-day data remains available through the date selector. A zero comparison denominator has no percentage change.

Spend is AUD. CPC, CPM, CTR and cost per landing page view are recomputed from totals. Reach cannot be deduplicated across campaign periods and is shown only in raw detail. Results in this sample represent landing page views, not leads. TikTok/SEM, leads, sales, revenue and CPA targets are unavailable.

For a cross-channel production version, request **daily** exports for META, TikTok and Google Ads: date, channel, account/campaign IDs and names, currency, spend, impressions, link clicks, landing page views, leads/conversions, conversion definition, attribution window and timezone. Request CRM qualified leads/sales, revenue and agreed targets to assess agency outcomes. Agree on conversion definitions and attribution before combining leads across channels. Export data should carry the actual extract timestamp; reporting end alone does not establish freshness.
