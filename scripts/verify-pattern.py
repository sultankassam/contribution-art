"""Verify grid/calendar mapping, state/history agreement and date safety."""
import argparse
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import date,datetime,timedelta,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def run(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True,encoding='utf-8').strip()

def verify(history=True):
    grid=json.loads((ROOT/'design/sultan-kassam-grid.json').read_text(encoding='utf-8'))
    state=json.loads((ROOT/'state.json').read_text(encoding='utf-8'))
    now=datetime.now(timezone.utc);today=now.astimezone(timezone(timedelta(hours=3))).date()
    assert grid['username']=='sultankassam' and grid['year']==2026
    assert len(grid['rows'])==7 and all(len(r)==53 and set(r)<=set('01') for r in grid['rows'])
    start=date.fromisoformat(grid['calendarStart']);intended={p['date']:p for p in grid['pixels']}
    assert len(intended)==len(grid['pixels'])==sum(r.count('1') for r in grid['rows'])
    for day,p in intended.items():
        assert start+timedelta(days=p['column']*7+p['row'])==date.fromisoformat(day)
        assert date.fromisoformat(day).year==2026 and p['commits']==1
        assert grid['rows'][p['row']][p['column']]=='1'
    for day,entry in state['applied'].items():
        assert day in intended and date.fromisoformat(day)<=today and entry['commits']==1
        assert datetime.fromisoformat(entry['createdAtUTC'])<=now
    for file in (ROOT/'design').glob('*.svg'):ET.parse(file)
    for file in ROOT.rglob('*'):
        if file.is_file() and '.git' not in file.parts and file.suffix in ['.py','.json','.md','.svg','.yml','.txt']:
            content=file.read_text(encoding='utf-8')
            assert not re.search(r'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9]{24,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----',content),f'Credential pattern: {file}'
    if history:
        assert Path(run('rev-parse','--show-toplevel')).resolve()==ROOT
        email=run('config','user.email');painted=[]
        for commit in run('log','--format=%H%x09%aI%x09%cI%x09%ae%x09%s').splitlines():
            sha,author,committer,address,message=commit.split('\t',4)
            assert datetime.fromisoformat(author)<=now and datetime.fromisoformat(committer)<=now
            assert address==email
            if message.startswith('art: pixel '):
                matched=re.fullmatch(r'art: pixel (\d{4}-\d{2}-\d{2}) intensity-1',message)
                assert matched
                day=matched[1];assert day in intended and datetime.fromisoformat(author).date().isoformat()==day
                assert datetime.fromisoformat(author).astimezone(timezone.utc).date().isoformat()==day
                changed=run('diff-tree','--no-commit-id','--name-only','-r',sha).splitlines()
                assert changed==['state.json']
                painted.append(day)
        assert len(painted)==len(set(painted)), 'Duplicate pixel commits'
        assert set(painted)==set(state['applied']), 'State/history mismatch'
    applied=len(state['applied']);pending=[d for d in intended if date.fromisoformat(d)>today]
    missed=[d for d in intended if date.fromisoformat(d)<=today and d not in state['applied']]
    result={'grid':'53 x 7','intendedPixels':len(intended),'applied':applied,'futurePending':len(pending),'missedReachable':len(missed),'completion':max(intended),'nextPixel':min(pending) if pending else None}
    print(json.dumps(result,indent=2));return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--no-history',action='store_true');args=parser.parse_args();verify(not args.no_history)
