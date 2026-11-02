# Deploy to Streamlit Community Cloud

1. Restore GitHub login (`gh auth login -h github.com`) and select/create the intended private GitHub repository.
2. Push `app.py`, `metrics.py`, `requirements.txt`, `.streamlit/config.toml`, `templates/`, and documentation. The original campaign CSV is intentionally excluded from Git to avoid publishing business data. The hosted app starts with an upload prompt.
3. Sign in at https://share.streamlit.io and create an app from that repository: branch `main`, entrypoint `app.py`, Python 3.12 in advanced settings.
4. Deploy, verify successful startup, then verify app sharing is private before uploading campaign data. Invite intended viewers separately when access is agreed.
5. Upload the original META CSV or the daily consolidated agency template to check the report. Uploads are session-only and are not a shared data store.

The original META CSV remains on this computer. To use a persistent shared dataset, implement durable storage or an authorized connected data source; do not rely on Community Cloud local disk for permanent uploads.
