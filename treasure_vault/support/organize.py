import collections
import csv
import hashlib
import json
import os
from pathlib import Path
import sqlite3

ROOT = Path(os.environ.get('D2R_OUTPUT_DIR',Path(__file__).resolve().parent.parent))
SUPPORT = ROOT / 'support'
SOURCE = Path('__select_inventory__.db')
if os.environ.get('D2R_INPUT_JSON'):
    rows=json.loads(Path(os.environ['D2R_INPUT_JSON']).read_text(encoding='utf-8'))
else:
    conn = sqlite3.connect(SOURCE.as_uri() + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute('BEGIN')
    rows = [dict(r) for r in conn.execute('SELECT * FROM stash_items')]
    conn.close()
(SUPPORT / 'source-records.json').write_text(json.dumps(rows), encoding='utf-8')
stat_meta = {r['ID']: r for r in csv.DictReader((SUPPORT / 'ItemStatCost.txt').open(), delimiter='\t') if r['ID']}
skill_names = {int(r['*Id']): r['skill'] for r in csv.DictReader((SUPPORT / 'current-skills.txt').open(encoding='utf-8-sig'), delimiter='\t') if r.get('*Id', '').isdigit()}
accounts = {a: f'Account {i+1}' for i, a in enumerate(sorted(set(r['account_id'] for r in rows)))}
latest = {a: max(r['snapshot_ts'] for r in rows if r['account_id'] == a) for a in accounts}
shared = lambda r: r['stash_type'] == 'advanced' or r['stash_type'].startswith('shared')
latest_shared_owner={a:min((r['char_name'] for r in rows if r['account_id']==a and shared(r) and r['snapshot_ts']==latest[a]),default=None) for a in accounts}
stash_only = lambda r: r['stash_type']=='personal' or shared(r)
include_inventory=os.environ.get('D2R_INCLUDE_INVENTORY')=='1'
eligible=lambda r:stash_only(r) or (include_inventory and r['stash_type']=='inventory')
current = [r for r in rows if eligible(r) and (not shared(r) or (r['snapshot_ts']==latest[r['account_id']] and r['char_name']==latest_shared_owner[r['account_id']]))]
unknown_materials = [r for r in current if r['stash_type']=='advanced' and r['stack_count'] is None]
selected = [r for r in current if r not in unknown_materials and (r['stack_count'] is None or r['stack_count'] > 0)]
quality = {1:'Low quality',2:'Normal',3:'Superior',4:'Magic',5:'Set',6:'Rare',7:'Unique',8:'Crafted'}
classes = ['Amazon','Sorceress','Necromancer','Paladin','Barbarian','Druid','Assassin','Warlock']
tabs = {0:'Bow and Crossbow (Amazon)',1:'Passive and Magic (Amazon)',2:'Javelin and Spear (Amazon)',8:'Fire (Sorceress)',9:'Lightning (Sorceress)',10:'Cold (Sorceress)',16:'Curses (Necromancer)',17:'Poison and Bone (Necromancer)',18:'Summoning (Necromancer)',24:'Combat (Paladin)',25:'Offensive Auras (Paladin)',26:'Defensive Auras (Paladin)',32:'Combat (Barbarian)',33:'Combat Masteries (Barbarian)',34:'Warcries (Barbarian)',40:'Summoning (Druid)',41:'Shape Shifting (Druid)',42:'Elemental (Druid)',48:'Traps (Assassin)',49:'Shadow Disciplines (Assassin)',50:'Martial Arts (Assassin)'}
runes = ['El','Eld','Tir','Nef','Eth','Ith','Tal','Ral','Ort','Thul','Amn','Sol','Shael','Dol','Hel','Io','Lum','Ko','Fal','Lem','Pul','Um','Mal','Ist','Gul','Vex','Ohm','Lo','Sur','Ber','Jah','Cham','Zod']
tabs.update({56:'Demon (Warlock)',57:'Eldritch (Warlock)',58:'Chaos (Warlock)'})
labels = {
 '0':'Strength','1':'Energy','2':'Dexterity','3':'Vitality','7':'Life','9':'Mana','11':'Stamina',
 '16':'Enhanced defense %','17':'Enhanced maximum damage %','18':'Enhanced minimum damage %','19':'Attack rating',
 '20':'Block chance %','31':'Defense (stored)','32':'Defense vs missiles','34':'Physical damage reduced','35':'Magic damage reduced','36':'Physical damage reduced %',
 '37':'Magic resistance %','39':'Fire resistance %','40':'Maximum fire resistance %','41':'Lightning resistance %','42':'Maximum lightning resistance %','43':'Cold resistance %','44':'Maximum cold resistance %','45':'Poison resistance %','46':'Maximum poison resistance %',
 '60':'Life stolen per hit %','62':'Mana stolen per hit %','74':'Replenish life','75':'Maximum durability %','76':'Maximum life %','77':'Maximum mana %',
 '78':'Attacker takes damage','79':'Extra gold %','80':'Magic find %','85':'Experience gain %','86':'Life after each kill','87':'Vendor price reduction %','89':'Light radius','91':'Requirements %',
 '93':'IAS %','96':'FRW %','99':'FHR %','102':'FBR %','105':'FCR %','110':'Poison length reduced %','114':'Damage taken goes to mana %',
 '119':'Attack rating bonus %','121':'Damage to demons %','122':'Damage to undead %','123':'Attack rating vs demons','124':'Attack rating vs undead','127':'All skills',
 '135':'Open wounds %','136':'Crushing blow %','138':'Mana after each kill','139':'Life after demon kill','141':'Deadly strike %',
 '142':'Fire absorb %','143':'Fire absorb','144':'Lightning absorb %','145':'Lightning absorb','147':'Magic absorb','148':'Cold absorb %','149':'Cold absorb','150':'Slows target %',
 '329':'Fire skill damage %','330':'Lightning skill damage %','331':'Cold skill damage %','332':'Poison skill damage %',
 '333':'Enemy fire resistance reduction %','334':'Enemy lightning resistance reduction %','335':'Enemy cold resistance reduction %','336':'Enemy poison resistance reduction %','357':'Magic skill damage %','358':'Enemy magic resistance reduction %'
}
booleans = {'81':'Knockback','115':'Ignore target defense','117':'Prevent monster heal','118':'Half freeze duration','152':'Indestructible','153':'Cannot be frozen'}
order = ['Runes','Gems','Keys, essences and tokens','RotW materials','Runewords','Charms','Jewels','Rings and amulets','Uniques - armor','Uniques - weapons','Set items','Bases','Magic and rare gear','Consumables','Utility and quest items','Other items']
armor = {'Body Armor','Boots','Gloves','Helm','Belt','Shield','Auric Shield','Circlet','Druid Pelt','Primal Helm','Head'}
rotw_names={r['item_name'] for r in rows if r['stash_type']=='advanced' and r['item_type'] in {'Quest','Grim'}}
def category(r):
    t,n = r['item_type'] or '', r['item_name']
    if t == 'Rune': return 'Runes'
    if t.startswith('Gem'): return 'Gems'
    if n.startswith('Key of ') or 'Essence' in n or n == 'Token of Absolution': return 'Keys, essences and tokens'
    if n in rotw_names: return 'RotW materials'
    if r['is_runeword']: return 'Runewords'
    if t in {'Scha','Lcha','Mcha','Csch'}: return 'Charms'
    if t in {'Jewel','Cjwl'}: return 'Jewels'
    if t in {'Ring','Amulet'}: return 'Rings and amulets'
    if r['quality']==7: return 'Uniques - armor' if t in armor else 'Uniques - weapons'
    if r['quality']==5: return 'Set items'
    if t in {'Rpot','Hpot','Mpot'}: return 'Consumables'
    if t in {'Book','Key','Quest'}: return 'Utility and quest items'
    if r['quality'] in {1,2,3}: return 'Bases'
    if r['quality'] in {4,6,8}: return 'Magic and rare gear'
    return 'Other items'

def decode(r):
    stats=json.loads(r['stats_json'] or '{}'); skills=json.loads(r['skills_json'] or '{}')
    parts=[]; issues=[]
    def skill(sid):
        if sid not in skill_names: issues.append(f'Skill ID {sid} needs RotW lookup')
        return skill_names.get(sid, f'Skill ID {sid}')
    for kind, entries in skills.items():
        seen=set()
        for entry in entries:
            token=json.dumps(entry,sort_keys=True)
            if token in seen: continue
            seen.add(token)
            if kind in {'class_skills','skill_tabs','single_skills','non_class_skills','item_auras'}:
                sid,val=entry
                if kind=='class_skills': name=(classes[sid] if sid<len(classes) else f'Class {sid}')+' skills'
                elif kind=='skill_tabs':
                    name=tabs.get(sid,f'Warlock skill tree ID {sid}' if sid in {56,57,58} else f'Skill tree ID {sid}')
                    if sid not in tabs: issues.append(f'Skill tree ID {sid} needs confirmed name')
                else: name=skill(sid)
                parts.append(f'Level {val} {name} aura' if kind=='item_auras' else f'+{val} {name}')
            elif kind=='charged_skills': parts.append(f"Level {entry['level']} {skill(entry['skill_id'])} ({entry['current_charges']}/{entry['max_charges']} charges)")
            elif kind=='skill_procs':
                parts.append(f"{entry['chance']}% level {entry['level']} {skill(entry['skill_id'])} proc (trigger unverified)")
                issues.append('Proc trigger not decoded')
            else: issues.append(f'Unmapped skill group: {kind}')
    if stats.get('17') is not None and stats.get('17')==stats.get('18'):
        parts.append(f"{stats['17']}% enhanced damage")
    if all(k in stats for k in ['39','41','43','45']) and len({stats[k] for k in ['39','41','43','45']})==1:
        parts.append(f"All resistances: {stats['39']}%")
        resist_group=True
    else: resist_group=False
    for k, label in labels.items():
        if k not in stats: continue
        if k in {'17','18'} and stats.get('17')==stats.get('18'): continue
        if k in {'39','41','43','45'} and resist_group: continue
        parts.append(f'{label}: {stats[k]}')
    for k,label in booleans.items():
        if stats.get(k): parts.append(label)
    # Preserve damage observations without pretending they are base-independent affix rolls.
    for lo,hi,label in [('21','22','Physical damage (stored)'),('48','49','Fire damage'),('50','51','Lightning damage'),('52','53','Magic damage'),('54','55','Cold damage')]:
        if lo in stats or hi in stats: parts.append(f'{label}: {stats.get(lo,0)}-{stats.get(hi,0)}')
    if any(k in stats for k in ['57','58','59']): issues.append('Poison damage units need tooltip verification')
    if any(214 <= int(k) <= 268 for k in stats): issues.append('Level-scaled modifiers retained raw; verify tooltip')
    if r['is_runeword'] and r['item_type'] not in armor and not ('17' in stats or '18' in stats): issues.append('Weapon runeword: verify complete affix rolls against tooltip')
    if not r['identified']: issues.append('Unidentified')
    if r['stash_type']=='advanced' and r['stack_count'] is None: issues.append('Material quantity missing: could be empty slot or unrecorded quantity')
    if r['stash_type'] in {'equipped','merc'}: issues.append('Currently equipped' if r['stash_type']=='equipped' else 'Currently on mercenary')
    if category(r)=='Utility and quest items': issues.append('Check tradeability / include only if useful')
    raw='; '.join(f"{labels.get(k,stat_meta.get(k,{}).get('Stat',f'Stat ID {k}'))} [ID {k}]={v}" for k,v in sorted(stats.items(),key=lambda kv:int(kv[0])))
    contents=[]
    for code in json.loads(r['socketed_runes'] or '[]'):
        contents.append(runes[int(code[1:])-1] if code.startswith('r') and code[1:].isdigit() and 1<=int(code[1:])<=33 else code)
    sockets=stats.get('194',0)
    if sockets and not contents: issues.append('Socket contents not recorded; empty/filled not confirmed')
    return '; '.join(parts),raw,'; '.join(dict.fromkeys(issues)),sockets,' + '.join(contents)

def source_key(r): return (r['account_id'],r['char_name'],r['unit_id'])
def ref(r): return 'I-'+hashlib.sha256('|'.join(map(str,source_key(r))).encode()).hexdigest()[:8].upper()
headers=['Reference','Category','Item','Base','Quality','Quantity','Quantity status','Key stats (partial)','Ethereal','Sockets (total)','Recorded socket contents','Account','Character','Location','Grid X (0-based)','Grid Y (0-based)','Captured UTC','Review notes','BIN FG','Minimum FG','Sale status','Named stats (raw values)','Skills JSON (original)','Unit ID']
selected.sort(key=lambda r:(order.index(category(r)),r['item_name'].casefold(),accounts[r['account_id']],r['char_name'],r['unit_id']))
organized=[]; by_ref={}
for r in selected:
    summary,raw,issues,sockets,contents=decode(r)
    qty=r['stack_count'] if r['stack_count'] is not None else (None if r['stash_type']=='advanced' else 1)
    record=[ref(r),category(r),r['runeword_name'] or r['item_name'],r['base_name'],quality.get(r['quality'],str(r['quality'])),qty,'Unknown' if qty is None else ('Recorded stack' if r['stack_count'] is not None else 'Single item'),summary,'Yes' if r['ethereal'] else 'No',sockets,contents,accounts[r['account_id']],r['char_name'],r['stash_type'],r['grid_x'],r['grid_y'],r['snapshot_ts'],issues,None,None,'Unpriced / review' if issues else 'Unpriced',raw,r['skills_json'],r['unit_id']]
    organized.append(record); by_ref[ref(r)]=r

chosen_keys={source_key(r) for r in selected}
audit=[['Source reference','Account','Character','Location','Item','Unit ID','Captured UTC','Disposition','Reason']]
older_tabs={}
for r in rows:
    if source_key(r) in chosen_keys: disposition='Included'; reason='One consolidated latest account-wide shared snapshot' if shared(r) else 'Character-owned record retained'
    elif not eligible(r):
        disposition='Excluded character item'; reason='Equipped and mercenary items excluded; character inventory requires inclusion'
    elif r in unknown_materials or (r['stack_count'] is not None and r['stack_count'] <= 0):
        disposition='Excluded quantity'; reason='Missing or nonpositive material quantity; omitted from post and totals'
    else:
        disposition='Older shared observation'; reason='Not counted; shared data is recorded separately under multiple character snapshots'
        if shared(r) and r['snapshot_ts']==latest[r['account_id']] and r['char_name']!=latest_shared_owner[r['account_id']]:
            disposition='Duplicate shared observation';reason='Not counted; another character from the same account recorded the same latest shared snapshot'
        if not any(x['account_id']==r['account_id'] and x['stash_type']==r['stash_type'] for x in current):
            key=(r['account_id'],r['stash_type'])
            older_tabs[key]=max(older_tabs.get(key,''),r['snapshot_ts'])
            reason='Tab absent from newest account snapshot; possible emptied/moved tab; review instead of counting'
    audit.append([ref(r),accounts[r['account_id']],r['char_name'],r['stash_type'],r['item_name'],r['unit_id'],r['snapshot_ts'],disposition,reason])
legacy=[r for r in rows if (r['account_id'],r['stash_type']) in older_tabs and r['snapshot_ts']==older_tabs[(r['account_id'],r['stash_type'])]]
review_headers=['Reference','Item','Account','Character','Location','Captured UTC','Reason','Key stats (partial)']
review=[review_headers]+[[r[0],r[2],r[11],r[12],r[13],r[16],r[17],r[7]] for r in organized if r[17]]
for r in unknown_materials:
    review.append([ref(r),r['item_name'],accounts[r['account_id']],r['char_name'],r['stash_type'],r['snapshot_ts'],'Excluded from post and totals: quantity missing',decode(r)[0]])
for r in legacy:
    review.append([ref(r),r['item_name'],accounts[r['account_id']],r['char_name'],r['stash_type'],r['snapshot_ts'],'Older tab absent from newest account snapshot: not included; verify whether moved or still present',decode(r)[0]])
counts=collections.Counter(r[1] for r in organized)
summary_rows=[['Category','Inventory records','Known units (not including unknown quantities)','Unknown quantity records','Records with review notes','BIN FG']]
for cat in order:
    group=[r for r in organized if r[1]==cat]
    if group: summary_rows.append([cat,len(group),sum(r[5] or 0 for r in group),sum(r[5] is None for r in group),sum(bool(r[17]) for r in group),None])
payload={'organized_inventory.csv':[headers]+organized,'review_queue.csv':review,'source_audit.csv':audit,'category_summary.csv':summary_rows}

# The private inventory preserves each location; the post combines fungible materials.
post_rows=[]
bulk_categories={'Runes','Gems','Keys, essences and tokens','RotW materials','Consumables'}
for cat in order:
    group=[r for r in organized if r[1]==cat]
    if cat in bulk_categories:
        grouped=collections.defaultdict(list)
        for r in group: grouped[(r[2],r[3],r[4],r[7],r[8],r[9],r[10])].append(r)
        for key, entries in grouped.items():
            combined=list(entries[0])
            combined[0]='B-'+hashlib.sha256((cat+'|'+json.dumps(key)).encode()).hexdigest()[:8].upper()
            combined[5]=sum(r[5] for r in entries)
            combined[13]='Shared stash' if all(shared(by_ref[r[0]]) for r in entries) else 'Stash (shared and personal)' if any(shared(by_ref[r[0]]) for r in entries) else 'Personal stash'
            post_rows.append((combined,[r[0] for r in entries]))
    else:
        for r in group:
            item=list(r)
            item[13]='Shared stash - '+r[13] if shared(by_ref[r[0]]) else 'Personal stash'
            post_rows.append((item,[r[0]]))
payload['post_inventory.csv']=[['Reference','Category','Item','Base','Quality','Total quantity','Stash location','Key stats (partial)','Ethereal','Sockets (total)','Recorded socket contents','Review notes','BIN FG','Source references']]+[[r[0],r[1],r[2],r[3],r[4],r[5],r[13],r[7],r[8],r[9],r[10],r[17],None,'; '.join(refs)] for r,refs in post_rows]
(SUPPORT/'tables.json').write_text(json.dumps(payload),encoding='utf-8')

draft_dir=ROOT/'category-drafts'; draft_dir.mkdir(exist_ok=True)
intro='[b]Softcore Ladder RotW | PC | Americas[/b]\nOrganization draft - prices not assigned. Verify marked entries before posting.\nPlease reference the item ID when discussing an item.\n'
draft=[intro]
for cat in order:
    group=[r for r,refs in post_rows if r[1]==cat]
    block=[f'\n[b]{cat}[/b]']
    for r in group:
        name=r[2]+(f' ({r[3]})' if r[3] and r[3]!=r[2] else '')
        if r[4] in {'Magic','Rare','Superior','Crafted'}: name=r[4]+' '+name
        detail=[]
        if r[8]=='Yes': detail.append('ETH')
        if r[9]: detail.append(f'{r[9]} sockets'+(f' / {r[10]}' if r[10] else ' / contents unverified'))
        if r[7]: detail.append(r[7])
        qty='quantity unverified' if r[5] is None else f'x{r[5]}'
        line=f'{r[0]} | {name} | {qty} | {r[13]}'
        if detail: line+=' | '+'; '.join(detail)
        if r[17]: line+=' | [VERIFY: '+r[17]+']'
        block.append(line)
    if not group: block.append('No eligible stash items.')
    text='\n'.join(block)+'\n'
    filename=cat.lower().replace(',','').replace(' ','-')+'.txt'
    (draft_dir/filename).write_text(intro+text,encoding='utf-8')
    if group: draft.append(text)
(ROOT/'d2jsp_organized_draft.txt').write_text('\n'.join(draft),encoding='utf-8')

unknown=sum(r[5] is None for r in organized)
notes=f'''# Inventory organized for sale

Softcore Ladder RotW · PC · Americas · Stash items only · Prices blank

The stash-only list contains **{len(organized):,} source records**, combined into **{len(post_rows):,} post entries**. Accounts use generic labels for this database. Rune, gem, and other fungible material quantities are combined across accounts. **{len(unknown_materials)} unknown-quantity material records are omitted**, without assuming a quantity. Personal stash and current shared-stash records are eligible; character inventory, equipped gear and mercenary gear are excluded. Shared-stash entries are explicitly labeled in the post.

## Files

- [Post inventory](post_inventory.csv): combined quantities matching the post, shared/personal labels, source references, and blank prices.
- [Organized inventory](organized_inventory.csv): private stash-only source list, partial readable stats, individual locations, stable reference IDs, and blank price columns.
- [Category summary](category_summary.csv): counts by sale category.
- [Review queue](review_queue.csv): excluded unknown quantities, stat decoding limitations, and older shared tabs needing review. Excluded records are not counted in the post.
- [d2jsp organization draft](d2jsp_organized_draft.txt): categorized text with reference IDs, no account identifiers or character locations, and no prices. It is a working draft, not ready to publish.
- [Category drafts](category-drafts): each category is also saved separately for editing into manageable posts.
- [Source audit](source_audit.csv): every original record and why it was included or set aside.

## Categories

| Category | Records | Known units | Unknown quantity records |
|---|---:|---:|---:|
'''
for r in summary_rows[1:]: notes+=f'| {r[0]} | {r[1]} | {r[2]} | {r[3]} |\n'
notes+='''
## How repeated observations were handled

Shared and advanced/materials tabs are recorded anew for each character, with different unit IDs. For each account, only shared records from its newest captured timestamp are included. Only personal stash and shared stash are eligible. Character inventory, equipped gear and mercenary items are excluded. No items were deleted from the original database. Individual gear items retain separate IDs; fungible materials are totaled across accounts in the post. The private source list retains their individual locations for retrieval.

This assumes each latest character snapshot includes the complete shared inventory. The database does not explicitly record empty tabs or prove that assumption. Older tabs absent from the newest snapshot are therefore retained in the review queue, not silently declared sold or lost. Movement between character snapshots can also leave duplicates that this data alone cannot conclusively identify. Quantities describe captured records, not a live in-game verification.

Latest shared snapshots by account:
'''
for a,ts in sorted(latest.items()):
    chars=', '.join(sorted(set(r['char_name'] for r in rows if r['account_id']==a and r['snapshot_ts']==ts)))
    notes+=f'- {accounts[a]}: {ts} ({chars})\n'
notes+=f'''
There are {len(legacy)} records from the most recent observations of older tabs missing from the latest snapshot. They are listed for review, not added to sale quantities. Null material quantities are omitted from the post and totals as requested. If another account has a known quantity of the same material, that known quantity is included.

## Stats and sale readiness

The readable description is a partial interpretation of stored stats, not a complete recreated tooltip. All stored stats are retained with their numeric IDs, and original skill JSON is preserved. Exact repeated skill entries are shown once, never added together. Prices are intentionally blank.

- Level-scaled stats and poison damage retain their raw values pending verification of the manager's units. No automatic bit shifting was applied to the manager's already-processed values.
- Proc trigger codes and Warlock skill-tree IDs are left explicitly unverified where a matching lookup was not available.
- Socket counts are total sockets, not empty sockets. Recorded contents are shown when available.
- Some runeword snapshots lack enhanced-damage affix values; displayed weapon damage is not used to invent those rolls.
- Inventory, equipped and mercenary items are excluded. Any utility/quest items in an eligible stash remain visible with a tradeability check.
- Rare/magic names can be generic in the database; retain their reference IDs and check the full tooltip before pricing valuable pieces. Item level and required level are not supplied.
- The mode/region header comes from your instructions; these settings are not independently encoded in this inventory schema.

## Supplied database files

`items.db` stores inventory and drop history. The drop log was not treated as additional inventory. SQLite read the source in read-only mode with a consistent transaction and its existing WAL sidecar. The `.db-wal` and `.db-shm` files are SQLite companions, not separate inventories; keep them with their databases. `item_assets.db` contains PNG artwork and item-code-to-image links, not stat or skill definitions. No executable or configuration changes were needed.

Stat naming references: [ItemStatCost table](https://github.com/fabd/diablo2/blob/master/code/d2_113_data/ItemStatCost.txt) and [Skills table](https://github.com/fabd/diablo2/blob/master/code/d2_113_data/Skills.txt). These are legacy reference tables; newer/unverified RotW mappings are flagged rather than guessed.

Next step: review the remaining tooltip flags, then assign FG prices by post reference ID. Use post_inventory.csv for combined listings and organized_inventory.csv to locate their source items.
'''
(ROOT/'START_HERE.md').write_text(notes,encoding='utf-8')
assert len(audit)-1==len(rows)
assert len(set(r[0] for r in organized))==len(organized)
assert len(selected)+sum(r[7]!='Included' for r in audit[1:])==len(rows)
assert all(not shared(r) or (r['snapshot_ts']==latest[r['account_id']] and r['char_name']==latest_shared_owner[r['account_id']]) for r in selected)
assert all(len({r['char_name'] for r in selected if r['account_id']==a and shared(r)})<=1 for a in accounts)
assert all(r[18] is None and r[19] is None for r in organized)
assert all(a not in '\n'.join(draft) for a in accounts)
assert all(eligible(r) and r['stash_type'] not in {'equipped','merc'} for r in selected)
assert all(r[5] is not None and r[5] > 0 for r in organized)
assert sorted(x for r,refs in post_rows for x in refs)==sorted(r[0] for r in organized)
assert sum(r[5] for r,refs in post_rows)==sum(r[5] for r in organized)
assert 'quantity unverified' not in '\n'.join(draft)
assert 'Currently equipped' not in '\n'.join(draft) and 'Currently on mercenary' not in '\n'.join(draft)
for cat in ['Runes','Gems']:
    names=[r[2] for r,refs in post_rows if r[1]==cat]
    assert len(names)==len(set(names)), f'Duplicate material names in {cat}'
print(json.dumps({'source_records':len(rows),'organized_records':len(organized),'older_observations':len(rows)-len(organized),'legacy_tab_review_records':len(legacy),'unknown_quantities':unknown,'review_rows':len(review)-1,'categories':dict(counts)},indent=2))
