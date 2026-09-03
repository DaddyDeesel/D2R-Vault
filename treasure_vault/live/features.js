'use strict';
const VaultFeatures=(()=>{
  const shared=p=>p.tab==='advanced'||p.tab.startsWith('shared');
  const container=p=>JSON.stringify([p.accountKey||p.account,shared(p)?'shared':p.ownerKey||p.character,p.tab]);
  const position=p=>JSON.stringify([container(p),p.tab==='advanced'?null:p.x,p.tab==='advanced'?null:p.y]);
  const locations=item=>[...new Set(item.locations.map(position))].sort().join('|');
  const quantities=item=>item.locations.map(p=>JSON.stringify([position(p),p.quantity])).sort().join('|');
  function footprint(item,place){
    const cols=10,rows=place.tab==='inventory'?4:10;
    if(place.tab==='advanced')return {material:true};
    if(!['personal','inventory'].includes(place.tab)&&!place.tab.startsWith('shared'))return {invalid:true};
    if(!Number.isInteger(place.x)||!Number.isInteger(place.y)||place.x<0||place.y<0||place.x>=cols||place.y>=rows)return {invalid:true};
    const known=Number.isInteger(item.width)&&Number.isInteger(item.height)&&item.width>0&&item.height>0;
    const width=known?item.width:1,height=known?item.height:1;
    if(place.x+width>cols||place.y+height>rows)return {invalid:true};
    return {cols,rows,x:place.x,y:place.y,width,height,known};
  }
  function gridItems(data,place){
    return data.items.flatMap(item=>item.locations.filter(p=>container(p)===container(place)).map(location=>({item,location,rect:footprint(item,location)}))).filter(entry=>!entry.rect.invalid&&!entry.rect.material);
  }
  function historyScope(data,includeInventory=false){
    return {...data,items:data.items.flatMap(item=>{
      const locations=item.locations.filter(p=>p.tab==='personal'||p.tab==='advanced'||p.tab.startsWith('shared')||(includeInventory&&p.tab==='inventory'));
      if(!locations.length)return [];
      return [{...item,locations,quantity:locations.reduce((total,p)=>total+p.quantity,0)}];
    })};
  }
  function snapshot(data){
    return {sourceId:data.sourceId,version:data.version,capturedAt:data.sourceCaptured,items:data.items.map(item=>{
      const {key,name,item:baseName,base,category,quality,quantity,rolls,eth,sockets,contents,identitySignature,locations}=item;
      return {key,name,item:baseName,base,category,quality,quantity,rolls,eth,sockets,contents,identitySignature,locations};
    })};
  }
  const visible=item=>JSON.stringify([item.item,item.base,item.category,item.quality,item.rolls,item.eth,item.sockets,item.contents]);
  function diff(before,after){
    if(!before||before.sourceId!==after.sourceId)return [];
    const old=new Map(before.items.map(i=>[i.key,i])),next=new Map(after.items.map(i=>[i.key,i])),events=[];
    const pair=(a,b,inferred=false)=>{
      old.delete(a.key);next.delete(b.key);
      const kinds=[];if(a.quantity!==b.quantity||(locations(a)===locations(b)&&quantities(a)!==quantities(b)))kinds.push('quantity');if(locations(a)!==locations(b))kinds.push('moved');if(visible(a)!==visible(b))kinds.push('updated');
      if(kinds.length)events.push({kinds,before:a,after:b,inferred:inferred&&kinds.includes('moved')});
    };
    for(const [key,item] of [...old])if(next.has(key))pair(item,next.get(key));
    // Shared snapshots can get fresh unit IDs. Match identical signatures at the
    // same recorded position first; ignore which character observed shared stock.
    for(const item of [...old.values()]){
      if(!item.identitySignature)continue;
      const matches=[...next.values()].filter(n=>n.identitySignature===item.identitySignature&&locations(n)===locations(item));
      if(matches.length===1)pair(item,matches[0]);
    }
    // A cross-character move is a possible match only when unique on both sides.
    const signatures=new Set([...old.values()].map(i=>i.identitySignature).filter(Boolean));
    for(const signature of signatures){
      const a=[...old.values()].filter(i=>i.identitySignature===signature),b=[...next.values()].filter(i=>i.identitySignature===signature);
      if(a.length===1&&b.length===1)pair(a[0],b[0],true);
    }
    for(const item of next.values())events.push({kinds:['added'],before:null,after:item,inferred:false});
    for(const item of old.values())events.push({kinds:['removed'],before:item,after:null,inferred:false});
    return events;
  }
  function describeEvent(event){
    const before=event.before?.quantity||0,after=event.after?.quantity||0,delta=after-before;
    const tone=delta>0?'added':delta<0?'removed':'changed';
    const label=delta>0?'Added':delta<0?'Removed':event.kinds.includes('moved')?(event.inferred?'Possible move':'Moved'):event.kinds.includes('quantity')?'Redistributed':'Details updated';
    const detail=event.before&&event.after?before.toLocaleString()+' → '+after.toLocaleString()+' total':delta>0?'New in captured inventory':'No longer in captured inventory';
    return {tone,label,delta,amount:delta?(delta>0?'+':'−')+Math.abs(delta).toLocaleString():event.kinds.includes('moved')?'↔':'•',detail};
  }
  function summarizeEvents(events){
    const totals={added:0,removed:0,changed:0};
    for(const event of events){const e=describeEvent(event);if(e.delta>0)totals.added+=e.delta;else if(e.delta<0)totals.removed-=e.delta;else totals.changed++;}
    return totals;
  }
  const eventCollection=e=>(e.after||e.before).category;
  function collectionSummary(events){
    const categories={};
    for(const name of new Set(events.map(eventCollection))){const selected=events.filter(e=>eventCollection(e)===name);categories[name]={...summarizeEvents(selected),total:selected.length};}
    return categories;
  }
  function historyBatches(batches,excluded=[]){
    if(!excluded.length)return batches;
    return batches.map(batch=>{
      const events=batch.events.filter(e=>!excluded.includes(eventCollection(e)));
      const groups=batch.collections||collectionSummary(batch.events);
      const totals={added:0,removed:0,changed:0};let total=0;
      for(const [name,group] of Object.entries(groups))if(!excluded.includes(name)){total+=group.total;for(const key of Object.keys(totals))totals[key]+=group[key];}
      return {...batch,events,totals,total,partial:!batch.collections&&batch.total>batch.events.length};
    }).filter(batch=>batch.total);
  }
  function updateHistory(state,incoming,excluded=[]){
    const current=snapshot(incoming);
    if(!state||state.sourceId!==incoming.sourceId)return {sourceId:incoming.sourceId,baseline:current,batches:[]};
    if(state.baseline.version===current.version)return state;
    const events=diff(state.baseline,current).filter(e=>!excluded.includes(eventCollection(e))),batches=state.batches||[];
    if(events.length){
      const counts={added:0,removed:0,quantity:0,moved:0,updated:0};for(const e of events)for(const kind of e.kinds)counts[kind]++;
      return {sourceId:incoming.sourceId,baseline:current,batches:[{at:incoming.updatedAt,from:state.baseline.capturedAt,to:incoming.sourceCaptured,counts,collections:collectionSummary(events),totals:summarizeEvents(events),total:events.length,events:events.slice(0,200)},...batches].slice(0,10)};
    }
    return {...state,baseline:current};
  }
  return {container,position,footprint,gridItems,historyScope,snapshot,diff,describeEvent,summarizeEvents,historyBatches,updateHistory};
})();
