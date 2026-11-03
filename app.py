from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from metrics import load_data, totals, previous_week, outcome_summary

st.set_page_config(page_title='Paid Performance | JAC Motors', page_icon='📊', layout='wide')
st.markdown('''<style>
.stApp {background:#f4f5f7;color:#193e4b}
.block-container {max-width:1380px;padding-top:1.5rem}
.hero {background:#193f4c;color:white;padding:22px 28px;margin-bottom:20px;border-radius:6px}
.hero h1 {font-size:27px;color:white;margin:0}.hero p {color:#c6dce2;margin:6px 0 0}
[data-testid="stMetric"] {background:white;border:1px solid #e6eaed;border-radius:10px;padding:16px}
[data-testid="stMetricLabel"] {color:#52656d}
</style>''', unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>Paid Performance report</h1><p>JAC Motors · AUD</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.header('Reports')
    meta_upload = st.file_uploader('Upload META report', type=['csv'], key='meta-upload')
    google_upload = st.file_uploader('Upload Google report', type=['csv'], key='google-upload')
    st.caption('One file per channel · Uploads last this session only.')

# Prefer the latest supplied reports; never append the overlapping older META export.
root = Path(__file__).parent
meta_local = root / 'Meta -Campaigns-3-Oct-2026-1-Nov-2026.csv'
if not meta_local.exists():
    meta_local = next(root.glob('JAC-Motors-Campaigns-*.csv'), None)
google_local = root / 'Google Report - Oct.csv'
inputs = []
for platform, upload, local in [('META', meta_upload, meta_local), ('Google Ads', google_upload, google_local)]:
    if upload is not None:
        inputs.append((platform, upload.name, upload.getvalue()))
    elif local is not None and local.exists():
        inputs.append((platform, local.name, local.read_bytes()))
if not inputs:
    st.info('Upload a META or Google report to begin.')
    st.stop()
frames = []
for platform, name, content in inputs:
    try:
        part = load_data(content)
        if not part.empty and not part['Channel'].eq(platform).all():
            raise ValueError(f'Please upload a {platform} report in this upload field.')
        part['Source file'] = name
        frames.append(part)
    except (ValueError, UnicodeError, KeyError, pd.errors.ParserError) as exc:
        st.error(f'{name}: {exc}')
        st.stop()
df = pd.concat(frames, ignore_index=True)
if df.empty:
    st.info('No report rows found.'); st.stop()
for _, group in df.groupby('Campaign key'):
    ordered = group.sort_values('Reporting starts')
    if (ordered['Reporting starts'].iloc[1:].reset_index(drop=True) <= ordered['Reporting ends'].iloc[:-1].reset_index(drop=True)).any():
        st.error('Overlapping exports detected. Upload only one export per platform.'); st.stop()
st.subheader('Channel Overview')
st.caption('Each channel shows its own reporting period. Outcomes use different platform definitions.')
summary = []
for channel, group in df.groupby('Channel'):
    values = totals(group)
    summary.append({'Channel':channel, 'From':group['Reporting starts'].min().date(),
                    'To':group['Reporting ends'].max().date(), 'Campaigns':group['Campaign key'].nunique(),
                    'Spend (AUD)':values['Spend (AUD)'], 'Impressions':values['Impressions'],
                    'Clicks':values['Link clicks'], 'CPC (AUD)':values['CPC (AUD)'],
                    'CTR (%)':values['CTR (%)']})
st.dataframe(pd.DataFrame(summary), hide_index=True, width='stretch')

def chart(frame, x, y, title, kind='bar'):
    fig = (px.bar if kind == 'bar' else px.line)(frame, x=x, y=y, title=title)
    fig.update_traces(marker_color='#71bbd3')
    fig.update_layout(height=290, paper_bgcolor='white', plot_bgcolor='white', margin=dict(l=15,r=15,t=50,b=20), title_font_size=16)
    st.plotly_chart(fig, width='stretch')

def display(value, key):
    if value is None or pd.isna(value): return 'N/A'
    if '(AUD)' in key: return f'${value:,.2f}'
    if '(%)' in key: return f'{value:.2f}%'
    return f'{value:,.0f}'

channels = sorted(df['Channel'].unique())
for tab, channel in zip(st.tabs(channels), channels):
    with tab:
        data = df[df['Channel']==channel]
        st.subheader('Overview · WoW')
        c1, c2 = st.columns(2)
        with c1:
            selected = st.multiselect('Campaigns', sorted(data['Campaign name'].unique()), default=[], placeholder='All campaigns', key=f'campaign-{channel}')
        scope = data[data['Campaign name'].isin(selected)] if selected else data
        periods = data[['Reporting starts','Reporting ends']].drop_duplicates().sort_values('Reporting starts')
        options = ['All periods'] + [f'{a:%d %b %Y} – {b:%d %b %Y}' for a,b in periods.itertuples(index=False, name=None)]
        with c2:
            period = st.selectbox('Date range', options, key=f'period-{channel}')
        current = scope
        if period != options[0]:
            pair = periods.iloc[options.index(period)-1]
            current = scope[(scope['Reporting starts']==pair.iloc[0]) & (scope['Reporting ends']==pair.iloc[1])]
        if current.empty:
            st.info('No campaigns selected.'); continue
        st.caption(f"Period: {current['Reporting starts'].min():%d %b %Y} – {current['Reporting ends'].max():%d %b %Y}")
        m = totals(current)
        prior = previous_week(scope, current)
        st.caption('vs previous week' if prior is not None else 'WoW — unavailable for this period')
        outcomes = outcome_summary(current)
        cards = st.columns(6)
        for col,key,label in zip(cards[:4], ['Spend (AUD)', 'Link clicks', 'CPC (AUD)', 'CTR (%)'], ['Cost', 'Link clicks' if channel=='META' else 'Clicks', 'CPC', 'CTR']):
            value = m[key]
            delta = f'{(value/prior[key]-1)*100:+.1f}%' if prior and value is not None and prior[key] not in (None,0) else None
            col.metric(label, display(value,key), delta, delta_color='off')
        count = outcomes['Reported outcomes']
        cards[4].metric('Instant-form leads' if channel=='META' else 'Google conversions',
                        ('N/A' if count is None else f'{count:,.0f}' if channel=='META' else f'{count:,.2f}'))
        cards[5].metric('LeadGen CPL' if channel=='META' else 'Cost / conversion', display(outcomes['Cost / outcome (AUD)'], '(AUD)'))
        trend = pd.DataFrame([{'Period':f'{a:%d %b}–{b:%d %b}', **totals(g)} for (a,b),g in current.groupby(['Reporting starts','Reporting ends'])])
        for col,key in zip(st.columns(3), ['Spend (AUD)','Link clicks','CPC (AUD)']):
            with col: chart(trend,'Period',key, {'Spend (AUD)':'Cost', 'Link clicks':'Link clicks' if channel=='META' else 'Clicks', 'CPC (AUD)':'CPC'}[key])
        st.markdown('#### Campaign performance')
        campaign_rows = []
        for name,g in current.groupby('Campaign name'):
            values, result = totals(g), outcome_summary(g)
            campaign_rows.append({'Campaign':name, 'Impressions':values['Impressions'], 'Clicks':values['Link clicks'],
                                  'Cost (AUD)':values['Spend (AUD)'], 'CPC (AUD)':values['CPC (AUD)'],
                                  'CTR (%)':values['CTR (%)'],
                                  'Instant-form leads' if channel=='META' else 'Google conversions':result['Reported outcomes']})
        campaign_table = pd.DataFrame(campaign_rows).sort_values('Cost (AUD)', ascending=False)
        st.dataframe(campaign_table, hide_index=True, width='stretch')
        with st.expander('Report details'):
            st.caption('Sources: ' + ' · '.join(current['Source file'].unique()))
            st.markdown('**Reporting:** Source intervals are not split or prorated. WoW requires matching seven-day periods and campaigns. Arrows show change, not target achievement. Uploads are session-only.')
            st.markdown('**META:** Clicks are link clicks. Only instant-form LeadGen results count as leads; Prospecting results are landing page views. LeadGen CPL uses LeadGen spend only. Blank lead values for other objectives mean unavailable.')
            st.markdown('**Google:** Includes Search and Demand Gen. Conversions are platform-attributed values, not a count of unique people. Conversion actions and attribution settings are unconfirmed. Exported conversion rate is retained below; its denominator was not supplied. Landing page views are unavailable.')
            st.markdown('**Other data:** TikTok, revenue, lead quality and target CPA have not been supplied.')
            st.dataframe(current, hide_index=True, width='stretch')
            st.markdown('CPC = spend ÷ clicks. CPM = spend ÷ impressions × 1,000. CTR = clicks ÷ impressions × 100. Cost / LPV = spend ÷ measured landing page views. Zero denominators show N/A. Reach is not summed. Google total/subtotal rows are excluded to prevent double counting. Budget is the exported configured budget, not an agreed CPA target. Revenue, CRM lead quality and target CPA are unavailable.')
            st.download_button('Download filtered rows', current.to_csv(index=False).encode(), f'{channel}_filtered.csv', 'text/csv', key=f'download-{channel}')
