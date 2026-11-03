import unittest
from pathlib import Path
from metrics import load_data, totals, previous_week, TEMPLATE_COLUMNS, outcome_summary
import pandas as pd

class MetricsTest(unittest.TestCase):
    def setUp(self):
        if not (Path(__file__).parent / 'JAC-Motors-Campaigns-29-Sep-2026-28-Oct-2026.csv').exists():
            self.skipTest('Local source CSV is intentionally not committed')
        self.df = load_data((Path(__file__).parent / 'JAC-Motors-Campaigns-29-Sep-2026-28-Oct-2026.csv').read_bytes())

    def test_source_reconciliation(self):
        self.assertEqual(len(self.df), 5)
        m = totals(self.df)
        self.assertAlmostEqual(m['Spend (AUD)'], 1133.57)
        self.assertEqual(m['Link clicks'], 2585)
        self.assertEqual(m['Landing page views'], 2291)
        self.assertAlmostEqual(m['CPC (AUD)'], 1133.57/2585)

    def test_comparable_week(self):
        current = self.df[self.df['Reporting starts'].dt.day == 20]
        self.assertAlmostEqual(previous_week(self.df, current)['Spend (AUD)'],478.97)
        partial = self.df[self.df['Reporting starts'].dt.day == 27]
        self.assertIsNone(previous_week(self.df, partial))
        self.assertIsNone(previous_week(self.df, self.df))

    def test_zero_and_duplicates(self):
        zero = self.df[self.df['Reporting starts'].dt.day == 29]
        self.assertIsNone(totals(zero)['CPC (AUD)'])
        with self.assertRaisesRegex(ValueError, 'Overlapping'):
            load_data(self.df.iloc[[0,0]].to_csv(index=False).encode())

    def test_daily_cross_channel_template(self):
        rows = []
        for date in pd.date_range('2026-10-01', periods=14):
            for channel in ['META', 'TikTok', 'SEM']:
                rows.append([date.strftime('%Y-%m-%d'), channel, '001', 'Shared name', 'AUD',
                             'Australia/Sydney', 10, 1000, 20, 15, '', '', '', ''])
        raw = pd.DataFrame(rows, columns=TEMPLATE_COLUMNS)
        daily = load_data(raw.to_csv(index=False).encode())
        self.assertEqual(daily['Campaign key'].nunique(), 3)
        self.assertEqual(daily['campaign_id'].iloc[0], '001')
        current = daily[daily['Reporting starts'] >= '2026-10-08']
        self.assertEqual(previous_week(daily, current)['Spend (AUD)'], 210)
        self.assertIsNone(previous_week(daily.iloc[1:], current))
        raw.loc[0, 'spend'] = None
        with self.assertRaisesRegex(ValueError, 'cannot be blank'):
            load_data(raw.to_csv(index=False).encode())

class NewReportsTest(unittest.TestCase):
    def test_google_totals_excluded(self):
        path = Path(__file__).parent / 'Google Report - Oct.csv'
        if not path.exists(): self.skipTest('Local source report')
        df = load_data(path.read_bytes())
        self.assertEqual(len(df), 84)
        self.assertAlmostEqual(totals(df)['Spend (AUD)'],7421)
        self.assertEqual(totals(df)['Link clicks'],7885)
        self.assertIsNone(totals(df)['Landing page views'])
        self.assertAlmostEqual(outcome_summary(df)['Reported outcomes'],38.99)
        self.assertIsNone(previous_week(df,df))

    def test_meta_outcome_separation(self):
        path = Path(__file__).parent / 'Meta -Campaigns-3-Oct-2026-1-Nov-2026.csv'
        if not path.exists(): self.skipTest('Local source report')
        df = load_data(path.read_bytes())
        self.assertEqual(len(df),15)
        self.assertAlmostEqual(totals(df)['Spend (AUD)'],3219.8)
        outcome = outcome_summary(df)
        self.assertEqual(outcome['Reported outcomes'],35)
        self.assertAlmostEqual(outcome['Outcome campaign spend (AUD)'],920.88)
        week = df[df['Reporting starts']==pd.Timestamp('2026-10-24')]
        self.assertAlmostEqual(previous_week(df,week)['Spend (AUD)'],518.33)

if __name__ == '__main__':
    unittest.main()
