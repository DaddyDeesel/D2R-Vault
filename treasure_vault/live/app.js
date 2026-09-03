'use strict';
(()=>{
  const el=id=>document.getElementById(id);
  const ui=Object.fromEntries(['connection-state','last-checked','refresh','collections','source-time','collection-title','result-count','search','character','category','select-matching','clear-selection','selected-only','selection-count','export','notice','export-panel','close-export','post-text','copy-post','download-post','export-status','item-detail','items','page-status','previous','next','format-bold','format-italic','format-underline','format-color','apply-color','rebuild-post','restore-draft','draft-warning','draft-warning-text','accept-draft','post-preview','composer-help','set-prices','price-summary','pricing-panel','close-pricing','bulk-price-editor','mule-summary','mule-list','all-mules','clear-mules','settings','settings-panel','close-settings','settings-form','database-path','browse-database','save-settings','settings-status','quantity-breakdown','changes-summary','changes-status','clear-changes','changes-list','changes-totals','changes-filters','log-include-inventory','log-settings-status','changes-scope','open-log','close-log','changes-panel','log-collection-list','log-all-collections','log-no-collections','item-type','item-quality','clear-refinements','refinement-heading'].map(id=>[id,el(id)]));
  let data={items:[],images:{},sectionHeaders:{},postHeader:''};let selected=new Set();let category='';let page=0;const pageSize=16;let busy=false;let downloadURL='';let detailKey=null;let knownVersion=null;let hasCurrentConnection=false;let connectionProblem=false;
  let draftStorage='d2r-treasure-vault-draft-v1';let draft=null;let backupDraft=null;let previewText=null;let downloadText=null;let savedState='';
  let priceStorage='d2r-treasure-vault-prices-v1';const prices=Object.create(null);
  let muleStorage='d2r-treasure-vault-mules-v1';let mules=new Set();let rawData=null;
  let activeSource=null;let switchingDatabase=false;let setupPrompted=false;
  function useSource(incoming){
    if(!incoming.sourceId||incoming.sourceId===activeSource)return;
    activeSource=incoming.sourceId;
    const baseKeys=['d2r-treasure-vault-draft-v1','d2r-treasure-vault-prices-v1','d2r-treasure-vault-mules-v1'];
    const keys=baseKeys.map(key=>key+':'+activeSource);
    try{if(activeSource===incoming.legacySourceId)for(let i=0;i<keys.length;i++){if(localStorage.getItem(keys[i])===null){const prior=localStorage.getItem(baseKeys[i]);if(prior!==null)localStorage.setItem(keys[i],prior);}}}catch{}
    [draftStorage,priceStorage,muleStorage]=keys;
    draft=null;backupDraft=null;savedState='';previewText=null;downloadText=null;selected=new Set();mules=new Set();
    for(const key of Object.keys(prices))delete prices[key];
  try{const saved=JSON.parse(localStorage.getItem(muleStorage)||'[]');if(Array.isArray(saved))mules=new Set(saved.filter(id=>typeof id==='string'));}catch{}
  try{const saved=JSON.parse(localStorage.getItem(priceStorage)||'{}');for(const [id,price] of Object.entries(saved)){try{prices[id]=VaultLogic.priceEntry(price.amount,price.basis);}catch{}}}catch{}
  try{const saved=JSON.parse(localStorage.getItem(draftStorage)||'null');if(saved&&typeof saved.text==='string'&&typeof saved.base==='string'){draft={text:saved.text,base:saved.base,dirty:saved.text!==saved.base,stale:false};if(Array.isArray(saved.selected))selected=new Set(saved.selected.filter(x=>typeof x==='string'));if(saved.backup&&typeof saved.backup.text==='string'&&typeof saved.backup.base==='string')backupDraft=saved.backup;}}catch{}
    category='';ui['item-type'].value='';ui['item-quality'].value='';page=0;detailKey=null;ui['item-detail'].hidden=true;ui['export-panel'].hidden=true;ui['pricing-panel'].hidden=true;ui.search.value='';ui['selected-only'].checked=false;
  }
  const make=(tag,text,cls)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node;};
  const time=value=>value?new Date(value).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit'}):'—';
  const notify=text=>{ui.notice.textContent=text;ui.notice.hidden=!text;};
  let changeState=null;let changesStorage='';let changeFilter='all';let changesSource=null;let includeLogInventory=false;let excludedLogCollections=[];let logControlsSignature='';
  const logCollections=['Runes','Gems','Keys, essences and tokens','RotW materials','Runewords','Charms','Jewels','Rings and amulets','Uniques - armor','Uniques - weapons','Set items','Bases','Magic and rare gear','Consumables'];
  function availableLogCollections(){return [...new Set([...logCollections,...(rawData?.items||[]).map(i=>i.category)])];}
  function logCollectionControls(){
    const names=availableLogCollections(),signature=JSON.stringify([changesSource,names,excludedLogCollections]);if(signature===logControlsSignature)return;logControlsSignature=signature;
    ui['log-collection-list'].replaceChildren();
    for(const name of names){const label=make('label',undefined,'log-collection-option'),checkbox=make('input');checkbox.type='checkbox';checkbox.checked=!excludedLogCollections.includes(name);checkbox.onchange=()=>{excludedLogCollections=checkbox.checked?excludedLogCollections.filter(c=>c!==name):[...excludedLogCollections,name];saveLogCollections();};label.append(checkbox,make('span',name));ui['log-collection-list'].append(label);}
    ui['log-all-collections'].disabled=false;ui['log-no-collections'].disabled=false;
  }
  function saveLogCollections(){
    if(!rawData)return;
    let saved=true;try{localStorage.setItem('d2r-treasure-vault-log-collections-v1:'+rawData.sourceId,JSON.stringify(excludedLogCollections));}catch{saved=false;}
    trackInventory(rawData,true);
    const enabled=availableLogCollections().filter(c=>!excludedLogCollections.includes(c));
    ui['log-settings-status'].textContent=(saved?'Collection preferences saved. ':'Browser storage unavailable; these preferences last only while this page is open. ')+(enabled.length?'Tracking '+enabled.length+' collections from the current capture.':'Logging paused: no collections selected.');
  }
  function persistChanges(){
    try{localStorage.setItem(changesStorage,JSON.stringify(changeState));ui['changes-status'].textContent='Last 10 change summaries are saved in this browser for this database and log mode.';}
    catch{ui['changes-status'].textContent='Browser storage is full or unavailable. This change history will only last while the page stays open.';}
  }
  function trackInventory(incoming,rebase=false){
    if(changesSource!==incoming.sourceId){
      changesSource=incoming.sourceId;includeLogInventory=false;excludedLogCollections=[];
      try{includeLogInventory=localStorage.getItem('d2r-treasure-vault-log-inventory-v1:'+changesSource)==='true';}catch{}
      try{const stored=JSON.parse(localStorage.getItem('d2r-treasure-vault-log-collections-v1:'+changesSource)||'[]');if(Array.isArray(stored))excludedLogCollections=stored.filter(c=>typeof c==='string');}catch{}
      ui['log-settings-status'].textContent='';changeFilter='all';
    }
    ui['log-include-inventory'].checked=includeLogInventory;ui['log-include-inventory'].disabled=false;
    ui['changes-scope'].textContent=includeLogInventory?'Stashes + carried inventory · All captured characters, regardless of Select Mules. Change this in Settings.':'Stashes only · Shared stashes, materials tabs and all personal stash tabs. Carried inventory is excluded. Change this in Settings.';
    const tracked=availableLogCollections().filter(c=>!excludedLogCollections.includes(c));ui['changes-scope'].textContent+=' '+(tracked.length?(excludedLogCollections.length?'Logging: '+tracked.join(', ')+'.':'All collections are logged.'):'Logging paused: no collections selected.');logCollectionControls();
    const storage=(includeLogInventory?'d2r-treasure-vault-changes-v1:':'d2r-treasure-vault-stash-changes-v1:')+incoming.sourceId;
    if(changesStorage!==storage||!changeState){
      changesStorage=storage;changeState=null;
      try{const stored=JSON.parse(localStorage.getItem(changesStorage)||'null');if(stored?.sourceId===incoming.sourceId&&Array.isArray(stored.baseline?.items)&&Array.isArray(stored.batches))changeState=stored;}catch{}
    }
    const scoped=VaultFeatures.historyScope(incoming,includeLogInventory);
    if(rebase&&changeState)changeState={...changeState,baseline:VaultFeatures.snapshot(scoped)};
    try{changeState=VaultFeatures.updateHistory(changeState,scoped,excludedLogCollections);}catch{changeState=VaultFeatures.updateHistory(null,scoped);}
    persistChanges();renderChanges();
  }
  function renderChanges(){
    const batches=VaultFeatures.historyBatches(changeState?.batches||[],excludedLogCollections);ui['changes-list'].replaceChildren();ui['changes-totals'].replaceChildren();ui['clear-changes'].disabled=!batches.length;
    const totals=batches.reduce((sum,b)=>{const t=b.totals||VaultFeatures.summarizeEvents(b.events);for(const key of Object.keys(sum))sum[key]+=t[key];return sum;},{added:0,removed:0,changed:0});
    const incomplete=batches.some(b=>b.partial||(!b.totals&&b.total>b.events.length));
    ui['changes-summary'].textContent=batches.length?'+'+totals.added.toLocaleString()+' added · −'+totals.removed.toLocaleString()+' removed'+(incomplete?' (retained entries)':''):'Watching for your next inventory change';
    for(const [kind,label] of [['added','Units added'],['removed','Units removed'],['changed','Other changes']]){
      const card=make('div',undefined,'change-total '+kind);card.append(make('strong',(kind==='added'?'+':kind==='removed'?'−':'')+totals[kind].toLocaleString()),make('span',label));ui['changes-totals'].append(card);
    }
    let shown=0;
    for(const batch of batches){
      const matches=batch.events.filter(e=>changeFilter==='all'||VaultFeatures.describeEvent(e).tone===changeFilter);
      if(!matches.length&&batch.total<=batch.events.length)continue;
      const section=make('section',undefined,'change-batch');section.append(make('h4',new Date(batch.at).toLocaleString()),make('p','Captured inventory update · '+batch.total+' changed listing'+(batch.total===1?'':'s'),'composer-hint'));
      for(const event of matches){
        shown++;const item=event.after||event.before,e=VaultFeatures.describeEvent(event);const row=make('article',undefined,'change-entry '+e.tone);
        const badge=make('div',e.amount,'change-amount');const body=make('div',undefined,'change-body');const title=make('div',undefined,'change-title');title.append(make('span',e.label,'change-kind'),make('strong',item.name));body.append(title,make('p',e.detail,'change-detail'));
        const details=make('details',undefined,'change-location');details.append(make('summary','View '+(event.before&&event.after?'before & after':'location')));
        if(event.kinds.includes('moved'))details.append(make('p',event.inferred?'Possible move: matched identical recorded stats.':'Item location changed.','change-detail'));
        if(event.kinds.includes('quantity')&&event.before.quantity===event.after.quantity)details.append(make('p','Same total quantity, redistributed between locations.','change-detail'));
        if(event.kinds.includes('updated'))details.append(make('p','Before: '+(event.before.rolls||event.before.quality)+' · Now: '+(event.after.rolls||event.after.quality),'change-detail'));
        if(event.before)details.append(make('p','Before: '+event.before.locations.map(p=>VaultLogic.locationLabel(event.before,p)).join('; '),'change-detail'));
        if(event.after)details.append(make('p','Now: '+event.after.locations.map(p=>VaultLogic.locationLabel(event.after,p)).join('; '),'change-detail'));
        body.append(details);row.append(badge,body);
        const current=rawData?.items.find(i=>VaultLogic.key(i)===(event.after?.key));
        if(current){const button=make('button','Locate','button quiet');button.type='button';button.setAttribute('aria-label','Locate '+item.name);button.onclick=()=>{const scoped=data.items.find(i=>i.key===current.key);locate(scoped||current);ui['item-detail'].scrollIntoView({block:'nearest',behavior:'smooth'});};row.append(button);}section.append(row);
      }
      if(batch.total>batch.events.length)section.append(make('p','Details retained for the first '+batch.events.length+' of '+batch.total+' changed listings. Filters apply to these retained entries.','composer-hint'));
      ui['changes-list'].append(section);
    }
    if(!shown)ui['changes-list'].append(make('p',availableLogCollections().every(c=>excludedLogCollections.includes(c))?'Logging paused. Choose at least one collection in Settings to record new activity.':batches.length?'No '+(changeFilter==='all'?'matching':changeFilter)+' entries in the saved log.':'Your starting inventory is saved. Add, remove, or move items and capture them in D2R Manager. Changes will appear here automatically.','change-empty'));
    for(const button of ui['changes-filters'].querySelectorAll('button'))button.setAttribute('aria-pressed',String(button.dataset.changeFilter===changeFilter));
  }
  function locatorCard(item,place){
    const card=make('section',undefined,'locator-card');const label=VaultLogic.locationLabel(item,place);card.append(make('h4',label));
    const rect=VaultFeatures.footprint(item,place);
    if(rect.material){
      const material=make('div',undefined,'material-locator');if(item.image&&rawData?.images[item.image]){const image=make('img');image.src=rawData.images[item.image];image.alt='';material.append(image);}material.append(make('strong',item.item+' · x'+place.quantity.toLocaleString()));card.append(material,make('p','Find '+item.item+' in this account’s materials tab. The database does not record its slot position.','composer-hint'));
    }else if(rect.invalid){card.append(make('p','The recorded position is outside the known grid or missing. Use the account and tab above; a grid position cannot be drawn reliably.','composer-hint'));}
    else{
      const frame=make('div',undefined,'locator-frame');const axes=make('div',undefined,'locator-axis');for(let x=1;x<=rect.cols;x++)axes.append(make('span',x));frame.append(axes);
      const grid=make('div',undefined,'locator-grid');grid.style.gridTemplateRows='repeat('+rect.rows+', 1fr)';grid.style.aspectRatio=rect.cols+'/'+rect.rows;grid.setAttribute('role','group');grid.setAttribute('aria-label','Recorded '+(place.tab==='inventory'?'inventory':'stash')+' grid. Highlighted '+item.name+' at column '+(rect.x+1)+', row '+(rect.y+1)+'.');
      for(let y=0;y<rect.rows;y++)for(let x=0;x<rect.cols;x++){const cell=make('span',x===0?y+1:undefined,'locator-cell');cell.style.gridColumn=String(x+1);cell.style.gridRow=String(y+1);cell.setAttribute('aria-hidden','true');grid.append(cell);}
      for(const entry of VaultFeatures.gridItems(rawData||data,place)){
        const target=entry.item.key===item.key&&VaultFeatures.position(entry.location)===VaultFeatures.position(place);const shape=make('div',undefined,'locator-object'+(target?' locator-target':''));shape.style.gridColumn=(entry.rect.x+1)+' / span '+entry.rect.width;shape.style.gridRow=(entry.rect.y+1)+' / span '+entry.rect.height;shape.title=entry.item.name;
        if(entry.item.image&&(rawData||data).images[entry.item.image]){const image=make('img');image.src=(rawData||data).images[entry.item.image];image.alt=target?item.name:'';shape.append(image);}else shape.append(make('span',target?'◆':'·'));grid.append(shape);
      }
      frame.append(grid);card.append(frame,make('p',rect.known?'Gold outline: '+item.name+' · '+rect.width+' × '+rect.height+' cells. Nearby items are dimmed.':'Gold marks the recorded origin cell; the item’s full size is not available.','composer-hint'));
    }
    const copy=make('button','Copy location','button quiet');copy.type='button';copy.onclick=async()=>{try{await navigator.clipboard.writeText(item.name+' — '+label);copy.textContent='Location copied';}catch{copy.textContent='Copy unavailable — use the location above';}};card.append(copy);return card;
  }
  function muleControls(){
    ui['mule-list'].replaceChildren();const characters=VaultLogic.muleOptions(rawData);
    for(const character of characters){
      const label=make('label',undefined,'mule-option');const checkbox=make('input');checkbox.type='checkbox';checkbox.checked=mules.has(character.key);checkbox.disabled=!(character.personalCount+character.inventoryCount)&&!checkbox.checked;
      checkbox.onchange=()=>{if(checkbox.checked)mules.add(character.key);else mules.delete(character.key);changeScope();};
      const description=make('span');description.append(make('strong',character.name),make('small',character.account+' · '+character.personalCount+' personal stash · '+character.inventoryCount+' inventory'));label.append(checkbox,description);ui['mule-list'].append(label);
    }
    const chosen=characters.filter(c=>mules.has(c.key));ui['mule-summary'].textContent=chosen.length?chosen.length+' characters included':'Shared stash only';
  }
  function changeScope(){
    if(!rawData)return;
    let saved=true;try{localStorage.setItem(muleStorage,JSON.stringify([...mules]));}catch{saved=false;}
    data=VaultLogic.inventoryScope(rawData,mules);const before=selected.size;selected=VaultLogic.reconcile(selected,data.items);page=0;collectionControls();muleControls();render();
    if(detailKey){const item=data.items.find(i=>VaultLogic.key(i)===detailKey);if(item)locate(item);else{ui['item-detail'].hidden=true;detailKey=null;}}
    notify('Inventory sources updated.'+(before>selected.size?' '+(before-selected.size)+' selections outside this scope were removed.':'')+(!saved?' Browser storage unavailable; choose your mules again after reopening.':''));
  }
  function priceEditor(keys,initial){
    const form=make('form',undefined,'price-editor');const amountLabel=make('label','Asking price (FG)');const amount=make('input');amount.type='number';amount.min='0.01';amount.max='1000000000';amount.step='0.01';amount.placeholder='e.g. 5';amount.required=true;amount.value=initial?.amount||'';amountLabel.append(amount);
    const basisLabel=make('label','Price applies to');const basis=make('select');for(const [value,label] of [['each','Each item'],['lot','Whole listing']]){const option=make('option',label);option.value=value;basis.append(option);}basis.value=initial?.basis||'each';basisLabel.append(basis);
    const save=make('button','Save price','button primary');save.type='submit';const clear=make('button','Clear price','button quiet');clear.type='button';const status=make('span',undefined,'price-editor-status');status.setAttribute('role','status');
    function apply(remove){
      const valid=new Set(data.items.map(VaultLogic.key));const targets=[...keys()].filter(id=>valid.has(id));if(!targets.length){status.textContent='Select a listing first.';return;}
      let value;try{if(!remove)value=VaultLogic.priceEntry(amount.value,basis.value);}catch(error){status.textContent=error.message;return;}
      for(const id of targets){if(remove)delete prices[id];else prices[id]=value;}
      let saved=true;try{localStorage.setItem(priceStorage,JSON.stringify(prices));}catch{saved=false;}
      render();status.textContent=(remove?'Cleared prices for ':'Priced ')+targets.length+' listing'+(targets.length===1?'':'s')+'.'+(saved?' Saved in this browser.':' Browser storage unavailable; these prices will be lost when you close this page.');if(remove)amount.value='';
    }
    form.onsubmit=event=>{event.preventDefault();apply(false);};clear.onclick=()=>apply(true);form.append(amountLabel,basisLabel,save,clear,status);
    return form;
  }
  function filtered(){return VaultLogic.filter(data.items,{query:ui.search.value,character:ui.character.value,category,type:ui['item-type'].value,quality:ui['item-quality'].value,selectedOnly:ui['selected-only'].checked,selected});}
  function collectionControls(){
    const counts=new Map();for(const item of data.items)counts.set(item.category,(counts.get(item.category)||0)+1);
    if(category&&!counts.has(category))category='';
    ui.collections.replaceChildren();ui.category.replaceChildren();
    for(const [value,label,count] of [['','All treasures',data.items.length],...[...counts].map(([name,n])=>[name,name,n])]){
      const button=make('button',undefined,'collection-button');button.type='button';button.setAttribute('aria-pressed',String(category===value));button.append(make('span',label),make('span',count));button.onclick=()=>{category=value;ui['item-type'].value='';ui['item-quality'].value='';page=0;collectionControls();render();};ui.collections.append(button);
      const option=make('option',label);option.value=value;ui.category.append(option);
    }
    ui.category.value=category;
    const current=ui.character.value;ui.character.replaceChildren();const all=make('option','All characters');all.value='';ui.character.append(all);
    for(const name of [...new Set(data.items.flatMap(VaultLogic.characters))].sort((a,b)=>a.localeCompare(b))){const option=make('option',name);option.value=name;ui.character.append(option);}
    if([...ui.character.options].some(o=>o.value===current))ui.character.value=current;
  }
  function refinementControls(){
    const items=data.items.filter(i=>!category||i.category===category);
    for(const [id,valueOf,label] of [['item-type',VaultLogic.itemType,'All item types'],['item-quality',i=>i.quality,'All qualities']]){
      const control=ui[id],current=control.value,counts=new Map();for(const item of items){const value=valueOf(item);counts.set(value,(counts.get(value)||0)+1);}
      control.replaceChildren();const all=make('option',label);all.value='';control.append(all);
      for(const [value,count] of [...counts].sort(([a],[b])=>a.localeCompare(b))){const option=make('option',value+' ('+count+')');option.value=value;control.append(option);}
      if(counts.has(current))control.value=current;
      control.disabled=!counts.size;
    }
    ui['refinement-heading'].textContent='Narrow '+(category||'all treasures');ui['clear-refinements'].disabled=!ui['item-type'].value&&!ui['item-quality'].value;
  }
  function saveDraft(){
    if(!draft||knownVersion===null)return;
    const state=JSON.stringify({...draft,selected:[...selected],backup:backupDraft});if(state===savedState)return;
    try{localStorage.setItem(draftStorage,state);savedState=state;}catch{ui['composer-help'].textContent='Highlight text, then apply formatting. Browser storage is unavailable; copy your draft before closing.';}
  }
  function renderPreview(text){
    if(text===previewText)return;previewText=text;
    const build=node=>{
      if(typeof node==='string')return document.createTextNode(node);
      const tag={root:'div',b:'strong',i:'em',u:'u',center:'div',color:'span'}[node.tag];const element=document.createElement(tag);
      if(node.tag==='center')element.className='bb-center';if(node.tag==='color')element.style.color=node.color;
      for(const child of node.children)element.append(build(child));return element;
    };
    ui['post-preview'].replaceChildren(build(VaultLogic.parseBBCode(text)));
  }
  function exportText(){
    if(knownVersion===null)return;
    draft=VaultLogic.syncDraft(draft,VaultLogic.exportPost(data,selected,prices));
    const text=draft.text;
    if(ui['post-text'].value!==text)ui['post-text'].value=text;
    renderPreview(text);
    if(downloadText!==text){
      if(downloadURL)URL.revokeObjectURL(downloadURL);downloadURL='';downloadText=text;
      if(text){downloadURL=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));ui['download-post'].href=downloadURL;}else ui['download-post'].removeAttribute('href');
    }
    const allowed=!!text&&hasCurrentConnection&&!draft.stale;
    ui['copy-post'].disabled=!allowed;ui['download-post'].hidden=!allowed;
    ui['draft-warning'].hidden=!draft.stale;ui['draft-warning-text'].textContent='The inventory, selection or prices changed. Your edits were kept. Review the draft and keep it, or rebuild from the current selection.';
    ui['accept-draft'].disabled=!hasCurrentConnection;ui['restore-draft'].hidden=!backupDraft;
    ui['export-status'].textContent=!hasCurrentConnection?'Reconnect to the stash before exporting.':draft.stale?'Review inventory changes before exporting.':text?(draft.dirty?'Edited draft':'Generated draft')+' · '+selected.size+' selected listings · '+text.length.toLocaleString()+' characters':'Select a treasure to begin.';
    saveDraft();
  }
  function selectionStatus(){ui['selection-count'].textContent=selected.size+' selected';ui.export.disabled=(!selected.size&&!draft?.text)||!hasCurrentConnection;ui['clear-selection'].disabled=!selected.size;ui['set-prices'].disabled=!selected.size;const summary=VaultLogic.pricingSummary(data.items,selected,prices);ui['price-summary'].textContent=selected.size?summary.priced+' priced · '+summary.unpriced+' unpriced · '+summary.total.toLocaleString(undefined,{maximumFractionDigits:2})+' fg asking total for priced stock':'Select listings to price your sale.';if(draft||!ui['export-panel'].hidden)exportText();}
  function locate(item){
    detailKey=VaultLogic.key(item);const panel=ui['item-detail'];panel.hidden=false;panel.replaceChildren();
    const heading=make('div',undefined,'panel-heading');const title=make('div');title.append(make('p','LOCATION IN YOUR VAULT','eyebrow'),make('h3',item.name));const close=make('button','Close','button quiet');close.type='button';close.onclick=()=>{panel.hidden=true;detailKey=null;};heading.append(title,close);panel.append(heading);
    panel.append(make('p',[item.base,item.eth?'Ethereal':'',item.sockets?item.sockets+' sockets':'',item.contents,item.rolls].filter(Boolean).join(' · '),'detail-description'));
    const cards=make('div',undefined,'locator-cards');for(const place of item.locations)cards.append(locatorCard(item,place));panel.append(cards);
    if(data.items.some(i=>VaultLogic.key(i)===VaultLogic.key(item)))panel.append(make('h4','Asking price'),priceEditor(()=>[VaultLogic.key(item)],prices[VaultLogic.key(item)]));
    else panel.append(make('p','This item is outside your selected mule scope. Include its character in Settings → Select Mules to list it for sale.','composer-hint'));

  }
  function render(){
    refinementControls();
    const rows=filtered();const pages=Math.max(1,Math.ceil(rows.length/pageSize));page=Math.min(page,pages-1);
    ui['collection-title'].textContent=category||'All treasures';ui['result-count'].textContent=rows.length.toLocaleString()+' listings · '+rows.reduce((n,i)=>n+i.quantity,0).toLocaleString()+' total quantity (including stacks)';ui.items.replaceChildren();const totals=new Map();for(const item of rows)totals.set(item.category,(totals.get(item.category)||0)+item.quantity);ui['quantity-breakdown'].replaceChildren();for(const [name,total] of totals){const row=make('div');row.append(make('dt',name),make('dd',total.toLocaleString()));ui['quantity-breakdown'].append(row);}
    for(const item of rows.slice(page*pageSize,(page+1)*pageSize)){
      const key=VaultLogic.key(item);const tr=make('tr',undefined,'item-row'+(selected.has(key)?' selected':''));const first=make('td');const identity=make('div',undefined,'item-identity');
      const checkbox=make('input');checkbox.type='checkbox';checkbox.checked=selected.has(key);checkbox.setAttribute('aria-label','Select '+item.name);checkbox.onchange=()=>{if(checkbox.checked)selected.add(key);else selected.delete(key);tr.classList.toggle('selected',checkbox.checked);selectionStatus();if(ui['selected-only'].checked)render();};identity.append(checkbox);
      if(item.image&&data.images[item.image]){const img=make('img',undefined,'item-art');img.src=data.images[item.image];img.alt='';identity.append(img);}else{const placeholder=make('span','◇','item-art-placeholder');placeholder.setAttribute('aria-hidden','true');identity.append(placeholder);}
      const content=make('div',undefined,'item-text');const name=make('button',item.name,'item-name');name.type='button';name.dataset.quality=item.quality;name.setAttribute('aria-label','Locate '+item.name);name.onclick=()=>{locate(item);ui['item-detail'].scrollIntoView({block:'nearest',behavior:'smooth'});};name.title='Show item locator';content.append(name,make('span',[item.quality,item.eth?'ETH':'',item.sockets?item.sockets+'os':''].filter(Boolean).join(' · '),'item-meta'));const owner=VaultLogic.ownershipLabel(item);if(owner)content.append(make('span',owner,'item-character'));identity.append(content);first.append(identity);tr.append(first);
      const rolls=make('td');if(item.base)rolls.append(make('div',item.base,'base-name'));rolls.append(make('div',item.rolls||'—','rolls'));const priceCell=make('td',undefined,'price-column');const priceButton=make('button',VaultLogic.priceLabel(prices[key]),'price-button');priceButton.type='button';priceButton.setAttribute('aria-label','Edit price for '+item.name);priceButton.onclick=()=>{locate(item);ui['item-detail'].scrollIntoView({block:'nearest',behavior:'smooth'});};const actions=make('div',undefined,'price-actions');const searchPrice=make('a','Search Price','price-button search-price');searchPrice.href=VaultLogic.priceSearchURL(item);searchPrice.target='_blank';searchPrice.rel='noopener noreferrer';searchPrice.title='Search d2jsp prices with Google (opens a new tab)';searchPrice.setAttribute('aria-label','Search d2jsp prices for '+item.item+' (opens a new tab)');actions.append(priceButton,searchPrice);priceCell.append(actions);tr.append(rolls,make('td',item.quantity.toLocaleString(),'quantity'),priceCell);ui.items.append(tr);
    }
    if(!rows.length){const tr=make('tr');const td=make('td',data.items.length?'No treasures match these filters.':'No eligible stash items found.','empty');td.colSpan=4;tr.append(td);ui.items.append(tr);}
    ui['page-status'].textContent='Page '+(page+1)+' of '+pages;ui.previous.disabled=page===0;ui.next.disabled=page===pages-1;ui['select-matching'].disabled=!rows.length;selectionStatus();
  }
  async function poll(){
    if(busy)return;busy=true;
    try{
      const response=await fetch('/api/status',{cache:'no-store'});if(!response.ok)throw new Error('Status unavailable');const status=await response.json();
      hasCurrentConnection=status.ready&&!status.error&&!switchingDatabase;
      if(status.needsSetup&&!setupPrompted){setupPrompted=true;ui.settings.onclick();}
      ui['connection-state'].textContent=status.error?'Stash unavailable':status.refreshing?'Checking stash…':status.ready?'Stash connected':'Opening the vault…';ui['connection-state'].dataset.state=status.error?'error':status.ready?'live':'loading';
      if(status.needsSetup)ui['connection-state'].textContent='Choose your items.db in Settings';
      ui['last-checked'].textContent=status.lastChecked?'Checked '+time(status.lastChecked):'Reading stash records';ui.refresh.disabled=status.refreshing;
      if(status.error){connectionProblem=true;notify(status.error);}else if(connectionProblem){connectionProblem=false;notify('Stash reader reconnected.');}
      if(status.ready&&status.version!==knownVersion){
        const result=await fetch('/api/inventory',{cache:'no-store'});if(!result.ok)throw new Error('Inventory unavailable');const incoming=await result.json();
        useSource(incoming);rawData=incoming;trackInventory(incoming);const scoped=VaultLogic.inventoryScope(incoming,mules);
        const previousCount=selected.size;selected=VaultLogic.reconcile(selected,scoped.items);const removed=previousCount-selected.size;const updating=knownVersion!==null;
        data=scoped;knownVersion=incoming.version;collectionControls();muleControls();render();
        if(detailKey){const item=data.items.find(i=>VaultLogic.key(i)===detailKey);if(item)locate(item);else{ui['item-detail'].hidden=true;detailKey=null;}}
        if(!status.error)notify(updating?'Stash updated at '+time(incoming.updatedAt)+'.'+(removed?' '+removed+' unavailable selection'+(removed===1?' was':'s were')+' removed.':' Your remaining selections were kept.'):'');
        ui['source-time'].textContent=incoming.sourceCaptured?'Latest capture: '+new Date(incoming.sourceCaptured).toLocaleString():'';
      }
      selectionStatus();
    }catch{
      hasCurrentConnection=false;connectionProblem=true;ui['connection-state'].textContent='Reader not connected';ui['connection-state'].dataset.state='error';ui.refresh.disabled=false;notify('The local stash reader is unavailable. Reopen D2R Treasure Vault to reconnect. Your last inventory and selections remain visible.');selectionStatus();
    }finally{busy=false;}
  }
  ui.search.addEventListener('input',()=>{page=0;render();});ui.character.addEventListener('change',()=>{page=0;render();});ui.category.addEventListener('change',()=>{category=ui.category.value;ui['item-type'].value='';ui['item-quality'].value='';page=0;collectionControls();render();});ui['selected-only'].onchange=()=>{page=0;render();};
  ui.previous.onclick=()=>{page--;render();};ui.next.onclick=()=>{page++;render();};ui['select-matching'].onclick=()=>{for(const item of filtered())selected.add(VaultLogic.key(item));render();};ui['clear-selection'].onclick=()=>{selected.clear();render();};
  ui.export.onclick=()=>{ui['export-panel'].hidden=false;exportText();};ui['close-export'].onclick=()=>{ui['export-panel'].hidden=true;};
  ui['post-text'].addEventListener('input',()=>{if(!draft)return;draft={...draft,text:ui['post-text'].value,dirty:ui['post-text'].value!==draft.base};exportText();});
  function applyFormat(tag){
    const editor=ui['post-text'];const result=VaultLogic.formatSelection(editor.value,editor.selectionStart,editor.selectionEnd,tag,ui['format-color'].value);
    draft={...draft,text:result.text,dirty:result.text!==draft.base};exportText();editor.focus();editor.setSelectionRange(result.start,result.end);
  }
  ui['format-bold'].onclick=()=>applyFormat('b');ui['format-italic'].onclick=()=>applyFormat('i');ui['format-underline'].onclick=()=>applyFormat('u');ui['apply-color'].onclick=()=>applyFormat('color');
  ui['post-text'].addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&!event.altKey&&['b','i','u'].includes(event.key.toLowerCase())){event.preventDefault();applyFormat(event.key.toLowerCase());}});
  ui['rebuild-post'].onclick=()=>{backupDraft=draft?{...draft}:null;draft=null;exportText();};
  ui['restore-draft'].onclick=()=>{if(!backupDraft)return;const previous={...backupDraft};backupDraft=draft?{...draft}:null;draft=previous;exportText();};
  ui['accept-draft'].onclick=()=>{draft={...draft,base:VaultLogic.exportPost(data,selected,prices),stale:false};draft.dirty=draft.text!==draft.base;exportText();};
  ui['set-prices'].onclick=()=>{ui['pricing-panel'].hidden=false;ui['bulk-price-editor'].replaceChildren(priceEditor(()=>selected));};ui['close-pricing'].onclick=()=>{ui['pricing-panel'].hidden=true;};
  ui['all-mules'].onclick=()=>{mules=new Set(VaultLogic.muleOptions(rawData).filter(c=>c.personalCount+c.inventoryCount).map(c=>c.key));changeScope();};ui['clear-mules'].onclick=()=>{mules.clear();changeScope();};
  ui['copy-post'].onclick=async()=>{try{await navigator.clipboard.writeText(ui['post-text'].value);ui['export-status'].textContent='Post copied. Ready for d2jsp.';}catch{ui['post-text'].focus();ui['post-text'].select();ui['export-status'].textContent='Text selected. Press Ctrl+C (Cmd+C on Mac) to copy.';}};
  ui.refresh.onclick=async()=>{ui.refresh.disabled=true;try{const response=await fetch('/api/refresh',{method:'POST'});if(!response.ok)throw new Error();setTimeout(poll,500);}catch{notify('Could not request a refresh. Reopen D2R Treasure Vault.');ui.refresh.disabled=false;}};
  function showLog(open){ui['changes-panel'].hidden=!open;ui['open-log'].setAttribute('aria-expanded',String(open));if(open){ui['settings-panel'].hidden=true;ui['changes-panel'].scrollIntoView({block:'nearest',behavior:'smooth'});}}
  ui['open-log'].onclick=()=>showLog(ui['changes-panel'].hidden);
  ui['close-log'].onclick=()=>{showLog(false);ui['open-log'].focus();};
  ui['item-type'].onchange=ui['item-quality'].onchange=()=>{page=0;render();};
  ui['clear-refinements'].onclick=()=>{ui['item-type'].value='';ui['item-quality'].value='';page=0;render();};
  ui['log-all-collections'].onclick=()=>{excludedLogCollections=[];saveLogCollections();};
  ui['log-no-collections'].onclick=()=>{excludedLogCollections=availableLogCollections();saveLogCollections();};
  ui.settings.onclick=async()=>{
    showLog(false);
    ui['settings-panel'].hidden=false;ui['settings-status'].textContent='Loading database settings…';
    try{const response=await fetch('/api/settings',{cache:'no-store'});if(!response.ok)throw new Error();const settings=await response.json();ui['database-path'].value=settings.needsSetup?'':settings.databasePath;ui['settings-status'].textContent=settings.needsSetup?'Choose the items.db created by D2R Manager.':'Current database: '+settings.databasePath;}catch{ui['settings-status'].textContent='Could not load settings. Reopen D2R Treasure Vault to reconnect.';}
  };
  ui['close-settings'].onclick=()=>{ui['settings-panel'].hidden=true;};
  async function settingsRequest(route,body){const response=await fetch(route,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const result=await response.json();if(!response.ok)throw new Error(result.error||'Settings request failed.');return result;}
  ui['browse-database'].onclick=async()=>{
    ui['browse-database'].disabled=true;ui['settings-status'].textContent='Choose items.db in the Windows file picker, or cancel to enter a path.';
    try{const result=await settingsRequest('/api/settings/pick',{});if(result.path){ui['database-path'].value=result.path;ui['settings-status'].textContent='File selected. Click Save database to validate and load it.';}else ui['settings-status'].textContent='Selection canceled. Your database has not changed.';}catch(error){ui['settings-status'].textContent=error.message;}
    finally{ui['browse-database'].disabled=false;}
  };
  ui['settings-form'].onsubmit=async event=>{
    event.preventDefault();switchingDatabase=true;hasCurrentConnection=false;selectionStatus();ui['save-settings'].disabled=true;ui['browse-database'].disabled=true;ui['settings-status'].textContent='Validating and loading the database…';
    try{const result=await settingsRequest('/api/settings',{databasePath:ui['database-path'].value.trim()});ui['database-path'].value=result.databasePath;ui['settings-status'].textContent='Database saved. Updates now follow this file.';}catch(error){ui['settings-status'].textContent=error.message;}
    finally{switchingDatabase=false;ui['save-settings'].disabled=false;ui['browse-database'].disabled=false;await poll();}
  };
  ui['log-include-inventory'].onchange=()=>{
    if(!rawData)return;
    includeLogInventory=ui['log-include-inventory'].checked;
    let saved=true;try{localStorage.setItem('d2r-treasure-vault-log-inventory-v1:'+rawData.sourceId,String(includeLogInventory));}catch{saved=false;}
    trackInventory(rawData,true);
    ui['log-settings-status'].textContent=(saved?'Log preference saved.':'Browser storage unavailable; this preference lasts until you close the page.')+' '+(includeLogInventory?'Tracking stashes and carried inventory.':'Tracking stashes only.')+' New changes will be compared with the current capture.';
  };
  ui['changes-filters'].onclick=event=>{const button=event.target.closest('button[data-change-filter]');if(button){changeFilter=button.dataset.changeFilter;renderChanges();}};
  ui['clear-changes'].onclick=()=>{if(changeState){changeState={...changeState,batches:[]};persistChanges();renderChanges();}};
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)poll();});setInterval(()=>{if(!document.hidden)poll();},3000);poll();
})();
