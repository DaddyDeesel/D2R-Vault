import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import vm from 'node:vm';

const logic=vm.runInNewContext(await fs.readFile(new URL('./logic.js',import.meta.url),'utf8')+'\nVaultLogic;');
const place={account:'Account 1',character:'Trader',tab:'shared1',x:2,y:3,quantity:1};
const items=[
  {key:'item-1',identitySignature:'sig-1',name:'Spirit #1',item:'Spirit',category:'Runewords',quality:'Normal',base:'Monarch',rolls:'35 FCR, "perfect"\n112 mana',quantity:1,postLine:'[b]Spirit #1[/b]',locations:[place]},
  {key:'item-2',identitySignature:'sig-2',name:'Harlequin Crest',item:'Harlequin Crest',category:'Uniques - armor',quality:'Unique',base:'Shako',rolls:'98 def',quantity:1,postLine:'[b]Harlequin Crest[/b]',locations:[{...place,x:5}]}
];
const data={sourceId:'source-1',items,postHeader:'DEFAULT HEADER',sectionHeaders:{Runewords:'DEFAULT RUNEWORDS', 'Uniques - armor':'DEFAULT UNIQUES'}};
const selected=new Set(items.map(logic.key));
const prices={'item-1':logic.priceEntry('25','each')};

const json=logic.tradeList(data,selected,prices,'2026-09-03T00:00:00.000Z');
assert.equal(json.format,'d2r-treasure-vault-trade-list');
assert.equal(json.items.length,2);
assert.equal(json.items[0].price.amount,'25');
assert.equal(json.items[0].locations[0].character,'Trader');

const fromJson=logic.readTradeList(JSON.stringify(json),'backup.json');
let restored=logic.restoreTradeList(fromJson,items);
assert.deepEqual([...restored.keys],['item-1','item-2']);
assert.equal(restored.prices['item-1'].basis,'each');

const csv=logic.tradeListCSV(data,selected,prices);
assert.ok(csv.includes('"35 FCR, ""perfect""\n112 mana"'));
const fromCsv=logic.readTradeList('\uFEFF'+csv,'backup.csv');
restored=logic.restoreTradeList(fromCsv,items);
assert.deepEqual([...restored.keys],['item-1','item-2']);
assert.equal(restored.prices['item-1'].amount,'25');

const moved=[{...items[0],key:'replacement-key'}];
restored=logic.restoreTradeList(fromJson,moved);
assert.deepEqual([...restored.keys],['replacement-key']);
assert.deepEqual([...restored.missing],['Harlequin Crest']);

assert.throws(()=>logic.readTradeList('{"items":[]}','bad.json'),/supported/);
assert.throws(()=>logic.readTradeList('"key","name"\r\n','empty.csv'),/does not contain any items/);

const searchItems=[
  {...items[0],itemType:'Shield',sockets:4,eth:false},
  {...items[1],itemType:'Helm',eth:false},
  {key:'hoz',name:'Herald of Zakarum',item:'Herald of Zakarum',category:'Uniques - armor',quality:'Unique',base:'Gilded Shield',rolls:'30 all res',quantity:1,itemType:'Auric Shield',eth:false,locations:[place]},
  {key:'pcomb',name:'Captain Grand Charm',item:'Grand Charm',category:'Charms',quality:'Magic',base:'Grand Charm',rolls:'+1 to Paladin Combat Skills',quantity:1,itemType:'Lcha',eth:false,locations:[place]},
  {key:'eth',name:'Ethereal Cryptic Axe',item:'Cryptic Axe',category:'Bases',quality:'Normal',base:'Cryptic Axe',rolls:'4 sockets',quantity:1,itemType:'Polearm',sockets:4,eth:true,locations:[place]}
];
assert.deepEqual(logic.filter(searchItems,{query:'shako'}).map(logic.key),['item-2']);
assert.deepEqual(logic.filter(searchItems,{query:'hoz'}).map(logic.key),['hoz']);
assert.deepEqual(logic.filter(searchItems,{query:'pcomb'}).map(logic.key),['pcomb']);
assert.deepEqual(logic.filter(searchItems,{query:'FCR >= 35'}).map(logic.key),['item-1']);
assert.deepEqual(logic.filter(searchItems,{query:'sockets = 4'}).map(logic.key),['item-1','eth']);
assert.deepEqual(logic.filter(searchItems,{query:'3os armor'}).map(logic.key),[]);
assert.deepEqual(logic.filter(searchItems,{query:'ethereal'}).map(logic.key),['eth']);
assert.deepEqual(logic.filter(searchItems,{query:'resistance >= 30'}).map(logic.key),['hoz']);
assert.equal(logic.filter(searchItems,{query:'herlad'}).at(0)?.key,'hoz');

