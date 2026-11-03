from io import BytesIO
import pandas as pd

COUNTS = ['Amount spent (AUD)', 'Impressions', 'Link clicks', 'Landing page views']
TEMPLATE_COLUMNS = ['date', 'channel', 'campaign_id', 'campaign_name', 'currency', 'timezone',
                    'spend', 'impressions', 'link_clicks', 'landing_page_views', 'leads',
                    'conversion_definition', 'attribution_window', 'extracted_at']

def load_data(content: bytes) -> pd.DataFrame:
    if content.startswith((b'\xff\xfe', b'\xfe\xff')):
        return load_google(content)
    df = pd.read_csv(BytesIO(content), dtype={'campaign_id': str}).dropna(how='all')
    if 'date' in df.columns:
        required = TEMPLATE_COLUMNS[:10]
        missing = set(required) - set(df.columns)
        if missing:
            raise ValueError('Missing template columns: ' + ', '.join(sorted(missing)))
        if df[required].isna().any().any():
            raise ValueError('Required template fields cannot be blank; use 0 only for measured zero activity.')
        if not df['currency'].eq('AUD').all():
            raise ValueError('This dashboard requires AUD. Convert currencies before combining reports.')
        if df['timezone'].nunique() != 1:
            raise ValueError('Use one consistent reporting timezone across channels.')
        if not df['channel'].isin(['META', 'TikTok', 'SEM']).all():
            raise ValueError('Channel must be META, TikTok or SEM.')
        df['Reporting starts'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='raise')
        df['Reporting ends'] = df['Reporting starts']
        df = df.rename(columns={'channel':'Channel', 'campaign_name':'Campaign name',
                                'spend':COUNTS[0], 'impressions':COUNTS[1],
                                'link_clicks':COUNTS[2], 'landing_page_views':COUNTS[3]})
        df['Campaign key'] = df['Channel'] + ':' + df['campaign_id'].astype(str)
    required = ['Reporting starts', 'Reporting ends', 'Campaign name', *COUNTS]
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError('Missing columns: ' + ', '.join(sorted(missing)))
    for col in ['Reporting starts', 'Reporting ends']:
        iso = df[col].astype(str).str.match(r'^\d{4}-\d{2}-\d{2}$').all()
        df[col] = pd.to_datetime(df[col], format='%Y-%m-%d' if iso else '%d/%m/%Y', errors='raise')
    if df[required[:3]].isna().any().any():
        raise ValueError('Report dates and campaign names must be populated.')
    if (df['Reporting ends'] < df['Reporting starts']).any():
        raise ValueError('Reporting end precedes start.')
    for col in COUNTS:
        # Blank delivery counts in the supplied META export mean no recorded activity.
        df[col] = pd.to_numeric(df[col], errors='raise').fillna(0)
        if (df[col] < 0).any():
            raise ValueError(f'Negative values in {col}.')
    if 'Channel' not in df:
        df['Channel'] = 'META'
    if 'Campaign key' not in df:
        df['Campaign key'] = df['Channel'] + ':' + df['Campaign name']
    for _, rows in df.groupby('Campaign key'):
        rows = rows.sort_values('Reporting starts')
        if (rows['Reporting starts'].iloc[1:].reset_index(drop=True) <= rows['Reporting ends'].iloc[:-1].reset_index(drop=True)).any():
            raise ValueError('Overlapping or duplicate periods for a campaign; upload one non-overlapping export.')
    return df.sort_values(['Reporting starts', 'Campaign name'])

def totals(df):
    spend, impressions, clicks = (float(df[c].sum()) for c in COUNTS[:3])
    lpv = float(df[COUNTS[3]].sum()) if df[COUNTS[3]].notna().all() else None
    return {'Spend (AUD)': spend, 'Impressions': impressions, 'Link clicks': clicks,
            'Landing page views': lpv, 'CPC (AUD)': spend / clicks if clicks else None,
            'CPM (AUD)': spend / impressions * 1000 if impressions else None,
            'CTR (%)': clicks / impressions * 100 if impressions else None,
            'Cost / LPV (AUD)': spend / lpv if lpv else None}

