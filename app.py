from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from metrics import load_data, totals, previous_week, TEMPLATE_COLUMNS

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
    upload = st.file_uploader('Upload campaign CSV', type=['csv'])
    st.caption('Accepts the original META export or the daily cross-channel template. Upload replaces sample data for this session; uploads are not saved for other viewers or future sessions.')
    st.download_button('Download agency CSV template', ','.join(TEMPLATE_COLUMNS)+'\n', 'agency_daily_template.csv', 'text/csv')

files = sorted(Path(__file__).parent.glob('*.csv'))
if upload is None and not files:
    st.info('Upload a META CSV to begin.')
    st.stop()
try:
    df = load_data(upload.getvalue() if upload else files[0].read_bytes())
except (ValueError, pd.errors.ParserError) as exc:
    st.error(str(exc))
    st.stop()
if df.empty:
    st.info('The CSV contains no report rows.')
    st.stop()
source = upload.name if upload else files[0].name
st.caption(f"Source: {source} · Data through {df['Reporting ends'].max():%d %b %Y} · Reporting intervals, not daily data")

periods = df[['Reporting starts', 'Reporting ends']].drop_duplicates().sort_values('Reporting starts')
complete = periods[(periods['Reporting ends'] - periods['Reporting starts']).dt.days == 6]
default = complete.iloc[-1] if not complete.empty else periods.iloc[-1]
default_start = default.iloc[0].date()
if (df['Reporting starts'] == df['Reporting ends']).all():
    default_start = max(df['Reporting starts'].min().date(), default.iloc[1].date()-pd.Timedelta(days=6))
c1, c2 = st.columns([2, 3])
with c1:
    dates = st.date_input('Reporting date range', (default_start, default.iloc[1].date()),
                          min_value=df['Reporting starts'].min().date(), max_value=df['Reporting ends'].max().date())
with c2:
    campaigns = st.multiselect('Campaign', sorted(df['Campaign name'].unique()), default=sorted(df['Campaign name'].unique()))
st.caption('Only complete source intervals inside the date range are included. Dates within an interval cannot be split or prorated.')
if len(dates) != 2:
    st.info('Select a start and end date.'); st.stop()
scope = df[df['Campaign name'].isin(campaigns)]
current = scope[(scope['Reporting starts'] >= pd.Timestamp(dates[0])) & (scope['Reporting ends'] <= pd.Timestamp(dates[1]))]
if current.empty:
    st.info('No full reporting intervals match these filters. Expand the date range.'); st.stop()
m = totals(current)
prior = previous_week(scope, current)
st.subheader('Overview · WoW')
if prior is None:
    st.info('WoW unavailable: select one 7-day interval with a matching prior week and the same campaign coverage.')
else:
    start = current['Reporting starts'].min()
    st.caption(f"Comparing {start:%d %b}–{current['Reporting ends'].max():%d %b %Y} with {start-pd.Timedelta(days=7):%d %b}–{start-pd.Timedelta(days=1):%d %b %Y}. Arrows show direction, not performance against a target.")
keys = ['Link clicks', 'CPM (AUD)', 'Spend (AUD)', 'CPC (AUD)', 'Landing page views', 'CTR (%)']
for col, key in zip(st.columns(6), keys):
    value = m[key]
    display = 'N/A' if value is None else (f'{value:.2f}%' if key == 'CTR (%)' else f'${value:,.2f}' if 'AUD' in key else f'{value:,.0f}')
    delta = f'{(value/prior[key]-1)*100:+.1f}%' if prior and value is not None and prior[key] not in (None, 0) else None
    col.metric(key, display, delta, delta_color='off')
st.caption('Leads, lead conversion rate, revenue and target CPA: not provided. Landing page views are not leads.')

trend = pd.DataFrame([{'Period': f'{a:%d %b}–{b:%d %b}', **totals(g)} for (a,b),g in current.groupby(['Reporting starts','Reporting ends'])])
def chart(frame, x, y, title, color='#71bbd3', kind='line'):
    fig = (px.bar if kind == 'bar' else px.line)(frame, x=x, y=y, title=title)
    fig.update_traces(marker_color=color, **({'line_color': color, 'mode':'lines+markers'} if kind == 'line' else {}))
    fig.update_layout(height=280, paper_bgcolor='white', plot_bgcolor='white', margin=dict(l=15,r=15,t=50,b=20), title_font_size=16)
    st.plotly_chart(fig, width='stretch')
for col, key in zip(st.columns(3), ['Spend (AUD)', 'Link clicks', 'Landing page views']):
    with col: chart(trend, 'Period', key, f'{key} by report interval')
st.subheader('Channel Overview')
table = pd.DataFrame([{'Channel':channel, 'Availability':'Provided' if not (g := current[current['Channel']==channel]).empty else 'Not provided',
                       **(totals(g) if not g.empty else {})} for channel in ['META','TikTok','SEM']])
st.dataframe(table, hide_index=True, width='stretch', column_config={k:st.column_config.NumberColumn(k, format='%.2f') for k in m})
metric = st.selectbox('Channel chart metric', list(m), index=0)
for col, channel in zip(st.columns(3), ['TikTok','META','SEM']):
    with col:
        channel_rows = current[current['Channel']==channel]
        if not channel_rows.empty:
            channel_trend = pd.DataFrame([{'Period': f'{a:%d %b}–{b:%d %b}', **totals(g)} for (a,b),g in channel_rows.groupby(['Reporting starts','Reporting ends'])])
            chart(channel_trend, 'Period', metric, channel, kind='bar')
        else:
            st.markdown(f'#### {channel}')
            st.info('No data provided')
with st.expander('Campaign detail & metric definitions'):
    st.dataframe(current, hide_index=True, width='stretch')
    st.markdown('CPC = spend ÷ link clicks. CPM = spend ÷ impressions × 1,000. CTR = link clicks ÷ impressions × 100. Cost / LPV = spend ÷ landing page views. Rates are recomputed from totals; zero denominators display N/A. Reach is not summed across periods. META attribution settings remain visible in the source detail; channels may use different attribution methods.')
    st.download_button('Download filtered source rows', current.to_csv(index=False).encode(), 'filtered_meta.csv', 'text/csv')
