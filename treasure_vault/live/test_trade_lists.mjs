import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import vm from 'node:vm';

const logic=vm.runInNewContext(await fs.readFile(new URL('./logic.js',import.meta.url),'utf8')+'\nVaultLogic;');
const place={account:'Account 1',character:'Trader',tab:'shared1',x:2,y:3,quantity:1};
const items=[
  {key:'item-1',identitySignature:'sig-1',name:'Spirit #1',item:'Spirit',category:'Runewords',quality:'Normal',base:'Monarch',rolls:'35 FCR, "perfect"\n112 mana',quantity:1,locations:[place]},
  {key:'item-2',identitySignature:'sig-2',name:'Harlequin Crest',item:'Harlequin Crest',category:'Uniques - armor',quality:'Unique',base:'Shako',rolls:'98 def',quantity:1,locations:[{...place,x:5}]}
];
const data={sourceId:'source-1',items};
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

const html=await fs.readFile(new URL('./index.html',import.meta.url),'utf8');
const ids=[...html.matchAll(/id="([^"]+)"/g)].map(match=>match[1]);
assert.equal(new Set(ids).size,ids.length);
const app=await fs.readFile(new URL('./app.js',import.meta.url),'utf8');
const declarations=app.match(/Object.fromEntries\(\[([^\]]+)\]/)[1];
const controls=[...declarations.matchAll(/'([^']+)'/g)].map(match=>match[1]);
assert.ok(controls.every(id=>ids.includes(id)));

console.log('Passed: JSON/CSV trade-list export, parsing, restore matching, and UI references.');
