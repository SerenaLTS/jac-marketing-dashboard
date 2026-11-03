from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from metrics import load_data, totals, previous_week, TEMPLATE_COLUMNS, outcome_summary

st.set_page_config(page_title='Paid Performance | JAC Motors', page_icon='📊', layout='wide')
st.markdown('''<style>
.stApp {background:#f4f5f7;color:#193e4b}
.block-container {max-width:1450px;padding-top:2rem}
.hero {background:#193f4c;color:white;padding:28px 32px;margin-bottom:22px;border-radius:6px}
.hero h1 {font-size:30px;color:white;margin:0}.hero p {color:#c6dce2;margin:6px 0 0}
[data-testid="stMetric"] {background:white;border:1px solid #e6eaed;border-radius:10px;padding:18px}
[data-testid="stMetricLabel"] {color:#52656d}
</style>''', unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>Paid Performance report</h1><p>JAC Motors · Agency campaign monitoring · AUD</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.header('Report data')
    meta_upload = st.file_uploader('Upload META report', type=['csv'], key='meta-upload')
    google_upload = st.file_uploader('Upload Google report', type=['csv'], key='google-upload')
    st.caption('Upload one latest export per platform. Each upload replaces only that platform’s local report for this session. Uploads are not saved or shared.')
    st.download_button('Download daily agency template', ','.join(TEMPLATE_COLUMNS)+'\n', 'agency_daily_template.csv', 'text/csv')

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
    st.info('Upload the META and Google raw CSV reports to begin. Business data is not stored in the code repository.')
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
st.caption('Sources: ' + ' · '.join(f'{platform}: {name}' for platform, name, _ in inputs))
st.subheader('Channel overview · supplied reporting periods')
st.info('META and Google reporting periods do not align. Figures below describe each supplied period; there is no combined-period total. TikTok data has not been supplied.')
summary = []
for channel, group in df.groupby('Channel'):
    values = totals(group)
    summary.append({'Channel':channel, 'From':group['Reporting starts'].min().date(),
                    'To':group['Reporting ends'].max().date(), 'Campaigns':group['Campaign key'].nunique(),
                    'Spend (AUD)':values['Spend (AUD)'], 'Impressions':values['Impressions'],
                    'Clicks¹':values['Link clicks'], 'CPC (AUD)':values['CPC (AUD)'],
                    'CTR (%)':values['CTR (%)'], **outcome_summary(group)})
st.dataframe(pd.DataFrame(summary), hide_index=True, width='stretch')
st.caption('¹ META uses link clicks; Google uses exported Clicks. Outcomes are platform-reported and are not deduplicated customers. META cost per outcome uses LeadGen campaign spend only. Google Ads includes Search and Demand Gen; campaign type is not supplied on each campaign row.')

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
        st.subheader(channel)
        c1, c2 = st.columns(2)
        with c1:
            selected = st.multiselect('Campaigns', sorted(data['Campaign name'].unique()), default=sorted(data['Campaign name'].unique()), key=f'campaign-{channel}')
        scope = data[data['Campaign name'].isin(selected)]
        periods = data[['Reporting starts','Reporting ends']].drop_duplicates().sort_values('Reporting starts')
        options = ['All supplied periods'] + [f'{a:%d %b %Y} – {b:%d %b %Y}' for a,b in periods.itertuples(index=False, name=None)]
        with c2:
            period = st.selectbox('Reporting interval', options, key=f'period-{channel}')
        current = scope
        if period != options[0]:
            pair = periods.iloc[options.index(period)-1]
            current = scope[(scope['Reporting starts']==pair.iloc[0]) & (scope['Reporting ends']==pair.iloc[1])]
        if current.empty:
            st.info('No campaigns selected.'); continue
        st.caption(f"Actual coverage: {current['Reporting starts'].min():%d %b %Y} – {current['Reporting ends'].max():%d %b %Y}. Source intervals cannot be split into daily values.")
        m = totals(current)
        prior = previous_week(scope, current)
        if prior is None:
            st.caption('WoW unavailable for this selection. Choose a complete seven-day interval with a matching prior week. Google currently contains only one week.')
        else:
            st.caption('WoW compares the selected complete week with the immediately preceding week for the same campaigns. Arrows show direction, not target performance.')
        keys = ['Spend (AUD)', 'Impressions', 'Link clicks', 'CPC (AUD)', 'CPM (AUD)', 'CTR (%)']
        for col,key in zip(st.columns(6), keys):
            value = m[key]
            delta = f'{(value/prior[key]-1)*100:+.1f}%' if prior and value is not None and prior[key] not in (None,0) else None
            col.metric('Clicks' if channel=='Google Ads' and key=='Link clicks' else key, display(value,key), delta, delta_color='off')
        outcomes = outcome_summary(current)
        a,b,c = st.columns(3)
        a.metric(outcomes['Outcome'], f"{outcomes['Reported outcomes']:,.2f}" if outcomes['Reported outcomes'] is not None else 'N/A')
        b.metric('Cost / reported outcome', display(outcomes['Cost / outcome (AUD)'], '(AUD)'))
        c.metric('Landing page views', display(m['Landing page views'], 'count'))
        if channel == 'META':
            st.caption('Results are separated by indicator: instant-form leads are counted only from actions:leadgen.other. Prospecting Results are landing page views. Blank lead metrics for other objectives do not establish zero leads.')
        elif channel == 'Google Ads':
            st.caption('Conversions are preserved as decimal platform-attributed values, not rounded to people. Conversion actions and attribution settings were not supplied. Exported Conv. rate is shown only in raw detail because its denominator is not available. Landing page views are unavailable.')
        trend = pd.DataFrame([{'Period':f'{a:%d %b}–{b:%d %b}', **totals(g)} for (a,b),g in current.groupby(['Reporting starts','Reporting ends'])])
        for col,key in zip(st.columns(3), ['Spend (AUD)','Link clicks','CPC (AUD)']):
            with col: chart(trend,'Period',key, key + ' by source interval')
        st.markdown('#### Campaign performance')
        campaign_table = pd.DataFrame([{'Campaign':name, **totals(g), **outcome_summary(g)} for name,g in current.groupby('Campaign name')])
        st.dataframe(campaign_table, hide_index=True, width='stretch')
        with st.expander('Raw report rows and definitions'):
            st.dataframe(current, hide_index=True, width='stretch')
            st.markdown('CPC = spend ÷ clicks. CPM = spend ÷ impressions × 1,000. CTR = clicks ÷ impressions × 100. Cost / LPV = spend ÷ measured landing page views. Zero denominators show N/A. Reach is not summed. Google total/subtotal rows are excluded to prevent double counting. Budget is the exported configured budget, not an agreed CPA target. Revenue, CRM lead quality and target CPA are unavailable.')
            st.download_button('Download filtered rows', current.to_csv(index=False).encode(), f'{channel}_filtered.csv', 'text/csv', key=f'download-{channel}')
