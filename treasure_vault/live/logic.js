'use strict';
const VaultLogic=(()=>{
  const key=item=>item.key||item.name;
  const materialCategories=new Set(['Runes','Gems','Keys, essences and tokens','RotW materials']);
  const isMaterial=item=>materialCategories.has(item.category);
  const isShared=place=>place.tab==='advanced'||place.tab.startsWith('shared');
  const characters=item=>isMaterial(item)?[]:[...new Set(item.locations.filter(p=>!isShared(p)).map(p=>p.character))];
  const ownershipLabel=item=>isMaterial(item)?'':[...new Set(item.locations.map(p=>isShared(p)?p.account:p.character+(p.tab==='inventory'?' · Inventory':'')))].join(', ');
  function locationLabel(item,place){
    if(place.tab==='advanced'){const section=item.category==='Runes'?'Runes':item.category==='Gems'?'Gems':'Materials';return place.account+' - '+section+' - x'+place.quantity;}
    if(place.tab.startsWith('shared')){const page=Number(place.tab.replace('shared',''))||place.tab.replace('shared','');return place.account+' - Shared Stash - Page '+page+' - x'+place.quantity+' - column '+(place.x+1)+', row '+(place.y+1);}
    const tab=place.tab==='personal'?'Personal Stash':place.tab==='inventory'?'Carried Inventory':place.tab;
    return place.character+' - '+place.account+' - '+tab+' - x'+place.quantity+' - column '+(place.x+1)+', row '+(place.y+1);
  }
  const typeLabels={'Helm':'Helms','Primal Helm':'Helms','Druid Pelt':'Helms','Circlet':'Helms','Gloves':'Gloves','Boots':'Boots','Belt':'Belts','Body Armor':'Body armor','Shield':'Shields','Auric Shield':'Shields','Head':'Shields','Grim':'Grimoires','Lcha':'Grand charms','Mcha':'Large charms','Scha':'Small charms','Csch':'Sunder charms','Cjwl':'Colossal jewels','Jewel':'Jewels','Ring':'Rings','Amulet':'Amulets','Sword':'Swords','Axe':'Axes','Bow':'Bows','Amazon Bow':'Bows','Crossbow':'Crossbows','Claw':'Claws','Club':'Clubs','Mace':'Maces','Hammer':'Hammers','Dagger':'Daggers','Javelin':'Javelins','Amazon Javelin':'Javelins','Spear':'Spears','Amazon Spear':'Spears','Polearm':'Polearms','Scepter':'Scepters','Staff':'Staves','Wand':'Wands','Orb':'Orbs','Throwing Axe':'Throwing axes','Throwing Knife':'Throwing knives','Rune':'Runes','Book':'Tomes','Rpot':'Rejuvenation potions'};
  function itemType(item){
    if(item.category==='Gems')return (item.item||item.name).split(' ').at(-1);
    if(item.category==='RotW materials')return (item.item||item.name).includes('Worldstone')?'Worldstone shards':'Other materials';
    if(item.category==='Keys, essences and tokens'){const name=item.item||item.name;return name.includes('Essence')?'Essences':name.includes('Token')?'Tokens':'Keys';}
    return typeLabels[item.itemType]||item.itemType||'Other';
  }
  const searchAliases={
    hoz:['herald of zakarum'],hoto:['heart of the oak'],cta:['call to arms'],soj:['stone of jordan'],bk:['bul kathos'],
    maras:['kaleidoscope'],viper:['vipermagi'],griff:['griffon eye'],griffons:['griffon eye'],nw:['nightwing veil'],
    occy:['oculus'],arach:['arachnid mesh'],pcomb:['paladin combat','pally combat'],scomb:['sorceress combat','sorc combat'],
    skiller:['skill charm','skills grand charm']
  };
  const statFields={
    fcr:['fcr','faster cast rate'],sockets:['sockets','socket','os'],resistance:['resistance','res','allres','all res'],
    defense:['defense','def'],magicfind:['magic find','mf'],quantity:['quantity','qty']
  };
  const normalized=value=>String(value??'').toLowerCase().replace(/[’']/g,'').replace(/[^a-z0-9%+.<>=-]+/g,' ').trim();
  function searchPlan(query=''){
    let text=normalized(query),ethereal=null;const comparisons=[];
    text=text.replace(/\b(?:non[- ]?eth(?:ereal)?|not eth(?:ereal)?)\b/g,()=>{ethereal=false;return' ';});
    text=text.replace(/\b(?:ethereal|eth)\b/g,()=>{ethereal=true;return' ';});
    text=text.replace(/\b(\d+)\s*os\b/g,(_,value)=>{comparisons.push({field:'sockets',operator:'=',value:Number(value)});return' ';});
    const names=Object.entries(statFields).flatMap(([field,aliases])=>aliases.map(alias=>({field,alias}))).sort((a,b)=>b.alias.length-a.alias.length);
    for(const {field,alias} of names){
      const escaped=alias.replace(/[.*+?^${}()|[\]\\]/g,'\\$&').replace(/\s+/g,'\\s+');
      const expression=new RegExp('\\b'+escaped+'\\s*(>=|<=|=|>|<)\\s*(\\d+(?:\\.\\d+)?)\\b','g');
      text=text.replace(expression,(_,operator,value)=>{comparisons.push({field,operator,value:Number(value)});return' ';});
    }
    const groups=text.split(/\s+/).filter(Boolean).map(term=>({term,aliased:!!searchAliases[term],alternatives:[term,...(searchAliases[term]||[])].map(value=>normalized(value).split(/\s+/))}));
    return{query:String(query),groups,comparisons,ethereal};
  }
  function editDistance(a,b){
    if(a===b)return 0;if(!a.length)return b.length;if(!b.length)return a.length;
    let previous=Array.from({length:b.length+1},(_,i)=>i);
    for(let i=1;i<=a.length;i++){const current=[i];for(let j=1;j<=b.length;j++)current[j]=Math.min(current[j-1]+1,previous[j]+1,previous[j-1]+(a[i-1]===b[j-1]?0:1));previous=current;}return previous[b.length];
  }
  function fuzzyWord(word,haystack,words){
    if(haystack.includes(word))return true;if(!/^[a-z]+$/.test(word)||word.length<4)return false;
    const allowance=word.length>=8?2:1;return words.some(candidate=>{if(Math.abs(candidate.length-word.length)>allowance)return false;if(editDistance(word,candidate)<=allowance)return true;if(candidate.length!==word.length)return false;for(let i=0;i<word.length-1;i++)if(word[i]===candidate[i+1]&&word[i+1]===candidate[i]&&word.slice(0,i)===candidate.slice(0,i)&&word.slice(i+2)===candidate.slice(i+2))return true;return false;});
  }
  function numericValues(item,field){
    if(field==='quantity')return[Number(item.quantity||0)];
    const rolls=normalized(item.rolls),patterns={
      sockets:[/(\d+(?:\.\d+)?)\s*(?:sockets?|os\b)/g],
      fcr:[/(\d+(?:\.\d+)?)\s*%?\s*(?:fcr|faster cast rate)/g],
      resistance:[/(\d+(?:\.\d+)?)\s*%?\s*(?:(?:all|fire|cold|lightning|light|poison)\s+)?(?:resistance|res\b)/g,/(?:(?:all|fire|cold|lightning|light|poison)\s+)?(?:resistance|res)\s*\+?(\d+(?:\.\d+)?)/g],
      defense:[/(\d+(?:\.\d+)?)\s*(?:defense|def\b)/g],magicfind:[/(\d+(?:\.\d+)?)\s*%?\s*(?:magic find|mf\b)/g]
    };const values=field==='sockets'&&item.sockets!==undefined?[Number(item.sockets||0)]:[];for(const pattern of patterns[field]||[])for(const match of rolls.matchAll(pattern))values.push(Number(match[1]));return values;
  }
  const compare=(actual,operator,wanted)=>operator==='='?actual===wanted:operator==='>'?actual>wanted:operator==='>='?actual>=wanted:operator==='<'?actual<wanted:actual<=wanted;
  function matchesSearch(item,plan){
    const haystack=normalized([item.name,item.item,item.originalItem,item.base,item.rolls,item.quality,item.category,itemType(item),item.itemType||'',item.eth?'ethereal':'',item.sockets?item.sockets+'os':'',...characters(item),...(item.locations||[]).map(place=>place.account)].join(' '));
    const words=haystack.split(/\s+/);if(plan.ethereal!==null&&!!item.eth!==plan.ethereal)return false;
    if(!plan.comparisons.every(rule=>numericValues(item,rule.field).some(value=>compare(value,rule.operator,rule.value))))return false;
    return plan.groups.every(group=>group.term==='armor'?itemType(item)==='Body armor':group.alternatives.some((phrase,index)=>phrase.every(word=>group.aliased&&index===0?haystack.includes(word):fuzzyWord(word,haystack,words))));
  }
  function filter(items,{query='',category='',character='',type='',quality='',selectedOnly=false,selected=new Set()}={}){
    const plan=searchPlan(query);
    return items.filter(item=>(!category||item.category===category)&&(!type||itemType(item)===type)&&(!quality||item.quality===quality)&&(!character||characters(item).includes(character))&&(!selectedOnly||selected.has(key(item)))&&matchesSearch(item,plan));
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
  function templateText(text,context={}){return String(text||'').replace(/\{\{(category|listing_count|total_quantity|priced_count)\}\}/g,(_,name)=>String(context[name]??''));}
  function exportPost(data,selected,prices={},template=null){
    const chosen=data.items.filter(item=>selected.has(key(item)));if(!chosen.length)return '';
    const hasPrices=chosen.some(item=>prices[key(item)]);
    const pricedCount=chosen.filter(item=>prices[key(item)]).length,context={listing_count:chosen.length,total_quantity:chosen.reduce((sum,item)=>sum+item.quantity,0),priced_count:pricedCount};
    const pricing=text=>templateText(text,context).replace('Prices coming next — quote the item name and # when choosing a roll.',(hasPrices?'Prices in FG — ':'')+'Quote the item name and # when choosing a roll. Ask for pricing on unpriced items.');
    const blocks=template?[template.mainHeader?.enabled?pricing(template.mainHeader.text):'',template.mainSubtext?.enabled?pricing(template.mainSubtext.text):''].filter(Boolean):[pricing(data.postHeader)];
    for(const category of new Set(chosen.map(item=>item.category))){
      const categoryItems=chosen.filter(i=>i.category===category),section=template?.categories?.[category],categoryContext={...context,category,listing_count:categoryItems.length,total_quantity:categoryItems.reduce((sum,item)=>sum+item.quantity,0),priced_count:categoryItems.filter(item=>prices[key(item)]).length};
      const lines=section?[section.header?.enabled?templateText(section.header.text,categoryContext):'',section.subtext?.enabled?templateText(section.subtext.text,categoryContext):''].filter(Boolean):[data.sectionHeaders[category]];let gem='';
      for(const item of categoryItems){
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
  const equipmentTypes={
    helm:['Helms'],weapon:['Swords','Axes','Bows','Crossbows','Claws','Clubs','Maces','Hammers','Daggers','Javelins','Spears','Polearms','Scepters','Staves','Wands','Orbs','Throwing axes','Throwing knives'],
    shield:['Shields'],armor:['Body armor'],gloves:['Gloves'],belt:['Belts'],boots:['Boots'],amulet:['Amulets'],ring:['Rings'],charm:['Small charms','Large charms','Grand charms','Sunder charms']
  };
  const packageTemplates={
    blizzard:{title:'Blizzard Sorceress',description:'Cold damage, skills and cast speed with familiar magic-find options.',keywords:['cold skills','cold damage','sorceress skills','fcr','magic find'],slots:[
      ['Helm','helm',['nightwings veil','harlequin crest']],['Weapon','weapon',['deaths fathom','the oculus','oculus','spirit']],['Shield','shield',['spirit','lidless wall']],['Armor','armor',['ormus robes','skin of the vipermagi','chains of honor']],['Gloves','gloves',['magefist','trang ouls claws']],['Belt','belt',['arachnid mesh','snowclash']],['Boots','boots',['war traveler','sandstorm trek']],['Amulet','amulet',['maras kaleidoscope']],['Ring 1','ring',['stone of jordan','bul kathos']],['Ring 2','ring',['stone of jordan','bul kathos']],['Unique charm','charm',['hellfire torch','sorceress','annihilus','gheeds fortune']],['Cold skiller','charm',['cold sorceress','cold skills']]
    ]},
    nova:{title:'Nova Sorceress',description:'Lightning damage, cast speed and mana-focused equipment candidates.',keywords:['lightning skills','lightning damage','fcr','mana','energy'],slots:[
      ['Helm','helm',['griffons eye','harlequin crest']],['Weapon','weapon',['infinity','crescent moon','eschutas temper','the oculus','oculus']],['Shield','shield',['spirit','lidless wall']],['Armor','armor',['skin of the vipermagi','ormus robes','chains of honor']],['Gloves','gloves',['magefist','frostburn','trang ouls claws']],['Belt','belt',['arachnid mesh']],['Boots','boots',['silkweave','sandstorm trek']],['Amulet','amulet',['maras kaleidoscope']],['Ring 1','ring',['stone of jordan']],['Ring 2','ring',['stone of jordan']],['Unique charm','charm',['hellfire torch','sorceress','annihilus']],['Lightning skiller','charm',['lightning sorceress','lightning skills']]
    ]},
    hammerdin:{title:'Hammerdin',description:'Paladin skills, cast speed and the standard teleporting hammer setup.',keywords:['paladin skills','combat skills','fcr','all res'],slots:[
      ['Helm','helm',['harlequin crest','crown of ages']],['Weapon','weapon',['heart of the oak','wizardspike','spirit']],['Shield','shield',['herald of zakarum','spirit']],['Armor','armor',['enigma','skin of the vipermagi','chains of honor']],['Gloves','gloves',['magefist','trang ouls claws']],['Belt','belt',['arachnid mesh','verdungos']],['Boots','boots',['war traveler','sandstorm trek']],['Amulet','amulet',['maras kaleidoscope']],['Ring 1','ring',['stone of jordan','bul kathos']],['Ring 2','ring',['stone of jordan','bul kathos']],['Unique charm','charm',['hellfire torch','paladin','annihilus']],['Combat skiller','charm',['combat paladin','paladin combat','pally combat']]
    ]}
  };
  function packageTemplateList(){return Object.entries(packageTemplates).map(([id,value])=>({id,title:value.title,description:value.description}));}
  function packageKind(item){for(const [kind,types] of Object.entries(equipmentTypes))if(types.includes(itemType(item)))return kind;return null;}
  function packageBuild(items,templateOrId){
    const template=typeof templateOrId==='string'?packageTemplates[templateOrId]:templateOrId;if(!template||!Array.isArray(template.slots))throw new Error('Unknown character package.');const used=new Set(),slots=[];
    for(const definition of template.slots){
      const [label,kind,wants,slotId]=Array.isArray(definition)?[...definition,undefined]:[definition.label,definition.kind,definition.wants,definition.id];if(!label||!equipmentTypes[kind]||!Array.isArray(wants))continue;
      const types=equipmentTypes[kind];const candidates=items.filter(item=>types.includes(itemType(item))).map(item=>{
        const text=normalized([item.name,item.item,item.base,item.rolls,item.quality].join(' '));let score=0,reason='Matches '+label.toLowerCase()+' slot';
        const preferred=[];wants.forEach((want,index)=>{if(text.includes(normalized(want))){score+=120-index*8;preferred.push(want);}});if(preferred.length)reason='Preferred: '+preferred.join(' + ');
        for(const keyword of template.keywords||[])if(text.includes(normalized(keyword)))score+=6;
        if(item.quality==='Runeword'||item.quality==='Unique'||item.quality==='Set')score+=3;
        return{item,score,reason};
      }).filter(candidate=>template.custom?candidate.score>=100:label.includes('skiller')?candidate.score>=100:label==='Unique charm'?candidate.item.quality==='Unique'&&candidate.score>=100:true).sort((a,b)=>b.score-a.score||a.item.name.localeCompare(b.item.name));
      const available=candidates.find(candidate=>!used.has(key(candidate.item)))||candidates[0]||null;if(available)used.add(key(available.item));
      slots.push({id:slotId||label,label,kind,candidates:candidates.slice(0,15),selectedKey:available?key(available.item):null});
    }
    return{id:typeof templateOrId==='string'?templateOrId:template.id,title:template.title,description:template.description,slots};
  }
  return{key,itemType,characters,ownershipLabel,locationLabel,isMaterial,isShared,filter,searchPlan,reconcile,muleOptions,inventoryScope,exportPost,priceEntry,priceLabel,pricingSummary,priceSearchURL,colorValue,parseBBCode,formatSelection,syncDraft,tradeList,tradeListCSV,readTradeList,restoreTradeList,packageTemplateList,packageKind,packageBuild};
})();
