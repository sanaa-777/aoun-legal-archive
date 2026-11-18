#!/usr/bin/env python3
"""Build the searchable index from checked-in archive metadata only."""
from __future__ import annotations
import json
import re
from html import unescape
from pathlib import Path
from collections import Counter

REPO = Path(__file__).resolve().parents[1]
ARCHIVE = REPO / 'AOUN_LEGAL_ARCHIVE'
LIBRARY = ARCHIVE / '02_المكتبة_القانونية'
OUTPUT = REPO / 'docs' / 'assets' / 'legal_docs.json'
SOURCES = [
    ('01_القوانين/law_dataset.json', 'قوانين', 'قانون'),
    ('02_اللوائح_والقرارات/regulation_dataset.json', 'لوائح وقرارات', 'لائحة / قرار'),
    ('04_التعاميم/circular_dataset.json', 'تعاميم', 'تعميم'),
    ('05_الادلة_التطبيقية/guide_dataset.json', 'أدلة تطبيقية', 'دليل'),
]
# These identifiers are verified by title and reference in the checked-in law dataset.
LOCAL_STATUTES = {
    879: ('قانون الأحوال الشخصية', 'laws/قانون_الأحوال_الشخصية_20_1992_وتعديلاته.html'),
    935: ('قانون العمل', 'laws/قانون_العمل_5_1995.html'),
    1073: ('المرافعات والتنفيذ المدني- صنعاء', 'laws/قانون_المرافعات_والتنفيذ_المدني_40_2002.html'),
}

def load_json(path: Path):
    with path.open(encoding='utf-8') as source:
        return json.load(source)

def clean_year(value):
    """Keep only years explicitly present in source fields, as normalized text."""
    if value is None or value == '':
        return None
    return str(value).strip() or None

records = []
for relative, group, label in SOURCES:
    for row in load_json(LIBRARY / relative):
        topics = row.get('topics') or []
        authority_topics = [
            topic.get('name_ar') for topic in topics
            if topic.get('type') == 'circular_authority' and topic.get('name_ar')
        ]
        issuer = row.get('authority_category') or row.get('issuing_person') or (authority_topics[0] if authority_topics else None)
        scope = row.get('applicability_scope')
        record_id = row.get('id')
        local_match = LOCAL_STATUTES.get(record_id) if row.get('source_type') == 'law' else None
        if local_match and row.get('title') != local_match[0]:
            raise ValueError(f"Local statute ID {record_id} no longer matches its verified catalog title")
        local_url = local_match[1] if local_match else None
        if local_url and not (REPO / 'docs' / local_url).is_file():
            raise FileNotFoundError(f'Local statute link does not exist: {local_url}')
        records.append({
            'id': f"{row.get('source_type', 'record')}-{record_id}",
            'title': row.get('title') or 'بدون عنوان في السجل',
            'ref': row.get('reference_code') or None,
            'category': group,
            'kind': label,
            'year': clean_year(row.get('issued_year') or row.get('circular_year')),
            'issuer': issuer or None,
            'scope': scope or None,
            'status': row.get('legal_status_label') or None,
            'topics': [topic.get('name_ar') for topic in topics if topic.get('name_ar')],
            'localTextAvailable': bool(local_url),
            'url': f"https://www.awnlegal.com/library/{record_id}",
            'localUrl': local_url,
            'description': 'توجد صفحة نصية محلية مرتبطة بهذا السجل.' if local_url else 'بيانات فهرسة محفوظة في المستودع؛ المتن الكامل غير محفوظ ضمن ملفات هذه النسخة.',
        })

# Indexed articles: preserve the archived web URL and publication year; do not invent a citation.
article_file = ARCHIVE / '03_المقالات_القانونية' / 'المقالات_كاملة_2915.json'
for row in load_json(article_file):
    published = row.get('published_at') or ''
    records.append({
        'id': f"article-{row['id']}",
        'title': row.get('title') or 'مقال بلا عنوان في السجل',
        'ref': row.get('reference_code') or None,
        'category': 'مقالات قانونية',
        'kind': row.get('listing_type_label') or 'مقال',
        'year': clean_year(published[:4] if len(published) >= 4 else None),
        'issuer': row.get('author_name') or None,
        'scope': None,
        'status': 'مقال مفهرس',
        'topics': [],
        'localTextAvailable': False,
        'url': row.get('web_url') or None,
        'localUrl': None,
        'description': row.get('description') or 'بيانات المقال محفوظة في الفهرس؛ المتن الكامل غير موجود في ملف المقالات.',
    })

# The local civil-code page exists, but has no matching catalog row; identify it separately.
civil_path = 'laws/القانون_المدني_14_2002.html'
if not (REPO / 'docs' / civil_path).is_file():
    raise FileNotFoundError(f'Local statute link does not exist: {civil_path}')
records.append({
    'id': 'local-statute-civil-code-14-2002',
    'title': 'القانون المدني',
    'ref': 'قانون رقم (14) لسنة 2002م',
    'category': 'نصوص محلية',
    'kind': 'نص محفوظ محلياً',
    'year': '2002',
    'issuer': None,
    'scope': None,
    'status': None,
    'topics': [],
    'localTextAvailable': True,
    'url': None,
    'localUrl': civil_path,
    'description': 'نص محفوظ في ملفات الموقع المحلية؛ تحقّق من النسخة ومصدرها قبل الاستناد إليها.',
})

# Index the five existing templates by their actual HTML page titles.
for number in range(1, 6):
    local_url = f'contracts/contract_{number}.html'
    local_path = REPO / 'docs' / local_url
    if not local_path.is_file():
        raise FileNotFoundError(f'Local template link does not exist: {local_url}')
    title_match = re.search(r'<title[^>]*>(.*?)</title>', local_path.read_text(encoding='utf-8'), re.I | re.S)
    if not title_match or not unescape(title_match.group(1)).strip():
        raise ValueError(f'Could not read template title from {local_url}')
    title = unescape(title_match.group(1)).strip()
    records.append({
        'id': f'template-{number}', 'title': title, 'ref': None,
        'category': 'نماذج وعقود', 'kind': 'نموذج محفوظ محلياً', 'year': None,
        'issuer': None, 'scope': None, 'status': None, 'topics': ['نماذج', 'عقود'],
        'localTextAvailable': True, 'url': None, 'localUrl': local_url,
        'description': 'نموذج موجود ضمن ملفات الموقع؛ ليس نصاً تشريعياً ولا يُفترض أنه صالح لكل حالة.',
    })

# Validate stable identifiers, categories, years, and every local link before writing.
ids = [record['id'] for record in records]
if len(ids) != len(set(ids)):
    raise ValueError('Duplicate record IDs in generated index')
for record in records:
    if record['year'] is not None and not isinstance(record['year'], str):
        raise TypeError(f"Year is not normalized for {record['id']}")
    if record['localUrl'] and not (REPO / 'docs' / record['localUrl']).is_file():
        raise FileNotFoundError(record['localUrl'])
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(records, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
print(f'Wrote {len(records)} records to {OUTPUT.relative_to(REPO)}')
for category, count in sorted(Counter(record['category'] for record in records).items()):
    print(f'{category}: {count}')