const hammerdin=logic.packageBuild(searchItems,'hammerdin');
assert.equal(hammerdin.title,'Hammerdin');
assert.equal(hammerdin.slots.find(slot=>slot.label==='Helm').selectedKey,'item-2');
assert.equal(hammerdin.slots.find(slot=>slot.label==='Shield').selectedKey,'hoz');
assert.equal(hammerdin.slots.find(slot=>slot.label==='Combat skiller').selectedKey,'pcomb');
assert.equal(logic.packageKind(searchItems[1]),'helm');
assert.equal(logic.packageKind(searchItems[3]),'charm');
const custom=logic.packageBuild(searchItems,{id:'custom-test',title:'My Build',description:'Exact saved choices',custom:true,keywords:[],slots:[
  {id:'slot-helm',label:'Helm — Harlequin Crest',kind:'helm',wants:['Harlequin Crest']},
  {id:'slot-shield',label:'Shield — Herald of Zakarum',kind:'shield',wants:['Herald of Zakarum']}
]});
assert.equal(custom.title,'My Build');
assert.equal(custom.slots[0].id,'slot-helm');
assert.equal(custom.slots[0].selectedKey,'item-2');
assert.equal(custom.slots[1].selectedKey,'hoz');
const missingCustom=logic.packageBuild(searchItems,{id:'missing',title:'Missing item',custom:true,slots:[{id:'missing-slot',label:'Helm — Griffon',kind:'helm',wants:["Griffon's Eye"]}]});
assert.equal(missingCustom.slots[0].selectedKey,null);

const styledPost=logic.exportPost(data,selected,prices,{mainHeader:{enabled:false,text:'HIDDEN'},mainSubtext:{enabled:true,text:'[b]{{listing_count}} offers[/b]'},categories:{Runewords:{header:{enabled:true,text:'[color=orange]{{category}}[/color]'},subtext:{enabled:false,text:'HIDDEN'}},'Uniques - armor':{header:{enabled:false,text:'HIDDEN'},subtext:{enabled:true,text:'[i]{{total_quantity}} armor[/i]'}}}});
assert.ok(styledPost.startsWith('[b]2 offers[/b]'));
assert.ok(styledPost.includes('[color=orange]Runewords[/color]'));
assert.ok(styledPost.includes('[i]1 armor[/i]'));
assert.ok(!styledPost.includes('HIDDEN'));
assert.equal(logic.locationLabel(searchItems[0],place),'Account 1 - Shared Stash - Page 1 - x1 - column 3, row 4');
assert.equal(logic.locationLabel({...searchItems[0],category:'Runes'},{...place,tab:'advanced',quantity:12}),'Account 1 - Runes - x12');
const muleOnly={...searchItems[1],key:'mule-only',locations:[{...place,tab:'inventory',ownerKey:'mule-a',character:'HiddenMule'}]};
const scoped=logic.inventoryScope({items:[searchItems[0],muleOnly]},new Set());
assert.equal(scoped.items.map(logic.key).join(','),'item-1');
assert.equal(logic.packageBuild(scoped.items,'blizzard').slots.some(slot=>slot.candidates.some(candidate=>candidate.item.key==='mule-only')),false);

const html=await fs.readFile(new URL('./index.html',import.meta.url),'utf8');
const ids=[...html.matchAll(/id="([^"]+)"/g)].map(match=>match[1]);
assert.equal(new Set(ids).size,ids.length);
const app=await fs.readFile(new URL('./app.js',import.meta.url),'utf8');
const declarations=app.match(/Object.fromEntries\(\[([^\]]+)\]/)[1];
const controls=[...declarations.matchAll(/'([^']+)'/g)].map(match=>match[1]);
assert.ok(controls.every(id=>ids.includes(id)));

console.log('Passed: trade-list backups, advanced search, package ranking, and UI references.');
