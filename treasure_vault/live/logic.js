'use strict';
const VaultLogic=(()=>{
  const key=item=>item.key||item.name;
  const materialCategories=new Set(['Runes','Gems','Keys, essences and tokens','RotW materials']);
  const isMaterial=item=>materialCategories.has(item.category);
  const isShared=place=>place.tab==='advanced'||place.tab.startsWith('shared');
  const characters=item=>isMaterial(item)?[]:[...new Set(item.locations.filter(p=>!isShared(p)).map(p=>p.character))];
  const ownershipLabel=item=>isMaterial(item)?'':[...new Set(item.locations.map(p=>isShared(p)?p.account:p.character+(p.tab==='inventory'?' · Inventory':'')))].join(', ');
  function locationLabel(item,place){
    const tab=place.tab==='advanced'?'Materials tab':place.tab==='personal'?'Personal tab':place.tab==='inventory'?'Carried inventory':place.tab.replace('shared','Tab ');
    const owner=isMaterial(item)||isShared(place)?place.account:place.character+' · '+place.account;
    return owner+' · '+tab+' · x'+place.quantity+(place.tab!=='advanced'?' · column '+(place.x+1)+', row '+(place.y+1):'');
  }
  const typeLabels={'Helm':'Helms','Primal Helm':'Helms','Druid Pelt':'Helms','Circlet':'Helms','Gloves':'Gloves','Boots':'Boots','Belt':'Belts','Body Armor':'Body armor','Shield':'Shields','Auric Shield':'Shields','Head':'Shields','Grim':'Grimoires','Lcha':'Grand charms','Mcha':'Large charms','Scha':'Small charms','Csch':'Sunder charms','Cjwl':'Colossal jewels','Jewel':'Jewels','Ring':'Rings','Amulet':'Amulets','Sword':'Swords','Axe':'Axes','Bow':'Bows','Amazon Bow':'Bows','Crossbow':'Crossbows','Claw':'Claws','Club':'Clubs','Mace':'Maces','Hammer':'Hammers','Dagger':'Daggers','Javelin':'Javelins','Amazon Javelin':'Javelins','Spear':'Spears','Amazon Spear':'Spears','Polearm':'Polearms','Scepter':'Scepters','Staff':'Staves','Wand':'Wands','Orb':'Orbs','Throwing Axe':'Throwing axes','Throwing Knife':'Throwing knives','Rune':'Runes','Book':'Tomes','Rpot':'Rejuvenation potions'};
  function itemType(item){
    if(item.category==='Gems')return (item.item||item.name).split(' ').at(-1);
    if(item.category==='RotW materials')return (item.item||item.name).includes('Worldstone')?'Worldstone shards':'Other materials';
    if(item.category==='Keys, essences and tokens'){const name=item.item||item.name;return name.includes('Essence')?'Essences':name.includes('Token')?'Tokens':'Keys';}
    return typeLabels[item.itemType]||item.itemType||'Other';
  }
  function filter(items,{query='',category='',character='',type='',quality='',selectedOnly=false,selected=new Set()}={}){
    const terms=query.toLowerCase().trim().split(/\s+/).filter(Boolean);
    return items.filter(item=>(!category||item.category===category)&&(!type||itemType(item)===type)&&(!quality||item.quality===quality)&&(!character||characters(item).includes(character))&&(!selectedOnly||selected.has(key(item)))&&terms.every(term=>[item.name,item.base,item.rolls,item.quality,itemType(item),item.itemType||'',...characters(item),...item.locations.map(p=>p.account)].join(' ').toLowerCase().includes(term)));
  }
  function reconcile(selected,items){const valid=new Set(items.map(key));return new Set([...selected].filter(id=>valid.has(id)));}
  function muleOptions(data){
    const characters=new Map((data?.characters||[]).map(c=>[c.key,{...c,personalCount:0,inventoryCount:0}]));
    for(const item of data?.items||[])for(const place of item.locations){
      const owner=characters.get(place.ownerKey);if(!owner)continue;
      if(place.tab==='personal')owner.personalCount+=place.quantity;
      if(place.tab==='inventory')owner.inventoryCount+=place.quantity;
    }
    return [...characters.values()];
  }
  function inventoryScope(data,mules){
    const items=[];
    for(const item of data.items){
      const locations=item.locations.filter(p=>isShared(p)||(['personal','inventory'].includes(p.tab)&&mules.has(p.ownerKey)));
      if(!locations.length)continue;
      const quantity=locations.reduce((sum,p)=>sum+p.quantity,0);
      const postLine=item.postLine.replace(/ — \[b\]x[\d,]+\[\/b\]/,' — [b]x'+quantity.toLocaleString('en-US')+'[/b]');
      items.push({...item,locations,quantity,postLine});
    }
    return {...data,items};
  }
  function priceEntry(amount,basis='each'){
    const value=String(amount).trim();
    if(!['each','lot'].includes(basis)||!/^\d+(?:\.\d{1,2})?$/.test(value)||Number(value)<=0||Number(value)>1e9)throw new Error('Enter a positive FG price with up to two decimal places.');
    return {amount:String(Number(value)),basis};
  }
  function priceLabel(price){return price?price.amount+' fg '+(price.basis==='lot'?'for listing':'each'):'Set price';}
  function priceSearchURL(item){
    const name=String(item.item||item.base||item.name).replace(/ #\d+$/, '').replace(/["\r\n]/g,' ').trim();
    const query='site:forums.d2jsp.org "D2:R RotW Softcore Ladder Trading" "'+name+'"';
    return 'https://www.google.com/search?q='+encodeURIComponent(query);
  }
  function pricingSummary(items,selected,prices){
    const chosen=items.filter(item=>selected.has(key(item)));let cents=0,priced=0;
    for(const item of chosen){const price=prices[key(item)];if(price){priced++;cents+=Math.round(Number(price.amount)*100)*(price.basis==='lot'?1:item.quantity);}}
    return {priced,unpriced:chosen.length-priced,total:cents/100};
  }
  function exportPost(data,selected,prices={}){
    const chosen=data.items.filter(item=>selected.has(key(item)));if(!chosen.length)return '';
    const hasPrices=chosen.some(item=>prices[key(item)]);
    const header=data.postHeader.replace('Prices coming next — quote the item name and # when choosing a roll.',(hasPrices?'Prices in FG — ':'')+'Quote the item name and # when choosing a roll. Ask for pricing on unpriced items.');
    const blocks=[header];
    for(const category of new Set(chosen.map(item=>item.category))){
      const lines=[data.sectionHeaders[category]];let gem='';
      for(const item of chosen.filter(i=>i.category===category)){
        if(category==='Gems'){const next=item.item.split(' ').at(-1);if(next!==gem){lines.push('','[b]'+next+'[/b]');gem=next;}}
        const price=prices[key(item)];
        lines.push(item.postLine+(price?' — [b][color=gold]'+priceLabel(price)+'[/color][/b]':''));
      }
      blocks.push(lines.join('\n'));
    }
    return blocks.join('\n\n')+'\n';
  }
  const allowedColors=new Set(['gold','green','blue','red','purple','orange','teal','white','gray','grey','yellow','black','navy','silver','maroon','lime','aqua','fuchsia','pink']);
  function colorValue(value){const color=String(value||'').trim().toLowerCase();return allowedColors.has(color)||/^#[0-9a-f]{3}(?:[0-9a-f]{3})?$/.test(color)?color:null;}
  function parseBBCode(text){
    const root={tag:'root',children:[]};const stack=[root];let previous=0;
    const tokens=/\[(\/?)(b|i|u|center|color)(?:=([^\]\r\n]*))?\]/gi;
    const literal=value=>{if(value)stack.at(-1).children.push(value);};
    for(const match of text.matchAll(tokens)){
      literal(text.slice(previous,match.index));previous=match.index+match[0].length;
      const closing=!!match[1],tag=match[2].toLowerCase();
      if(closing){if(!match[3]&&stack.length>1&&stack.at(-1).tag===tag)stack.pop();else literal(match[0]);continue;}
      const color=tag==='color'?colorValue(match[3]):null;
      if(stack.length>=64||(tag==='color'&&!color)||(tag!=='color'&&match[3]!==undefined)){literal(match[0]);continue;}
      const node={tag,color,children:[]};stack.at(-1).children.push(node);stack.push(node);
    }
    literal(text.slice(previous));return root;
  }
  function formatSelection(text,start,end,tag,color){
    if(!['b','i','u','color'].includes(tag))throw new Error('Unsupported format');
    const value=tag==='color'?colorValue(color):null;if(tag==='color'&&!value)throw new Error('Unsupported color');
    const open='['+tag+(value?'='+value:'')+']',close='[/'+tag+']';
    return {text:text.slice(0,start)+open+text.slice(start,end)+close+text.slice(end),start:start+open.length,end:end+open.length};
  }
  function syncDraft(draft,generated){
    if(!draft||!draft.dirty)return{text:generated,base:generated,dirty:false,stale:false};
    return{...draft,stale:draft.base!==generated};
  }
  function tradeList(data,selected,prices={},exportedAt=new Date().toISOString()){
    const items=data.items.filter(item=>selected.has(key(item))).map(item=>({
      key:key(item),identitySignature:item.identitySignature||'',name:item.name,item:item.item||'',category:item.category||'',quality:item.quality||'',base:item.base||'',rolls:item.rolls||'',quantity:item.quantity,price:prices[key(item)]||null,
      locations:(item.locations||[]).map(place=>({account:place.account||'',character:place.character||'',tab:place.tab||'',x:place.x,y:place.y,quantity:place.quantity}))
    }));
    return{format:'d2r-treasure-vault-trade-list',version:1,exportedAt,sourceId:data.sourceId||'',items};
  }
  const csvCell=value=>'"'+String(value??'').replace(/"/g,'""')+'"';
  function tradeListCSV(data,selected,prices={}){
    const backup=tradeList(data,selected,prices);const headings=['key','identitySignature','name','item','category','quality','base','rolls','quantity','priceAmount','priceBasis','locations'];
    const rows=backup.items.map(item=>[item.key,item.identitySignature,item.name,item.item,item.category,item.quality,item.base,item.rolls,item.quantity,item.price?.amount||'',item.price?.basis||'',item.locations.map(place=>locationLabel(item,place)).join(' | ')]);
    return[headings,...rows].map(row=>row.map(csvCell).join(',')).join('\r\n')+'\r\n';
  }
  function parseCSV(text){
    const rows=[];let row=[],cell='',quoted=false;
    for(let i=0;i<text.length;i++){const char=text[i];if(quoted){if(char==='"'&&text[i+1]==='"'){cell+='"';i++;}else if(char==='"')quoted=false;else cell+=char;}else if(char==='"')quoted=true;else if(char===','){row.push(cell);cell='';}else if(char==='\n'){row.push(cell.replace(/\r$/,''));rows.push(row);row=[];cell='';}else cell+=char;}
    if(quoted)throw new Error('The CSV file has an unfinished quoted value.');if(cell||row.length){row.push(cell.replace(/\r$/,''));rows.push(row);}return rows;
  }
  function readTradeList(text,filename=''){
    text=String(text).replace(/^\uFEFF/,'');let imported;
    if(filename.toLowerCase().endsWith('.csv')||String(text).trimStart().startsWith('"key"')){
      const rows=parseCSV(String(text));if(rows.length<2)throw new Error('The CSV trade list does not contain any items.');const headings=rows.shift();const at=name=>headings.indexOf(name);if(at('key')<0||at('name')<0)throw new Error('This CSV is not a D2R Treasure Vault trade list.');
      imported=rows.filter(row=>row.some(Boolean)).map(row=>({key:row[at('key')],identitySignature:at('identitySignature')<0?'':row[at('identitySignature')],name:row[at('name')],price:at('priceAmount')>=0&&row[at('priceAmount')]?{amount:row[at('priceAmount')],basis:row[at('priceBasis')]||'each'}:null}));
    }else{
      let parsed;try{parsed=JSON.parse(text);}catch{throw new Error('Choose a valid JSON or CSV trade-list backup.');}
      if(parsed?.format!=='d2r-treasure-vault-trade-list'||parsed.version!==1||!Array.isArray(parsed.items))throw new Error('This JSON is not a supported D2R Treasure Vault trade list.');imported=parsed.items;
    }
    if(!imported.length)throw new Error('The trade-list backup does not contain any items.');if(imported.length>10000)throw new Error('This trade list is too large to import.');return imported;
  }
  function restoreTradeList(imported,items){
    const byKey=new Map(items.map(item=>[key(item),item])),bySignature=new Map();for(const item of items){if(!item.identitySignature)continue;const group=bySignature.get(item.identitySignature)||[];group.push(item);bySignature.set(item.identitySignature,group);}
    const keys=[],restoredPrices={},missing=[];
    for(const saved of imported){let item=byKey.get(saved.key);if(!item&&saved.identitySignature){const matches=bySignature.get(saved.identitySignature)||[];if(matches.length===1)item=matches[0];}if(!item){missing.push(saved.name||saved.key||'Unknown item');continue;}const id=key(item);if(!keys.includes(id))keys.push(id);if(saved.price){try{restoredPrices[id]=priceEntry(saved.price.amount,saved.price.basis);}catch{}}
    }
    return{keys,prices:restoredPrices,missing};
  }
  return{key,itemType,characters,ownershipLabel,locationLabel,isMaterial,isShared,filter,reconcile,muleOptions,inventoryScope,exportPost,priceEntry,priceLabel,pricingSummary,priceSearchURL,colorValue,parseBBCode,formatSelection,syncDraft,tradeList,tradeListCSV,readTradeList,restoreTradeList};
})();
