/* Ontology Studio: dependency-free, read-only knowledge-graph interface. */
(() => {
  'use strict';
  const SVG_NS = 'http://www.w3.org/2000/svg';
  const VIEW = {w: 1000, h: 580};
  const PALETTE = {Customer:'#b39cff', Order:'#66bfec', Product:'#35d4a6', Invoice:'#f1bd7c'};
  const TYPE_SYMBOL = {Customer:'C', Order:'O', Product:'P', Invoice:'I'};
  const $ = id => document.getElementById(id);
  const escapeHtml = x => String(x == null ? '—' : x).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = x => Number(x || 0).toLocaleString('en-US');
  const state = {overview:null,graph:null,nodes:[],edges:[],byId:new Map(),selected:null,search:'',relation:'all',layout:'force',scale:1,tx:0,ty:0,frame:0,simulation:null,drag:null,pan:null};
  let toastTimer;

  function toast(message, isError=false) {
    const el=$('toast');el.textContent=message;el.className='toast show'+(isError?' error':'');
    clearTimeout(toastTimer);toastTimer=setTimeout(()=>{el.className='toast';},3800);
  }
  async function api(path) {
    const response=await fetch(path,{headers:{Accept:'application/json'}});
    if(!response.ok){let body={};try{body=await response.json();}catch(_){/* skip */}throw new Error(body.detail||`Request failed (${response.status})`);}
    return response.json();
  }
  function svgEl(name,attrs={}){
    const el=document.createElementNS(SVG_NS,name);
    Object.entries(attrs).forEach(([key,value])=>el.setAttribute(key,String(value)));
    return el;
  }
  function colors(type){return PALETTE[type]||'#8799ae';}
  function solidIcon(type){return TYPE_SYMBOL[type]||'•';}
  function nodeTitle(node){return node.label!==node.entity_id?node.label:node.entity_type;}
  function getNode(id){return state.byId.get(id);}
  function nodeVisible(node){
    const term=state.search.trim().toLowerCase();
    const matches=!term||[node.entity_id,node.label,node.entity_type,...Object.values(node.properties)].some(v=>String(v).toLowerCase().includes(term));
    if(!matches)return false;
    if(state.relation==='all')return true;
    return state.edges.some(e=>e.relationship===state.relation&&(e.source===node.id||e.target===node.id));
  }
  function visibleEdge(edge){return (state.relation==='all'||state.relation===edge.relationship)&&nodeVisible(getNode(edge.source))&&nodeVisible(getNode(edge.target));}

  function createNodePositions(){
    const groups={Customer:[],Order:[],Product:[],Invoice:[]};
    state.nodes.forEach(node=>{(groups[node.entity_type]||(groups[node.entity_type]=[])).push(node);});
    const center={Customer:[240,193],Order:[485,265],Product:[755,187],Invoice:[760,432]};
    Object.entries(groups).forEach(([name,list])=>{
      list.forEach((n,i)=>{
        const [cx,cy]=center[name]||[500,290];
        const angle=i*2.3999632+({Customer:0,Order:.2,Product:.7,Invoice:1.6}[name]||0);
        const radius=27+Math.sqrt(i+1)*27;
        n.x=Math.max(45,Math.min(945,cx+Math.cos(angle)*radius));
        n.y=Math.max(56,Math.min(532,cy+Math.sin(angle)*radius));
        n.vx=0;n.vy=0;n.fixed=false;
      });
    });
  }
  function updateViewport(){
    $('viewport').setAttribute('transform',`translate(${state.tx.toFixed(2)} ${state.ty.toFixed(2)}) scale(${state.scale.toFixed(3)})`);
  }
  function setZoom(next,focus={x:500,y:290}){
    const value=Math.max(.55,Math.min(2.7,next));
    const factor=value/state.scale;
    state.tx=focus.x-(focus.x-state.tx)*factor;
    state.ty=focus.y-(focus.y-state.ty)*factor;
    state.scale=value;updateViewport();
  }
  function fitGraph(){state.scale=1;state.tx=0;state.ty=0;updateViewport();}
  function toViewBox(event){
    const bounds=$('graphSvg').getBoundingClientRect();
    return {x:(event.clientX-bounds.left)*VIEW.w/bounds.width,y:(event.clientY-bounds.top)*VIEW.h/bounds.height};
  }
  function screenToGraph(event){const p=toViewBox(event);return {x:(p.x-state.tx)/state.scale,y:(p.y-state.ty)/state.scale};}

  const drawnNodes=new Map(),drawnEdges=new Map();
  function buildSvgGraph(){
    const nodesLayer=$('graphNodes'),edgesLayer=$('graphEdges');
    nodesLayer.replaceChildren();edgesLayer.replaceChildren();drawnNodes.clear();drawnEdges.clear();
    for(const edge of state.edges){
      const line=svgEl('line',{'class':'graph-edge','marker-end':'url(#arrowHead)'});
      const title=svgEl('title');title.textContent=`${edge.relationship}: ${edge.source} → ${edge.target}`;line.append(title);
      edgesLayer.append(line);drawnEdges.set(edge.id,line);
    }
    for(const node of state.nodes){
      const g=svgEl('g',{'class':'graph-node','tabindex':'0','role':'button','aria-label':`${node.entity_type} ${node.entity_id}: ${nodeTitle(node)}`});
      const halo=svgEl('circle',{'class':'halo','cx':0,'cy':0,'r':31,'stroke':colors(node.entity_type)});
      const circle=svgEl('circle',{'class':'node-circle','cx':0,'cy':0,'r':23,'fill':colors(node.entity_type)+'20','stroke':colors(node.entity_type)});
      const glyph=svgEl('text',{'class':'node-glyph','y':5});glyph.textContent=solidIcon(node.entity_type);
      const id=svgEl('text',{'class':'node-id','y':38});id.textContent=node.entity_id;
      const label=svgEl('text',{'class':'node-label','y':51});label.textContent=nodeTitle(node).length>17?nodeTitle(node).slice(0,16)+'…':nodeTitle(node);
      const title=svgEl('title');title.textContent=`${node.entity_type}: ${node.entity_id} — ${nodeTitle(node)}`;
      g.append(halo,circle,glyph,id,label,title);
      g.addEventListener('pointerdown',event=>{
        event.stopPropagation();event.preventDefault();
        const p=screenToGraph(event);state.drag={node,offsetX:node.x-p.x,offsetY:node.y-p.y,pointerId:event.pointerId};
        node.fixed=true;$('graphSvg').setPointerCapture(event.pointerId);
        selectNode(node.id);
      });
      g.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();selectNode(node.id);}});
      nodesLayer.append(g);drawnNodes.set(node.id,g);
    }
    positionSvg();filterGraph();
  }
  function positionSvg(){
    for(const edge of state.edges){
      const e=drawnEdges.get(edge.id),a=getNode(edge.source),b=getNode(edge.target);
      if(!e||!a||!b)continue;
      e.setAttribute('x1',a.x.toFixed(1));e.setAttribute('y1',a.y.toFixed(1));
      e.setAttribute('x2',b.x.toFixed(1));e.setAttribute('y2',b.y.toFixed(1));
    }
    state.nodes.forEach(node=>drawnNodes.get(node.id)?.setAttribute('transform',`translate(${node.x.toFixed(1)} ${node.y.toFixed(1)})`));
  }
  function applyColumnLayout(){
    const col={Customer:142,Order:377,Product:624,Invoice:860};
    for(const type of Object.keys(col)){
      const group=state.nodes.filter(n=>n.entity_type===type).sort((a,b)=>a.entity_id.localeCompare(b.entity_id));
      group.forEach((n,i)=>{n.x=col[type];n.y=55+(i+.5)*(470/group.length);n.vx=0;n.vy=0;});
    }
    positionSvg();
  }
  function tickForce(){
    if(state.layout!=='force'||state.frame>=260)return;
    state.frame++;
    const nodes=state.nodes,force=state.frame<80?1:Math.max(.2,1-(state.frame-80)/220);
    for(let i=0;i<nodes.length;i++)for(let j=i+1;j<nodes.length;j++){
      const a=nodes[i],b=nodes[j];let dx=b.x-a.x,dy=b.y-a.y;const d2=Math.max(100,dx*dx+dy*dy);let k=(17000*force)/(d2*Math.sqrt(d2));
      if(d2<2900)k*=1.5;
      if(!a.fixed){a.vx-=dx*k;a.vy-=dy*k;}
      if(!b.fixed){b.vx+=dx*k;b.vy+=dy*k;}
    }
    for(const edge of state.edges){
      const a=getNode(edge.source),b=getNode(edge.target);
      let dx=b.x-a.x,dy=b.y-a.y,dist=Math.max(1,Math.hypot(dx,dy));
      const forceStrength=((dist-170)*.00085)*force;
      const fx=dx*forceStrength,fy=dy*forceStrength;
      if(!a.fixed){a.vx+=fx;a.vy+=fy;}
      if(!b.fixed){b.vx-=fx;b.vy-=fy;}
    }
    const center={Customer:[205,200],Order:[460,294],Product:[752,190],Invoice:[768,425]};
    for(const node of nodes){
      if(node.fixed)continue;
      const c=center[node.entity_type]||[500,280];
      node.vx+=(c[0]-node.x)*.0018*force;node.vy+=(c[1]-node.y)*.0018*force;
      node.vx*=.83;node.vy*=.83;
      node.x=Math.min(947,Math.max(53,node.x+node.vx));
      node.y=Math.min(523,Math.max(50,node.y+node.vy));
    }
    positionSvg();state.simulation=requestAnimationFrame(tickForce);
  }
  function runLayout(){
    if(state.simulation)cancelAnimationFrame(state.simulation);
    state.frame=0;
    if(state.layout==='columns'){applyColumnLayout();return;}
    createNodePositions();positionSvg();state.simulation=requestAnimationFrame(tickForce);
  }
  function filterGraph(){
    let shown=0;const selected=state.selected;
    const neighbors=new Set();
    if(selected){neighbors.add(selected);state.edges.forEach(e=>{if(e.source===selected)neighbors.add(e.target);if(e.target===selected)neighbors.add(e.source);});}
    for(const n of state.nodes){
      const valid=nodeVisible(n),active=!selected||neighbors.has(n.id);
      shown+=valid?1:0;
      const g=drawnNodes.get(n.id);
      if(!g)continue;
      g.classList.toggle('selected',n.id===selected);
      g.classList.toggle('dim',valid&&!active);g.classList.toggle('filtered',!valid);
      g.classList.toggle('matched',!!state.search&&valid);
    }
    let shownEdges=0;
    for(const e of state.edges){
      const valid=visibleEdge(e);shownEdges+=valid?1:0;
      const active=!selected||(e.source===selected||e.target===selected);
      const el=drawnEdges.get(e.id);if(!el)continue;
      el.classList.toggle('dim',valid&&!active);el.classList.toggle('filtered',!valid);
      el.classList.toggle('highlight',!!selected&&valid&&active);
    }
    $('visibleCount').textContent=`${shown} nodes · ${shownEdges} edges visible`;
  }
  async function selectNode(id){
    const node=getNode(id);if(!node)return;
    state.selected=id;filterGraph();
    $('entityDetails').innerHTML=`<div class="entity-identity"><span class="entity-type-logo" style="background:${colors(node.entity_type)}30;color:${colors(node.entity_type)}">${solidIcon(node.entity_type)}</span><div><h3>${escapeHtml(nodeTitle(node))}</h3><small>${escapeHtml(node.entity_type)} · ${escapeHtml(node.entity_id)}</small></div></div><div class="properties-label">ENTITY PROPERTIES</div>${Object.entries(node.properties).map(([k,v])=>`<div class="prop-row"><span>${escapeHtml(k)}</span><strong>${escapeHtml(v)}</strong></div>`).join('')}<div class="properties-label">CONNECTED ENTITIES</div><span style="color:#7f97aa;font-size:10px">Loading relationships...</span>`;
    try{
      const data=await api(`/api/entities/${encodeURIComponent(node.entity_type)}/${encodeURIComponent(node.entity_id)}`);
      if(state.selected!==id)return;
      const rel=data.related.results;
      const content=rel.length?rel.slice(0,12).map(r=>{
        const n=r.entity;const key=`${n.type}:${n.id}`;
        return `<button class="neighbor-btn" data-target="${escapeHtml(key)}"><span><b>${escapeHtml(n.id)} · ${escapeHtml(n.properties.name||n.type)}</b><small>${escapeHtml(r.relationship)} · ${escapeHtml(r.direction)}</small></span><span>›</span></button>`;
      }).join(''):'<span style="color:#8da6b5;font-size:11px">No connected entities.</span>';
      const header=$('entityDetails').innerHTML.split('<div class="properties-label">CONNECTED ENTITIES</div>')[0];
      $('entityDetails').innerHTML=header+`<div class="properties-label">CONNECTED ENTITIES · ${rel.length}</div>`+content;
      $('entityDetails').querySelectorAll('.neighbor-btn').forEach(el=>el.addEventListener('click',()=>selectNode(el.dataset.target)));
    }catch(err){toast(err.message,true);}
  }

  function barRows(items,palette=PALETTE,limit=Infinity){
    if(!items.length)return'<span style="color:#8396a8;font-size:12px">No data available</span>';
    const max=Math.max(1,...items.map(([_,n])=>n));
    return items.slice(0,limit).map(([label,value],i)=>{
      const color=palette[label]||['#35d4a6','#75b9ed','#b39cff','#f1bd7c','#da91aa'][i%5];
      return `<div class="bar-row"><span class="bar-label" title="${escapeHtml(label)}">${escapeHtml(label)}</span><div class="bar-track"><div class="bar-fill" style="background:${color};width:${Math.max(3,100*value/max)}%"></div></div><span class="bar-number">${fmt(value)}</span></div>`;
    }).join('');
  }
  function initStats(){
    const o=state.overview;
    $('statEntities').textContent=fmt(o.graph_nodes);$('statEdges').textContent=fmt(o.graph_edges);
    $('statTypes').textContent=fmt(o.entity_types.length);$('statTools').textContent=fmt(o.mcp_tools.length);
    $('graphCount').textContent=`${o.graph_nodes} nodes`;
    const cats=Object.entries(o.entity_counts);const rels=Object.entries(o.relationship_counts);
    $('entityBars').innerHTML=barRows(cats);
    $('relationBars').innerHTML=barRows(rels,{CONTAINS:'#65bdee',PLACES:'#b39cff',HAS_INVOICE:'#35d4a6'});
    $('insightEntityBars').innerHTML=barRows(cats);
    $('insightRelationBars').innerHTML=barRows(rels,{CONTAINS:'#65bdee',PLACES:'#b39cff',HAS_INVOICE:'#35d4a6'});
    $('invoiceStatusBars').innerHTML=barRows(Object.entries(o.invoice_status_counts),{paid:'#36d5ad',pending:'#e9b87c'});
    $('topProductsBars').innerHTML=barRows(o.product_purchase_counts.map(p=>[`${p.id} · ${p.name}`,p.orders]),{},8);
    $('graphLegend').innerHTML=o.entity_types.map(type=>`<span class="legend-item"><i class="legend-dot" style="background:${colors(type)}"></i>${escapeHtml(type)}</span>`).join('');
    for(const r of o.relationship_types){const el=document.createElement('option');el.value=r;el.textContent=r;$('relationFilter').append(el);}
    for(const type of o.entity_types){const el=document.createElement('option');el.value=type;el.textContent=type;$('directoryType').append(el);}
    const products=state.nodes.filter(n=>n.entity_type==='Product').sort((a,b)=>a.entity_id.localeCompare(b.entity_id));
    for(const selector of ['quickProduct','workbenchProduct'])for(const p of products){const el=document.createElement('option');el.value=p.entity_id;el.textContent=`${p.entity_id} · ${p.label}`;$(selector).append(el);}
  }
  function renderDirectory(){
    const typ=$('directoryType').value,term=$('directorySearch').value.trim().toLowerCase();
    const matches=state.nodes.filter(n=>(typ==='all'||n.entity_type===typ)&&[n.entity_id,n.entity_type,n.label,...Object.values(n.properties)].some(v=>String(v).toLowerCase().includes(term)));
    $('directoryCount').textContent=`${matches.length} records`;
    $('entityRows').innerHTML=matches.map(n=>{
      const relevant=Object.entries(n.properties).filter(([key])=>key!==`${n.entity_type.toLowerCase()}_id`).slice(0,2).map(([k,v])=>`${k}: ${v}`).join(' · ');
      return `<tr><td><div class="table-entity"><span class="table-icon" style="background:${colors(n.entity_type)}36;color:${colors(n.entity_type)}">${solidIcon(n.entity_type)}</span><b>${escapeHtml(nodeTitle(n))}</b></div></td><td><span class="type-pill" style="color:${colors(n.entity_type)}">${escapeHtml(n.entity_type)}</span></td><td>${escapeHtml(n.entity_id)}</td><td title="${escapeHtml(relevant)}">${escapeHtml(relevant)}</td><td><button class="table-action" data-target="${escapeHtml(n.id)}">View graph →</button></td></tr>`;
    }).join('')||'<tr><td colspan="5">No entities match your filters.</td></tr>';
    $('entityRows').querySelectorAll('button[data-target]').forEach(btn=>btn.addEventListener('click',()=>{navigate('explorer');selectNode(btn.dataset.target);}));
  }
  function resultTable(data){
    const rows=data.purchases;
    if(!rows.length)return'<div class="empty-state"><strong>No purchase relationships found</strong><p>The product exists but has no recorded orders.</p></div>';
    return `<div class="result-summary"><strong>${escapeHtml(data.product_id)} · ${data.count} recorded orders</strong><span>Source-backed traversal</span></div><div class="table-scroll"><table class="result-table"><thead><tr><th>ORDER</th><th>CUSTOMER</th><th>INVOICE TOTAL</th><th>STATUS</th></tr></thead><tbody>${rows.map(row=>{
      const amount=row.invoice_amount==null?'—':`${escapeHtml(row.invoice_currency||'')} ${Number(row.invoice_amount).toFixed(2)}`;
      const status=String(row.invoice_status||'unknown');
      return `<tr><td>${escapeHtml(row.order_id)}</td><td>${escapeHtml(row.customer_name||row.customer_id)}</td><td>${amount}</td><td><span class="status ${status==='paid'?'status-paid':'status-pending'}">${escapeHtml(status)}</span></td></tr>`;
    }).join('')}</tbody></table></div><p class="insight-footnote">Invoice totals belong to entire orders, not individual products.</p>`;
  }
  async function executeQuery(target,selector){
    const id=$(selector).value;if(!id)return;
    const output=$(target);output.innerHTML='<span style="color:#9cc6c4;font-size:11px">Running validated graph traversal...</span>';
    try{
      const data=await api(`/api/queries/product-purchases?product_id=${encodeURIComponent(id)}`);
      if(target==='quickQueryResult'){
        output.innerHTML=`<b>${fmt(data.count)} matching orders</b><br>${data.purchases.map(p=>escapeHtml(p.customer_name||p.customer_id)).join(' · ')||'No recorded orders'}`;
      }else{output.innerHTML=resultTable(data);}
      toast(`${id}: ${data.count} purchase relationship${data.count===1?'':'s'} found`);
    }catch(err){output.textContent=`Query failed: ${err.message}`;toast(err.message,true);}
  }
  function navigate(page){
    for(const id of ['explorer','directory','query','insights']){$(`page-${id}`).classList.toggle('visible',id===page);}
    document.querySelectorAll('.nav-item[data-page]').forEach(el=>el.classList.toggle('active',el.dataset.page===page));
    const label={explorer:'Graph Explorer',directory:'Entity Directory',query:'Query Workbench',insights:'Data Insights'}[page];
    $('breadcrumb').textContent=label;window.scrollTo({top:0,behavior:'instant'});
  }
  function bindEvents(){
    document.querySelectorAll('.nav-item[data-page]').forEach(el=>el.addEventListener('click',()=>navigate(el.dataset.page)));
    $('graphSearch').addEventListener('input',e=>{state.search=e.target.value;filterGraph();});
    $('relationFilter').addEventListener('change',e=>{state.relation=e.target.value;filterGraph();});
    $('layoutFilter').addEventListener('change',e=>{state.layout=e.target.value;runLayout();});
    $('zoomIn').addEventListener('click',()=>setZoom(state.scale*1.2));
    $('zoomOut').addEventListener('click',()=>setZoom(state.scale/1.2));
    $('fitGraph').addEventListener('click',fitGraph);
    $('resetGraph').addEventListener('click',()=>{fitGraph();runLayout();});
    $('showNodeDetails').addEventListener('click',()=>$('nodePanel').scrollIntoView({behavior:'smooth'}));
    $('directorySearch').addEventListener('input',renderDirectory);
    $('directoryType').addEventListener('change',renderDirectory);
    $('quickRun').addEventListener('click',()=>executeQuery('quickQueryResult','quickProduct'));
    $('workbenchRun').addEventListener('click',()=>executeQuery('queryOutput','workbenchProduct'));
    $('exportGraph').addEventListener('click',()=>{
      const blob=new Blob([JSON.stringify(state.graph,null,2)],{type:'application/json'});
      const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='commerce_core_graph.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1500);
      toast('Graph exported as JSON');
    });
    const svg=$('graphSvg');
    svg.addEventListener('pointerdown',event=>{if(event.target.closest('.graph-node'))return;state.pan={pointerId:event.pointerId,point:toViewBox(event),tx:state.tx,ty:state.ty};svg.setPointerCapture(event.pointerId);svg.classList.add('is-panning');});
    svg.addEventListener('pointermove',event=>{
      if(state.drag&&state.drag.pointerId===event.pointerId){const p=screenToGraph(event),n=state.drag.node;n.x=Math.max(42,Math.min(960,p.x+state.drag.offsetX));n.y=Math.max(38,Math.min(540,p.y+state.drag.offsetY));n.vx=0;n.vy=0;positionSvg();}
      else if(state.pan&&state.pan.pointerId===event.pointerId){const p=toViewBox(event);state.tx=state.pan.tx+(p.x-state.pan.point.x);state.ty=state.pan.ty+(p.y-state.pan.point.y);updateViewport();}
    });
    const endPointer=event=>{if(state.drag?.pointerId===event.pointerId){state.drag.node.fixed=false;state.drag=null;if(state.layout==='force'){state.frame=Math.min(state.frame,190);if(state.simulation)cancelAnimationFrame(state.simulation);state.simulation=requestAnimationFrame(tickForce);}}if(state.pan?.pointerId===event.pointerId){state.pan=null;svg.classList.remove('is-panning');}if(svg.hasPointerCapture(event.pointerId))svg.releasePointerCapture(event.pointerId);};
    svg.addEventListener('pointerup',endPointer);svg.addEventListener('pointercancel',endPointer);
    svg.addEventListener('wheel',event=>{event.preventDefault();setZoom(state.scale*(event.deltaY>0?.89:1.12),toViewBox(event));},{passive:false});
  }
  async function boot(){
    bindEvents();
    try{
      const [overview,graph]=await Promise.all([api('/api/overview'),api('/api/graph')]);
      state.overview=overview;state.graph=graph;state.nodes=graph.nodes;state.edges=graph.edges;
      state.byId=new Map(state.nodes.map(n=>[n.id,n]));
      createNodePositions();buildSvgGraph();initStats();renderDirectory();runLayout();
      // Start with a meaningful selected entity and query data.
      selectNode(state.byId.has('Customer:C001')?'Customer:C001':state.nodes[0]?.id);
    }catch(error){console.error(error);toast(`Could not load graph: ${error.message}`,true);
      $('graphArea').insertAdjacentHTML('beforeend',`<div class="empty-state" style="position:absolute;inset:20% 0;z-index:5"><strong>Unable to connect to the knowledge graph</strong><p>${escapeHtml(error.message)}</p><p>Check the FastAPI terminal and reload this page.</p></div>`);
    }
  }
  boot();
})();
