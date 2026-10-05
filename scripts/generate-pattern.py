"""Generate calendar art options and an exact date map. No Git writes."""
import argparse
import json
from datetime import date, timedelta
from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parents[1]
FONT = {
    'S': ['111','100','111','001','111'],
    'U': ['101','101','101','101','111'],
    'L': ['100','100','100','100','111'],
    'T': ['111','010','010','010','010'],
    'A': ['010','101','111','101','101'],
    'N': ['1001','1101','1011','1001','1001'],
    'K': ['101','101','110','101','101'],
    'M': ['1001','1111','1001','1001','1001'],
}
DENSE = {**FONT, 'N':['101','111','111','111','101'], 'M':['101','111','111','101','101']}

def bitmap(words, font, height=5):
    rows = [''] * 5
    for word_index, word in enumerate(words):
        if word_index:
            rows = [r + '000' for r in rows]
        for index, letter in enumerate(word):
            if index:
                rows = [r + '0' for r in rows]
            rows = [r + glyph for r, glyph in zip(rows, font[letter])]
    if height == 7:
        rows = [rows[i] for i in [0,1,1,2,3,3,4]]
    offset = (53 - len(rows[0])) // 2
    assert offset >= 0
    rows = ['0'*offset + r + '0'*(53-offset-len(r)) for r in rows]
    return ['0'*53] + rows + ['0'*53] if height==5 else rows

def calendar_start(year):
    jan = date(year,1,1)
    return jan - timedelta(days=(jan.weekday()+1)%7)

def mapping(rows, year):
    start = calendar_start(year)
    cells = []
    for row in range(7):
        for column in range(53):
            day = start + timedelta(days=column*7+row)
            if rows[row][column]=='1':
                if day.year != year:
                    raise ValueError('Artwork includes a cell outside the selected year')
                cells.append({'date':day.isoformat(),'column':column,'row':row,'commits':1})
    return sorted(cells,key=lambda c:c['date'])

def baseline():
    source = json.loads((ROOT/'design/baseline-2026.json').read_text(encoding='utf-8'))
    calendar = source['data']['user']['contributionsCollection']['contributionCalendar']
    return {d['date']:d['contributionCount'] for w in calendar['weeks'] for d in w['contributionDays'] if d['contributionCount']}

def render_svg(rows,year,today,title,mode='complete'):
    start=calendar_start(year)
    known=baseline() if year==2026 else {}
    size,gap,x0,y0=12,3,30,90
    pieces=[f'<svg xmlns="http://www.w3.org/2000/svg" width="850" height="270" viewBox="0 0 850 270"><title>{escape(title)}</title><rect width="850" height="270" rx="16" fill="#0D1117"/><g font-family="Segoe UI,Arial,sans-serif"><text x="30" y="35" font-size="20" font-weight="700" fill="#F0F6FC">{escape(title)}</text><text x="30" y="61" font-size="13" fill="#A0AEBD">53 weeks × 7 weekdays / {year} / one art commit per letter pixel</text>']
    for column in range(53):
        for row in range(7):
            day=start+timedelta(days=column*7+row)
            intended=rows[row][column]=='1'
            existing=known.get(day.isoformat(),0)>0
            pending=day>today
            fill='#161B22'
            stroke='none'
            if existing and day.year==year:
                fill='#216E39'
                stroke='#A0AEBD'
            if intended:
                fill='#39D353' if mode=='complete' or not pending else '#193725'
                stroke='none' if not pending or mode=='complete' else '#39D353'
            if day.year!=year: fill='#0D1117'
            pieces.append(f'<rect x="{x0+column*(size+gap)}" y="{y0+row*(size+gap)}" width="{size}" height="{size}" rx="2" fill="{fill}" stroke="{stroke}" stroke-width=".7"><title>{day.isoformat()} / art {int(intended)} / existing {known.get(day.isoformat(),0)} / {"pending" if pending and intended else "reachable"}</title></rect>')
    pieces.extend(['<text x="30" y="218" font-size="13" fill="#A0AEBD">Bright green: intended art • Gray outline: existing activity • Hollow green: future pixels</text>',f'<text x="30" y="246" font-size="12" fill="#A0AEBD">{escape("Completed target; contribution shades are illustrative, not guaranteed." if mode=="complete" else "Reachable through "+today.isoformat()+"; future cells are a plan, not contributions.")}</text></g></svg>'])
    return ''.join(pieces)+'\n'

def generate(year,today):
    options=[('A','SULTAN KASSAM / maximum readability',bitmap(['SULTAN','KASSAM'],FONT)),('B','SULTAN KASSAM / denser seven-row typography',bitmap(['SULTAN','KASSAM'],DENSE,7)),('C','SULTAN + SK / monogram-assisted alternative',bitmap(['SULTAN','SK'],FONT))]
    folder=ROOT/'design'; folder.mkdir(exist_ok=True)
    for code,title,rows in options:
        cells=mapping(rows,year)
        (folder/f'option-{code}.svg').write_text(render_svg(rows,year,today,title),encoding='utf-8')
        (folder/f'option-{code}.json').write_text(json.dumps({'option':code,'title':title,'rows':rows,'pixels':len(cells)},indent=2)+'\n',encoding='utf-8')
    rows=options[0][2];cells=mapping(rows,year)
    data={'username':'sultankassam','year':year,'text':'SULTAN KASSAM','option':'A','columns':53,'rowCount':7,'rowOrder':['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'],'calendarStart':calendar_start(year).isoformat(),'commitsPerPixel':1,'shadePolicy':'Visibility first. GitHub intensity is relative; no exact shade guarantee.','rows':rows,'pixels':cells}
    (folder/'sultan-kassam-grid.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    (folder/'preview.svg').write_text(render_svg(rows,year,today,'SULTAN KASSAM / selected design A'),encoding='utf-8')
    (folder/'preview-progress.svg').write_text(render_svg(rows,year,today,'SULTAN KASSAM / reachable + pending',mode='progress'),encoding='utf-8')
    (folder/'mapping.txt').write_text('\n'.join(rows)+'\n\n'+'\n'.join(f"{p['date']}  col={p['column']:02} row={p['row']}  commits=1  {'reachable' if date.fromisoformat(p['date'])<=today else 'pending'}" for p in cells)+'\n',encoding='utf-8')
    # Optional 2025 plan only. No commits are made by this generator.
    plan_2025={'year':2025,'text':'SULTAN KASSAM','selected':False,'rows':rows,'pixels':mapping(rows,2025),'note':'Optional plan only. Requires explicit user selection before applying.'}
    (folder/'optional-2025-plan.json').write_text(json.dumps(plan_2025,indent=2)+'\n',encoding='utf-8')
    reachable=[p for p in cells if date.fromisoformat(p['date'])<=today]
    pending=[p for p in cells if date.fromisoformat(p['date'])>today]
    print(json.dumps({'selected':'A','pixels':len(cells),'historical':len(reachable),'future':len(pending),'completion':cells[-1]['date']},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--year',type=int,default=2026);parser.add_argument('--today',type=date.fromisoformat,required=True)
    args=parser.parse_args();generate(args.year,args.today)