def previous_week(df, current):
    if not current.empty and (current['Reporting starts'] == current['Reporting ends']).all():
        start, end = current['Reporting starts'].min(), current['Reporting ends'].max()
        if (end-start).days != 6:
            return None
        prev = df[(df['Reporting starts'] >= start-pd.Timedelta(days=7)) &
                  (df['Reporting ends'] <= end-pd.Timedelta(days=7))]
        expected = {(r['Campaign key'], r['Reporting starts']-pd.Timedelta(days=7)) for _,r in current.iterrows()}
        actual = {(r['Campaign key'], r['Reporting starts']) for _,r in prev.iterrows()}
        # Each campaign must have all seven days, including explicit zero-activity rows.
        if expected != actual or not current.groupby('Campaign key').size().eq(7).all():
            return None
        return totals(prev)
    if current.empty or current['Reporting starts'].nunique() != 1 or current['Reporting ends'].nunique() != 1:
        return None
    start, end = current['Reporting starts'].iloc[0], current['Reporting ends'].iloc[0]
    if (end - start).days != 6:
        return None
    prev = df[(df['Reporting starts'] == start - pd.Timedelta(days=7)) &
              (df['Reporting ends'] == end - pd.Timedelta(days=7))]
    if set(prev['Campaign key']) != set(current['Campaign key']):
        return None
    return totals(prev)


def load_google(content):
    """Read native Google Ads UTF-16 TSV; never count exported total rows."""
    from io import StringIO
    import re
    text = content.decode('utf-16')
    lines = text.splitlines()
    match = re.fullmatch(r'(\d{1,2} [A-Za-z]+ \d{4}) - (\d{1,2} [A-Za-z]+ \d{4})', lines[1].strip())
    if not match:
        raise ValueError('Google report date range is not recognized.')
    start, end = [pd.to_datetime(x, format='%d %B %Y') for x in match.groups()]
    raw = pd.read_csv(StringIO(text), sep='\t', skiprows=2)
    df = raw[~raw['Campaign status'].str.startswith('Total:', na=False)].copy()
    if not df['Currency code'].eq('AUD').all():
        raise ValueError('Google report must use AUD.')
    week = pd.to_datetime(df['Week'], format='%Y-%m-%d', errors='raise')
    df['Reporting starts'] = week.clip(lower=start)
    df['Reporting ends'] = (week + pd.Timedelta(days=6)).clip(upper=end)
    for original, target in [('Cost',COUNTS[0]), ('Impr.',COUNTS[1]), ('Clicks',COUNTS[2]), ('Conversions','Google conversions')]:
        df[target] = pd.to_numeric(df[original].astype(str).str.replace(',', '', regex=False), errors='raise')
        if (df[target] < 0).any():
            raise ValueError('Negative Google metric values.')
    df['Landing page views'] = float('nan')
    df['Campaign name'] = df['Campaign']
    df['Channel'] = 'Google Ads'
    df['Campaign key'] = 'Google Ads:' + df['Campaign']
    if df.duplicated(['Campaign key','Reporting starts','Reporting ends']).any():
        raise ValueError('Duplicate Google campaign periods.')
    return df.sort_values(['Reporting starts','Campaign name'])


def outcome_summary(df):
    if df['Channel'].eq('Google Ads').all():
        conversions = float(df['Google conversions'].sum())
        return {'Outcome': 'Google conversions', 'Reported outcomes': conversions,
                'Outcome campaign spend (AUD)': float(df[COUNTS[0]].sum()),
                'Cost / outcome (AUD)': float(df[COUNTS[0]].sum()) / conversions if conversions else None}
    if 'Result indicator' in df:
        lead = df[df['Result indicator'].eq('actions:leadgen.other')]
        if not lead.empty:
            count = float(pd.to_numeric(lead['Results'], errors='raise').sum())
            spend = float(lead[COUNTS[0]].sum())
            return {'Outcome': 'META instant-form leads', 'Reported outcomes':count,
                    'Outcome campaign spend (AUD)':spend,
                    'Cost / outcome (AUD)':spend/count if count else None}
    return {'Outcome':'Not provided', 'Reported outcomes':None, 'Cost / outcome (AUD)':None}
