"""Append explicitly labeled art commits in this repository only. Never rewrite."""
import argparse
import json
import os
import subprocess
from datetime import date, datetime, time, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NAIROBI=timezone(timedelta(hours=3),'Africa/Nairobi')

def git(*args,env=None):
    return subprocess.check_output(['git',*args],cwd=ROOT,env=env,text=True,encoding='utf-8').strip()

def now():
    return datetime.now(timezone.utc)

def targets(grid,state,mode,today):
    painted=set(state['applied'])
    return [p for p in grid['pixels'] if p['date'] not in painted and date.fromisoformat(p['date'])<=today and (mode!='daily' or p['date']==today.isoformat())]

def load():
    grid=json.loads((ROOT/'design/sultan-kassam-grid.json').read_text(encoding='utf-8'))
    state=json.loads((ROOT/'state.json').read_text(encoding='utf-8'))
    if grid['username']!='sultankassam' or grid['year']!=2026 or state['repository']!='sultankassam/contribution-art':
        raise RuntimeError('Wrong identity, year or repository')
    return grid,state

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['historical','daily','catch-up'],default='daily')
    operation=parser.add_mutually_exclusive_group(required=True)
    operation.add_argument('--dry-run',action='store_true');operation.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    grid,state=load();today=now().astimezone(NAIROBI).date()
    due=targets(grid,state,args.mode,today)
    if args.dry_run:
        print(json.dumps({'mode':args.mode,'todayNairobi':today.isoformat(),'commitsToAdd':len(due),'dates':[p['date'] for p in due]},indent=2));return
    if Path(git('rev-parse','--show-toplevel')).resolve()!=ROOT:
        raise RuntimeError('Refusing to write outside the dedicated repository')
    if git('branch','--show-current')!='main':raise RuntimeError('Art must be on main')
    if git('status','--porcelain'):raise RuntimeError('Working tree must be clean')
    if 'origin' in git('remote').splitlines():
        remote=git('remote','get-url','origin').removesuffix('.git')
        if remote not in ['https://github.com/sultankassam/contribution-art','git@github.com:sultankassam/contribution-art']:
            raise RuntimeError('Wrong remote repository')
    email=git('config','user.email')
    if not email or email!=os.environ.get('ART_AUTHOR_EMAIL',email):raise RuntimeError('Author address mismatch')
    messages=git('log','--format=%s').splitlines()
    existing={m.split()[2] for m in messages if m.startswith('art: pixel ')}
    if existing!=set(state['applied']):raise RuntimeError('History and state differ; investigate rather than repaint')
    added=0
    for pixel in due:
        day=date.fromisoformat(pixel['date'])
        instant=now()
        stamp=min(datetime.combine(day,time(9),tzinfo=NAIROBI),instant.astimezone(NAIROBI))
        # 09:00 Nairobi = 06:00 UTC. If dispatched before the UTC day exists, wait.
        if stamp.astimezone(timezone.utc).date()!=day:
            print('Today pixel deferred until the same UTC calendar date exists.');continue
        if stamp>instant or day>instant.astimezone(NAIROBI).date():raise RuntimeError('Future timestamp refused')
        state['applied'][pixel['date']]={'commits':1,'createdAtUTC':instant.isoformat()}
        state_file=ROOT/'state.json'
        state_file.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8',newline='\n')
        environment=os.environ.copy()
        environment.update({'GIT_AUTHOR_DATE':stamp.isoformat(),'GIT_COMMITTER_DATE':instant.isoformat()})
        try:
            git('add','--','state.json')
            git('commit','--quiet','-m',f"art: pixel {pixel['date']} intensity-1",env=environment)
        except Exception:
            # Restore only this generator-owned state/index entry; no history reset.
            git('restore','--source=HEAD','--staged','--worktree','--','state.json')
            raise
        added+=1
    print(json.dumps({'mode':args.mode,'artCommitsAdded':added,'totalPainted':len(state['applied'])}))

if __name__=='__main__':main()
