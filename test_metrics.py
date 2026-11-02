import unittest
from pathlib import Path
from metrics import load_data, totals, previous_week, TEMPLATE_COLUMNS
import pandas as pd

class MetricsTest(unittest.TestCase):
    def setUp(self):
        self.df = load_data(next(Path(__file__).parent.glob('*.csv')).read_bytes())

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

if __name__ == '__main__':
    unittest.main()
