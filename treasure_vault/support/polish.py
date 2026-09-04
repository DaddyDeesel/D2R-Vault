import base64
import collections
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3

P=Path(os.environ['D2R_OUTPUT_DIR'])/'support' if os.environ.get('D2R_OUTPUT_DIR') else Path(__file__).resolve().parent
ROOT=P.parent
read=lambda name:list(csv.DictReader((P/f'current-{name}.txt').open(encoding='utf-8-sig'),delimiter='\t'))
tables=json.loads((P/'tables.json').read_text())
source=json.loads((P/'source-records.json').read_text())
sorc_accounts=set()
account_names={a:f'Account {i+1}' for i,a in enumerate(sorted({r['account_id'] for r in source}))}
account_label=lambda r:account_names[r['account_id']]
owner_key=lambda r:hashlib.sha256((r['account_id']+'|'+r['char_name']).encode()).hexdigest()[:16]
account_key=lambda r:hashlib.sha256(r['account_id'].encode()).hexdigest()[:16]
def identity_signature(r):
    fields={k:r[k] for k in ['account_id','item_name','base_name','item_type','quality','unique_set_id','identified','ethereal','is_runeword','runeword_name']}
    for k in ['stats_json','skills_json','socketed_runes']:fields[k]=json.loads(r[k] or ('[]' if k=='socketed_runes' else '{}'))
    return hashlib.sha256(json.dumps(fields,sort_keys=True).encode()).hexdigest()
key=lambda r:'I-'+hashlib.sha256('|'.join(map(str,(r['account_id'],r['char_name'],r['unit_id']))).encode()).hexdigest()[:8].upper()
raw_by_ref={key(r):r for r in source}
master=tables['organized_inventory.csv'][1:]
post=tables['post_inventory.csv'][1:]
unique={r['*ID']:r for r in read('uniqueitems') if r['*ID']}
sets={r['*ID']:r for r in read('setitems') if r['*ID']}
runewords=read('runes')
properties={r['code']:r for r in read('properties')}
skills={int(r['*Id']):r['skill'] for r in read('skills') if r['*Id'].isdigit()}
skillids={r['skill'].lower():int(r['*Id']) for r in read('skills') if r['*Id'].isdigit()}
classes=['Amazon','Sorceress','Necromancer','Paladin','Barbarian','Druid','Assassin','Warlock']
tabs={0:'Bow',1:'Passive',2:'Javelin',8:'Fire',9:'Lightning',10:'Cold',16:'Curses',17:'Poison & Bone',18:'Necro Summon',24:'Pally Combat',25:'Offensive Auras',26:'Defensive Auras',32:'Barb Combat',33:'Masteries',34:'Warcries',40:'Druid Summon',41:'Shapeshifting',42:'Elemental',48:'Traps',49:'Shadow',50:'Martial Arts',56:'Demon',57:'Eldritch',58:'Chaos'}
runes=['El','Eld','Tir','Nef','Eth','Ith','Tal','Ral','Ort','Thul','Amn','Sol','Shael','Dol','Hel','Io','Lum','Ko','Fal','Lem','Pul','Um','Mal','Ist','Gul','Vex','Ohm','Lo','Sur','Ber','Jah','Cham','Zod']
gemtypes=['Amethyst','Diamond','Emerald','Ruby','Sapphire','Skull','Topaz']
tiers=['Chipped','Flawed','','Flawless','Perfect']
categories=list(dict.fromkeys(r[1] for r in post))
normalize=lambda value:re.sub('[^a-z0-9]','',value.lower())
base_code_by_name={normalize(r['name']):r['code'] for table in ['armor','weapons','misc'] for r in read(table) if r.get('name') and r.get('code')}
unique_by_code=collections.defaultdict(list)
for definition in unique.values():
    if definition.get('code') and definition.get('index') and not definition.get('disabled'): unique_by_code[definition['code']].append(definition)
