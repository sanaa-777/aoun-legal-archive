#!/usr/bin/env python3
"""Regression checks for the generated legal archive index and homepage."""
import json
import re
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'AOUN_LEGAL_ARCHIVE'

class LegalIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads((ROOT / 'docs/assets/legal_docs.json').read_text(encoding='utf-8'))
        cls.html = (ROOT / 'docs/index.html').read_text(encoding='utf-8')

    def test_counts_match_source_files(self):
        sources = [
            ('01_القوانين/law_dataset.json', 'قوانين'),
            ('02_اللوائح_والقرارات/regulation_dataset.json', 'لوائح وقرارات'),
            ('04_التعاميم/circular_dataset.json', 'تعاميم'),
            ('05_الادلة_التطبيقية/guide_dataset.json', 'أدلة تطبيقية'),
        ]
        expected = Counter()
        for path, category in sources:
            data = json.loads((ARCHIVE / '02_المكتبة_القانونية' / path).read_text(encoding='utf-8'))
            expected[category] += len(data)
        articles = json.loads((ARCHIVE / '03_المقالات_القانونية/المقالات_كاملة_2915.json').read_text(encoding='utf-8'))
        expected['مقالات قانونية'] = len(articles)
        expected['نصوص محلية'] = 1
        expected['نماذج وعقود'] = 5
        self.assertEqual(Counter({k: sum(r['category'] == k for r in self.records) for k in expected}), expected)
        self.assertEqual(len(self.records), sum(expected.values()))

    def test_unique_ids_normalized_years_and_local_links(self):
        ids = [record['id'] for record in self.records]
        self.assertEqual(len(ids), len(set(ids)))
        for record in self.records:
            self.assertIn('localTextAvailable', record)
            self.assertNotIn('branch', record)
            self.assertIn('scope', record)
            self.assertEqual(record['localTextAvailable'], bool(record['localUrl']))
            if record['year'] is not None:
                self.assertIsInstance(record['year'], str)
                self.assertEqual(record['year'], record['year'].strip())
            if record['localUrl']:
                self.assertTrue((ROOT / 'docs' / record['localUrl']).is_file(), record['localUrl'])
            if record['url']:
                self.assertRegex(record['url'], r'^https://www\.awnlegal\.com/')

    def test_page_has_single_dynamic_category_container(self):
        self.assertEqual(self.html.count('id="categoryCards"'), 1)
        self.assertIn("fetch('assets/legal_docs.json')", self.html)
        self.assertIn('data-show-more', self.html)
        self.assertIn('statGroupCount', self.html)
        self.assertIn('categoryPills.innerHTML', self.html)

    def test_removed_unavailable_or_unverified_actions(self):
        for phrase in ('تحميل PDF', 'نسخ الاقتباس الرسمي', 'إرسال طلب الإدراج', 'تم استلام طلب', 'نص تجريبي', '§'):
            self.assertNotIn(phrase, self.html)
        self.assertNotIn('requestForm', self.html)

if __name__ == '__main__':
    unittest.main(verbosity=2)
