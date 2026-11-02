# Paid Performance dashboard

Local Streamlit dashboard based on the supplied META CSV and report reference.

```sh
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

The app loads the CSV beside `app.py` by default. Uploading a CSV replaces that data for the current session; it is not persisted or shared between viewers. Uploads accept either the original META column structure or the daily cross-channel template in `templates/`. Duplicate/overlapping campaign reporting intervals are rejected to prevent double counting. No platform account connection or scheduled refresh is configured. See `DEPLOY.md` for Community Cloud setup.

The default range is the latest seven-day reporting interval. WoW requires one seven-day interval and the immediately preceding seven-day interval with identical campaign coverage. Partial intervals are never prorated. Latest two-day data remains available through the date selector. A zero comparison denominator has no percentage change.

Spend is AUD. CPC, CPM, CTR and cost per landing page view are recomputed from totals. Reach cannot be deduplicated across campaign periods and is shown only in raw detail. Results in this sample represent landing page views, not leads. TikTok/SEM, leads, sales, revenue and CPA targets are unavailable.

For a cross-channel production version, request **daily** exports for META, TikTok and Google Ads: date, channel, account/campaign IDs and names, currency, spend, impressions, link clicks, landing page views, leads/conversions, conversion definition, attribution window and timezone. Request CRM qualified leads/sales, revenue and agreed targets to assess agency outcomes. Agree on conversion definitions and attribution before combining leads across channels. Export data should carry the actual extract timestamp; reporting end alone does not establish freshness.