def unique_definition(r):
    exact=unique.get(str(r.get('unique_set_id') or ''))
    if exact:return exact
    if r.get('quality')!=7 or r.get('identified'):return None
    matches=unique_by_code.get(base_code_by_name.get(normalize(r.get('base_name','')),''),[])
    return matches[0] if len(matches)==1 else None
unidentified_names={}
for row in post:
    src=raw_by_ref.get(row[13].split('; ')[0]);definition=unique_definition(src) if src else None
    if definition:
        unidentified_names[row[0]]=definition['index'];row[2]=definition['index']+' (Unid)'
def sorting(row):
    cat,name=row[1],row[2]
    if cat=='Runes': return categories.index(cat),runes.index(name.replace(' Rune','')),0,''
    if cat=='Gems':
        gem=next(g for g in gemtypes if name.endswith(g))
        tier=name[:-len(gem)].strip()
        return categories.index(cat),gemtypes.index(gem),tiers.index(tier),''
    return categories.index(cat),0,0,name.lower()
post.sort(key=sorting)

# Ordinary scalar rolls, read only when the item's definition has a min/max range.
short={'dmg%':('17','ED%'),'ac%':('16','EDef%'),'mag%':('80','MF'),'gold%':('79','GF'),'lifesteal':('60','LL'),'manasteal':('62','ML'),'str':('0','str'),'dex':('2','dex'),'vit':('3','vit'),'enr':('1','ene'),'hp':('7','life'),'mana':('9','mana'),'att':('19','AR'),'att%':('119','AR%'),'res-fire':('39','fire res'),'res-cold':('43','cold res'),'res-ltng':('41','light res'),'res-pois':('45','poison res'),'red-dmg%':('36','DR'),'red-mag':('35','MDR'),'red-dmg':('34','DR flat'),'abs-fire':('143','fire absorb'),'abs-ltng':('145','light absorb'),'abs-cold':('149','cold absorb'),'abs-fire%':('142','fire absorb%'),'abs-cold%':('148','cold absorb%'),'abs-ltng%':('144','light absorb%'),'regen':('74','replenish life'),'regen-mana':('27','mana regen'),'heal-kill':('86','LAEK'),'mana-kill':('138','MAEK'),'cheap':('87','vendor discount'),'addxp':('85','XP'),'cast1':('105','FCR'),'cast2':('105','FCR'),'cast3':('105','FCR'),'dmg-demon':('121','demon ED'),'dmg-undead':('122','undead ED'),'extra-fire':('329','fire dmg'),'extra-ltng':('330','light dmg'),'extra-cold':('331','cold dmg'),'extra-pois':('332','poison dmg'),'extra-mag':('357','magic dmg'),'pierce-fire':('333','enemy fire res'),'pierce-ltng':('334','enemy light res'),'pierce-cold':('335','enemy cold res'),'pierce-pois':('336','enemy poison res'),'pierce-mag':('358','enemy magic res'),'allskills':('127','all skills'),'hp%':('76','life%'),'mana%':('77','mana%'),'balance1':('99','FHR'),'move1':('96','FRW'),'crush':('136','CB')}
percent={'MF','GF','LL','ML','fire res','cold res','light res','poison res','DR','vendor discount','XP','FCR','demon ED','undead ED','fire dmg','light dmg','cold dmg','poison dmg','magic dmg','enemy fire res','enemy light res','enemy cold res','enemy poison res','enemy magic res','FHR','FRW','CB','mana regen'}
short.update({'abs-mag':('147','magic absorb'),'res-mag':('37','magic res')})
percent.add('magic res')
armor_types={'Body Armor','Boots','Gloves','Helm','Belt','Shield','Auric Shield','Circlet','Druid Pelt','Primal Helm','Head','Grim'}
issues={}
def compact_rolls(r):
    st=json.loads(r['stats_json'] or '{}'); sk=json.loads(r['skills_json'] or '{}')
    definition=None
    if r['is_runeword']:
        matches=[d for d in runewords if normalize(d['*Rune Name'])==normalize(r['runeword_name'] or r['item_name'])]
        if matches: definition=matches[0]
    else: definition=unique_definition(r) if r['quality']==7 else sets.get(str(r['unique_set_id']))
    out=[]; missing=[]
    def add(v):
        if v not in out: out.append(v)
    if not definition:
        issues[key(r)]=['Item definition unavailable: variable rolls omitted']
        return ''
    if r['quality']==7 or r['quality']==5:
        specs=[(definition.get(f'prop{i}'),definition.get(f'par{i}'),definition.get(f'min{i}'),definition.get(f'max{i}')) for i in range(1,13)]
    else:
        specs=[(definition.get(f'T1Code{i}'),definition.get(f'T1Param{i}'),definition.get(f'T1Min{i}'),definition.get(f'T1Max{i}')) for i in range(1,8)]
    # Class identity is essential for Torches, even though the +3 itself is fixed.
    if r['item_name']=='Hellfire Torch':
        for cls,val in sorted(set(tuple(x) for x in sk.get('class_skills',[]))): add(f'{classes[cls]}')
    for prop,param,lo,hi in specs:
        if not prop or not lo or not hi or lo==hi: continue
        if prop in short:
            stat,label=short[prop]
            if stat in st:
                val=st[stat]
                # Store elemental pierce as a reduction; retain signs for resistances.
                sign='-' if label.startswith('enemy ') and val>0 else ''
                add(f'{sign}{val}{"%" if label in percent or label.endswith("%") else ""} {label.rstrip("%")}')
            else: missing.append(prop)
        elif prop=='res-all':
            vals=[st.get(s) for s in ['39','41','43','45']]
            if all(v is not None for v in vals):
                if len(set(vals))==1: add(f'{vals[0]} all res')
                else: add(f'{"/".join(map(str,vals))} res (F/L/C/P)')
            else: missing.append(prop)
        elif prop=='all-stats':
            vals=[st.get(s) for s in ['0','1','2','3']]
            if None not in vals and len(set(vals))==1: add(f'{vals[0]} stats')
            else: missing.append(prop)
        elif prop in {'skill','oskill','skilltab','aura','ama','sor','nec','pal','bar','dru','ass','war'}:
            kind={'skill':'single_skills','oskill':'non_class_skills','skilltab':'skill_tabs','aura':'item_auras'}.get(prop,'class_skills')
            sid=int(param) if param and param.isdigit() else skillids.get((param or '').lower())
            if kind=='skill_tabs' and sid is not None: sid=(sid//3)*8+sid%3
            if kind=='class_skills': sid={'ama':0,'sor':1,'nec':2,'pal':3,'bar':4,'dru':5,'ass':6,'war':7}[prop]
            entries=[(s,v) for s,v in sk.get(kind,[]) if s==sid]
            for s,v in sorted(set(entries)):
                name=tabs.get(s,f'tree {s}') if kind=='skill_tabs' else classes[s] if kind=='class_skills' else skills.get(s,f'skill {s}')
                add(f'Lv{v} {name}' if kind=='item_auras' else f'+{v} {name}')
            if not entries: missing.append(f'{prop}:{param}')
        elif prop=='sock': pass # Socket total is displayed separately.
        elif prop in {'ac','dmg-min','dmg-max','fire-min','fire-max','cold-min','cold-max','ltng-min','ltng-max'}:
            if prop=='ac' and '31' in st: pass # Show observed total defense below.
            else: missing.append(prop)
        # Min/max on damage pairs and procs describes fixed endpoints, not variable rolls.
    if r['item_type'] in armor_types and '31' in st: add(f'{st["31"]} def')
    if missing: issues[key(r)]=['Variable roll not recoverable from snapshot: '+', '.join(missing)]
    out.sort(key=lambda s: 0 if 'FCR' in s else 1 if s.startswith('+') or s.startswith('Lv') else 9 if s.endswith(' def') else 5)
    return ' / '.join(out)

def compact_other(text):
    replacements={'All resistances: ':'All res ','Strength: ':'str ','Energy: ':'ene ','Dexterity: ':'dex ','Vitality: ':'vit ','Life: ':'life ','Mana: ':'mana ','Attack rating: ':'AR ','Physical damage (stored): ':'phys ','Defense (stored): ':'def ','Fire resistance %: ':'fire res ','Lightning resistance %: ':'light res ','Cold resistance %: ':'cold res ','Poison resistance %: ':'poison res ','IAS %: ':'IAS ','FCR %: ':'FCR ','FHR %: ':'FHR ','FRW %: ':'FRW ','Magic find %: ':'MF ','Extra gold %: ':'GF ','All skills: ':'all skills ','Life stolen per hit %: ':'LL ','Mana stolen per hit %: ':'ML '}
    pieces=[s for s in text.split('; ') if 'proc (trigger unverified)' not in s]
    text=' / '.join(pieces)
    for before,after in replacements.items(): text=text.replace(before,after)
    return text

name_counts=collections.Counter(r[2] for r in post); name_index=collections.Counter(); rename={}; display_data=[]
for r in post:
    original_ref=r[0]; refs=r[13].split('; '); src=raw_by_ref[refs[0]]
    name_index[r[2]]+=1
    name=r[2]+(f' #{name_index[r[2]]}' if name_counts[r[2]]>1 else '')
    r[0]=name
    r[7]=compact_rolls(src) if src['quality'] in {5,7} or src['is_runeword'] else compact_other(r[7])
    r[6]='' # Retrieval locations remain in the private source CSV only.
    r[11]='' # Internal review language is not sales copy.
    locations=[]
    for old in refs:
        s=raw_by_ref[old]
        account=account_label(s)
        rename[old]=name if len(refs)==1 else name+' - '+account
        locations.append({'account':account,'accountKey':account_key(s),'character':s['char_name'],'ownerKey':owner_key(s),'tab':s['stash_type'],'x':s['grid_x'],'y':s['grid_y'],'quantity':s['stack_count'] or 1})
    definition=unique_definition(src) if src['quality']==7 else sets.get(str(src['unique_set_id']),{}) if src['quality']==5 else {}
    canonical=unidentified_names.get(original_ref,r[2]);is_unidentified=not bool(src['identified'])
    display_data.append({'key':original_ref,'name':name,'item':canonical,'category':r[1],'itemType':src['item_type'],'base':r[3] if r[3]!=canonical else '', 'quality':r[4],'quantity':r[5],'rolls':r[7],'identified':not is_unidentified,'unid':is_unidentified,'inferredName':original_ref in unidentified_names,'eth':r[8]=='Yes','sockets':r[9],'contents':r[10],'locations':locations,'definitionCode':definition.get('code' if src['quality']==7 else 'item','') if definition else ''})
    display_data[-1]['identitySignature']=identity_signature(src)
    r[13]='; '.join(rename[old] for old in refs)
    rename[original_ref]=name

for r in master:
    old=r[0]
    r[0]=rename.get(old,r[2])
    if old in issues: r[17]+=('; ' if r[17] else '')+'; '.join(issues[old])
for sheet in ['review_queue.csv','source_audit.csv']:
    for r in tables[sheet][1:]:
        old=r[0]
        s=raw_by_ref.get(old)
        r[0]=rename.get(old,(s['item_name']+' - '+s['char_name'] if s else old))
for old,notes in issues.items():
    s=raw_by_ref[old]
    tables['review_queue.csv'].append([rename[old],s['item_name'],account_label(s),s['char_name'],s['stash_type'],s['snapshot_ts'],'; '.join(notes),''])
tables['post_inventory.csv']=[tables['post_inventory.csv'][0]]+post
(P/'tables.json').write_text(json.dumps(tables),encoding='utf-8')

flair={'Runes':('GOLD','RUNE VAULT','From El to Zod — rune order, combined quantities.'),'Gems':('PURPLE','GEM HOARD','Little chips, big sparkle. Grouped by gem, then grade.'),'Runewords':('ORANGE','WORDS OF POWER','Bases and the rolls that matter.'),'Set items':('GREEN','COMPLETE YOUR SET','One more piece for the collection.'),'Uniques - armor':('GOLD','LEGENDARY ARMORY','Armor, helms, boots and more.'),'Uniques - weapons':('GOLD','LEGENDARY WEAPONS','Find your next monster slayer.'),'Charms':('BLUE','POCKET POWER','Small inventory slots. Big possibilities.'),'Jewels':('PURPLE','SOCKET CANDY','A little extra something for your gear.')}
intro='[center][b][color=gold]◆ THE STASH TREASURE TROVE ◆[/color][/b]\n[b]Softcore Ladder RotW • PC • Americas[/b]\nRunes • Gems • Runewords • Uniques • Sets • Charms\nPrices coming next — quote the item name and # when choosing a roll.[/center]\n'
draft=[intro]; rows_by_cat=collections.defaultdict(list)
for r,d in zip(post,display_data):
    cat=r[1]; details=[]
    if d['base']: details.append(d['base'])
    if r[4] in {'Magic','Rare','Superior','Crafted'}: details.append(r[4])
    if d['eth']: details.append('[b]ETH[/b]')
    if d['sockets']: details.append(str(d['sockets'])+'os'+(' ('+d['contents']+')' if d['contents'] and cat!='Runewords' else ''))
    if r[7]: details.append(r[7])
    prefix=f'{runes.index(r[2].replace(" Rune",""))+1:02d} · ' if cat=='Runes' else ''
    line=f'[b]{prefix}{r[0]}[/b]'
    if r[5]>1 or cat in {'Runes','Gems','Keys, essences and tokens','RotW materials','Consumables'}: line+=f' — [b]x{r[5]:,}[/b]'
    if details: line+=' — '+' | '.join(details)
    rows_by_cat[cat].append(line)
for cat in categories:
    color,title,tagline=flair.get(cat,('TEAL',cat.upper(),'Browse the stash. Find your next upgrade.'))
    lines=rows_by_cat[cat]
    block=f'\n[b][color={color.lower()}]━━ {title} ━━[/color][/b]\n[i]{tagline}[/i]\n\n'+'\n'.join(lines)+'\n'
    if cat=='Gems':
        grouped=[]
        for gem in gemtypes:
            grouped.append(f'[b]{gem}[/b]')
            grouped.extend(line for line,r in zip(lines,[r for r in post if r[1]=='Gems']) if r[2].endswith(gem))
            grouped.append('')
        block=f'\n[b][color=purple]━━ GEM HOARD ━━[/color][/b]\n[i]Chipped → Flawed → Regular → Flawless → Perfect[/i]\n\n'+'\n'.join(grouped)+'\n'
    draft.append(block)
    filename=cat.lower().replace(',','').replace(' ','-')+'.txt'
    (ROOT/'category-drafts'/filename).write_text(intro+block,encoding='utf-8')
text='\n'.join(draft)
(ROOT/'d2jsp_organized_draft.txt').write_text(text,encoding='utf-8')

# Embed original artwork where a code/name resolves unambiguously; no image modifications.
assets_path=Path(os.environ.get('D2R_ASSETS_DB','item_assets.db'))
assets=sqlite3.connect(assets_path.as_uri()+'?mode=ro',uri=True)
codes=dict(assets.execute('SELECT item_code,asset_path FROM item_codes'))
normalized={normalize(code):path for code,path in codes.items()}
asset_names=collections.defaultdict(list)
for (asset_path,) in assets.execute('SELECT asset_path FROM assets'):
    asset_names[normalize(asset_path.rsplit('/',1)[-1])].append(asset_path)
# The supplied asset name contains a spelling error; retain the correct item name.
asset_aliases={'chargedessenceofhatred':'quest/charged_essense_of_hatred'}
basecodes={normalize(r['name']):r['code'] for table in ['armor','weapons','misc'] for r in read(table) if r.get('name') and r.get('code')}
# The game table spells this base "Stilleto" while captured names use "Stiletto".
basecodes['stiletto']=basecodes['stilleto']
dimensions={r['code']:(int(r.get('invwidth') or 0),int(r.get('invheight') or 0)) for table in ['armor','weapons','misc'] for r in read(table) if r.get('code')}
images={}; image_bytes=0
for d in display_data:
    code=basecodes.get(normalize(d['base'] or d['item']),d['definitionCode'])
    d['width'],d['height']=dimensions.get(code,(0,0))
    name=normalize(d['item'])
    matches=asset_names.get(name,[])
    path=asset_aliases.get(name) or normalized.get(name) or (matches[0] if len(matches)==1 else None) or codes.get(code)
    if not path and d['category']=='Runes': path=codes.get(f'r{runes.index(d["item"].replace(" Rune",""))+1:02d}')
    if path and path not in images:
        blob=assets.execute('SELECT png_data FROM assets WHERE asset_path=?',(path,)).fetchone()[0]
        uri='data:image/png;base64,'+base64.b64encode(blob).decode()
        images[path]=uri; image_bytes+=len(uri)
    if path in images: d['image']=path
    d.pop('definitionCode',None)
assets.close()
characters={owner_key(r):{'key':owner_key(r),'name':r['char_name'],'account':account_label(r),'inventoryCount':0} for r in source}
for d in display_data:
    for location in d['locations']:
        if location['tab']=='inventory': characters[location['ownerKey']]['inventoryCount']+=location['quantity']
(P/'browser-data.json').write_text(json.dumps({'items':display_data,'images':images,'characters':sorted(characters.values(),key=lambda c:(c['account'],c['name'].lower()))},ensure_ascii=False),encoding='utf-8')
notes=(ROOT/'START_HERE.md').read_text(encoding='utf-8')
notes=notes.replace('Shared-stash entries are explicitly labeled in the post.','The public post has no stash-location tags; retrieval details remain in the private source CSV.')
notes=notes.replace('shared/personal labels, source references','readable names, compact variable rolls, source references')
notes=notes.replace('Proc trigger codes and Warlock skill-tree IDs are left explicitly unverified where a matching lookup was not available.','Warlock skill trees use the current game table order: Demon, Eldritch, Chaos. Proc trigger decoding remains a private review item.')
notes+='\n## Readability update\n\nThe post uses item names and numbered copies, ascending rune rank, and gem type followed by Chipped/Flawed/Regular/Flawless/Perfect. Set, unique and runeword lines use variable scalar modifiers identified in current item definitions, plus useful identity/base information and observed defense. Fixed proc damage endpoints are not treated as variable rolls. Missing rolls remain in the private review queue; no values are invented. Socket counts are total sockets, not a promise of empty sockets. Verification labels and stash tags are omitted from the post.\n\nCurrent item-definition reference: https://github.com/pinkufairy/D2R-Excel .\n'
(ROOT/'START_HERE.md').write_text(notes,encoding='utf-8')
assert all(r[5]>0 for r in post)
assert sum(r[5] for r in post)==sum(r[5] for r in master)
assert not re.search(r'\b[IB]-[0-9A-F]{8}\b',text)
assert 'Shared stash' not in text and 'VERIFY' not in text and 'unverified' not in text
assert len({r[0] for r in post})==len(post)
assert [sorting(r) for r in post]==sorted(sorting(r) for r in post)
print(json.dumps({'post_entries':len(post),'roll_review_items':len(issues),'artwork_images':len(images),'artwork_bytes':image_bytes,'data_bytes':(P/'browser-data.json').stat().st_size}))
