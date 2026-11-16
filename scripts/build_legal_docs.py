#!/usr/bin/env python3
"""Build the public searchable index from the checked-in archive metadata."""
import json, os, re, unicodedata
ROOT='AOUN_LEGAL_ARCHIVE'
LIB=os.path.join(ROOT,'02_المكتبة_القانونية')
SOURCES=[('01_القوانين/law_dataset.json','قوانين','قانون'),('02_اللوائح_والقرارات/regulation_dataset.json','لوائح وقرارات','لائحة / قرار'),('04_التعاميم/circular_dataset.json','تعاميم','تعميم'),('05_الادلة_التطبيقية/guide_dataset.json','أدلة تطبيقية','دليل')]
def norm(s):
 return re.sub(r'[_\s]+',' ',unicodedata.normalize('NFKC',s or '')).strip().lower()
records=[]
for rel,group,label in SOURCES:
 for row in json.load(open(os.path.join(LIB,rel),encoding='utf-8')):
  topics=row.get('topics') or []
  branch=(row.get('authority_category') or row.get('issuing_person') or '')
  if not branch and topics: branch='، '.join(t.get('name_ar','') for t in topics if t.get('name_ar'))
  rec = {'id': f"{row.get('source_type', 'doc')}-{row['id']}", 'title': row.get('title') or 'وثيقة بدون عنوان', 'ref': row.get('reference_code') or 'غير محدد', 'category': group, 'kind': label, 'year': row.get('issued_year') or row.get('circular_year') or None, 'issuer': row.get('authority_category') or row.get('issuing_person') or 'غير محدد في الفهرس', 'branch': branch or 'غير مصنف', 'status': row.get('legal_status_label') or 'غير محدد', 'topics': [t.get('name_ar') for t in topics if t.get('name_ar')], 'locked': bool(row.get('content_locked', True)), 'url': f"https://www.awnlegal.com/library/{row['id']}", 'localUrl': None, 'description': 'بيانات فهرسة محفوظة في الأرشيف. النص الكامل غير متاح ضمن نسخة المستودع.'}
  records.append(rec)
# Match the few locally archived statute pages through the legacy search index.
idx=json.load(open('docs/assets/search_index.json',encoding='utf-8'))
local={norm(x.get('t')):x.get('u') for x in idx if x.get('u')}
for rec in records:
 u=local.get(norm(rec['title']))
 if u: rec['localUrl']=u
# Articles are included as searchable archive records; full bodies were not in the extracted archive.
article_path=os.path.join(ROOT,'03_المقالات_القانونية','المقالات_كاملة_2915.json')
for row in json.load(open(article_path,encoding='utf-8')):
 records.append({'id':f"article-{row['id']}",'title':row.get('title') or 'مقال قانوني','ref':row.get('listing_type_label') or 'مقال قانوني','category':'مقالات قانونية','kind':row.get('listing_type_label') or 'مقال','year':(row.get('published_at') or '')[:4] or None,'issuer':row.get('author_name') or 'غير محدد','branch':row.get('author_name') or 'مقالات قانونية','status':'مقال مفهرس','topics':[],'locked':bool(row.get('content_locked',True)),'url':row.get('web_url') or 'https://www.awnlegal.com','localUrl':None,'description':row.get('description') or 'بيانات المقال متاحة في الفهرس؛ متن المقال غير متضمن في نسخة المستودع.'})
# These are the repository's editable templates, not legislative instruments.
for n,title in enumerate(['عقد إيجار عقار','عقد بيع وشراء','عقد عمل فردي','وكالة عامة وخاصة','عقد شراكة تجارية'],1):
 records.append({'id':f'template-{n}','title':title,'ref':f'نموذج رقم {n}','category':'نماذج وعقود','kind':'نموذج إرشادي','year':None,'issuer':'أرشيف المستودع','branch':'نماذج العقود','status':'نموذج قابل للتحرير','topics':['نماذج','عقود'],'locked':False,'url':f'contracts/contract_{n}.html','localUrl':f'contracts/contract_{n}.html','description':'قالب استرشادي قابل للتعديل، وليس نصاً تشريعياً.'})
out='docs/assets/legal_docs.json'
with open(out,'w',encoding='utf-8') as f: json.dump(records,f,ensure_ascii=False,separators=(',',':'))
print(f'Wrote {len(records)} records to {out}; categories:')
from collections import Counter
for k,v in Counter(r['category'] for r in records).items(): print(f'  {k}: {v}')
