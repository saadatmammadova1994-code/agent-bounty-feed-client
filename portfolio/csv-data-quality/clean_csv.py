#!/usr/bin/env python3
"""Rule-based CSV hygiene pilot, stdlib only. No network calls or guessed corrections.
Usage: python clean_csv.py input.csv --out-dir results
"""
import argparse, csv, re, json
from collections import Counter
from datetime import datetime
from pathlib import Path

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
COUNTRIES = {'us': 'United States', 'usa': 'United States', 'united states':'United States',
             'uk':'United Kingdom','gb':'United Kingdom','united kingdom':'United Kingdom',
             'az':'Azerbaijan', 'azerbaijan':'Azerbaijan', 'de':'Germany', 'germany':'Germany'}

def trim(s):
    return ' '.join(str(s or '').split())

def iso_date(s):
    s = trim(s)
    if not s: return '', None
    for fmt in ('%Y-%m-%d','%d.%m.%Y','%Y/%m/%d'):
        try: return datetime.strptime(s,fmt).date().isoformat(), None
        except ValueError: pass
    if '/' in s:
        parts=s.split('/')
        if len(parts)==3 and parts[0].isdigit() and parts[1].isdigit() and int(parts[0])<=12 and int(parts[1])<=12:
            return s,'ambiguous_date'
        for fmt in ('%d/%m/%Y','%m/%d/%Y'):
            try: return datetime.strptime(s,fmt).date().isoformat(), None
            except ValueError: pass
    return s,'unrecognized_date'

def clean_rows(rows, headers):
    out=[]; seen={}; exceptions=[]; actions=Counter()
    for position, source in enumerate(rows, start=2):
        r={k: trim(source.get(k,'')) for k in headers}
        issues=[]
        if 'email' in r:
            lowered=r['email'].lower()
            if lowered!=r['email']: actions['normalized_emails']+=1
            r['email']=lowered
            if not r['email']: issues.append('missing_email')
            elif not EMAIL_RE.fullmatch(r['email']): issues.append('invalid_email_syntax')
        if 'country' in r and r['country']:
            mapped=COUNTRIES.get(r['country'].lower())
            if mapped and mapped!=r['country']:
                r['country']=mapped; actions['standardized_countries']+=1
        if 'signup_date' in r:
            transformed, issue=iso_date(r['signup_date'])
            if transformed!=r['signup_date']: actions['standardized_dates']+=1
            r['signup_date']=transformed
            if issue: issues.append(issue)
        key=r.get('email','')
        if key and EMAIL_RE.fullmatch(key) and key in seen:
            existing=out[seen[key]]
            mismatched=[]
            for k in headers:
                if not existing[k] and r[k]:
                    existing[k]=r[k]; actions['filled_blank_fields_from_duplicate']+=1
                elif existing[k] and r[k] and existing[k]!=r[k]:
                    mismatched.append(k)
            actions['removed_exact_email_duplicates']+=1
            if mismatched:
                exceptions.append({'source_row':position,'issue':'duplicate_conflicting_fields:'+','.join(mismatched),'email':key,'action':'kept_first_nonempty_values; review conflict'})
            continue
        if key and EMAIL_RE.fullmatch(key): seen[key]=len(out)
        out.append(r)
        for issue in issues: exceptions.append({'source_row':position,'issue':issue,'email':key,'action':'left unchanged; manual review required'})
        if r != {k:source.get(k,'') for k in headers}: actions['rows_with_format_changes']+=1
    return out,exceptions,actions

def main():
    p=argparse.ArgumentParser(); p.add_argument('input'); p.add_argument('--out-dir',default='results'); a=p.parse_args()
    target=Path(a.out_dir); target.mkdir(parents=True,exist_ok=True)
    with open(a.input, newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f); headers=reader.fieldnames or []; rows=list(reader)
    if not headers or len(set(headers))!=len(headers): raise SystemExit('CSV must have distinct column headers')
    cleaned,issues,changes=clean_rows(rows,headers)
    with (target/'cleaned.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=headers); w.writeheader(); w.writerows(cleaned)
    with (target/'exceptions.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['source_row','issue','email','action']); w.writeheader(); w.writerows(issues)
    report={'input_rows':len(rows),'output_rows':len(cleaned),'flagged_issues':len(issues),
           'changes':dict(changes),'important_limitations':[
           'Email syntax checked only; mailbox deliverability not verified.',
           'Ambiguous dates retained for human review.',
           'Deduplication matches only exact valid normalized emails.',
           'Input is assumed authorized and free of sensitive data for this demonstration.']}
    (target/'qa_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__': main()
