const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const ts=require('typescript');
const vm=require('node:vm');
const path=require('node:path');
function helpers(){
  const code=ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/bindingReviewQueue.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText;
  const ctx={exports:{}};vm.createContext(ctx);vm.runInContext(code,ctx);return ctx.exports;
}
const rows=[{id:'a',sheet:'BS',section:'body',state:'medium',roles:['r'],data_types:['monetary'],exceptions:['multiple_candidates']},
{id:'b',sheet:'BS',section:'body',state:'confirmed',roles:['r'],data_types:['monetary'],exceptions:[]},
{id:'c',sheet:'Note',section:'notes',state:'low',roles:['n'],data_types:['text'],exceptions:[]},
{id:'d',sheet:'BS',section:'body',state:'medium',roles:['r'],data_types:['monetary'],exceptions:[]}];
test('queue filters remain unchanged during next unresolved navigation',()=>{
 const h=helpers(), filters={state:'unresolved',sheet:'BS',section:'',role:'r',data_type:'monetary',exception:''};
 assert.equal(h.filterRows(rows,filters).length,2);
 assert.equal(h.nextUnresolved(rows,'a',filters,1),'d');
 assert.equal(h.nextUnresolved(rows,'d',filters,-1),'a');
 assert.equal(filters.sheet,'BS');
 const original={id:'x',revision:1,decisions:{a:{kind:'binding'}},sources:[{id:'s'}]};
 const updated=h.applyReviewUpdate(original,{id:'x',revision:2,decision_updates:{a:null},review:{rows},coverage:{confirmed:0}});
 assert.equal(Object.keys(updated.decisions).length,0);assert.equal(updated.sources,original.sources);
 assert.ok(original.decisions.a);assert.throws(()=>h.applyReviewUpdate(original,{id:'other',revision:2}));
});
test('after confirmation navigation skips completed item and respects filtered order',()=>{
 const h=helpers();const updated=rows.map(r=>r.id==='a'?{...r,state:'confirmed'}:r);
 assert.equal(h.nextUnresolved(updated,'a',{sheet:'BS'},1),'d');
 assert.equal(h.filterRows(rows,{exception:'multiple_candidates'})[0].id,'a');
});
test('keyboard shortcuts never intercept typing, composition, or batch approval',()=>{
 const h=helpers();
 assert.equal(h.shortcut({key:'ArrowDown',altKey:true,target:{tagName:'DIV'}}),'next');
 assert.equal(h.shortcut({key:'ArrowUp',altKey:true,target:{tagName:'DIV'}}),'previous');
 assert.equal(h.shortcut({key:'2',altKey:true,target:{tagName:'DIV'}}),'candidate:1');
 assert.equal(h.shortcut({key:'Enter',ctrlKey:true,target:{tagName:'DIV'}}),'confirm');
 assert.equal(h.shortcut({key:'Enter',ctrlKey:true,target:{tagName:'TEXTAREA'}}),null);
 assert.equal(h.shortcut({key:'ArrowDown',altKey:true,isComposing:true,target:{tagName:'DIV'}}),null);
 assert.equal(h.shortcut({key:'Enter',target:{tagName:'DIV'}}),null);
});

function harness(file,props={},api=async()=>({})) {
 let cursor=0;const state=[];
 const react={createElement:(tag,props,...children)=>({tag,props:props||{},children}),useState:init=>{const i=cursor++;if(!(i in state))state[i]=typeof init==='function'?init():init;return[state[i],v=>state[i]=typeof v==='function'?v(state[i]):v]},useEffect:()=>{},useRef:init=>{const i=cursor++;return state[i]??={current:init}}};
 const code=ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/'+file),'utf8'),{compilerOptions:{jsx:ts.JsxEmit.React,module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
 const ctx={exports:{},require:n=>n==='react'?{...react,default:react}:n==='./bindingReviewQueue'?helpers():n==='./ReviewQueue'?{default:'queue'}:n==='./api'?{api,openFile:async()=>{}}:{PrimaryBtn:'button',GhostBtn:'button'},JSON,console,Set};
 vm.createContext(ctx);vm.runInContext(code,ctx);return {render:()=>{cursor=0;return ctx.exports.default(props)},props};
}
function nodes(t){return t&&typeof t==='object'?[t,...(t.children||[]).flat(Infinity).flatMap(nodes)]:[]}
function txt(t){return Array.isArray(t)?t.map(txt).join(''):t&&typeof t==='object'?txt(t.children):t==null?'':String(t)}
function find(h,label){const n=nodes(h.render()).find(n=>n.props['aria-label']===label);assert.ok(n,label);return n}
function button(h,label){const n=nodes(h.render()).find(n=>n.tag==='button'&&txt(n).includes(label));assert.ok(n,label);return n}
test('batch preview never confirms, safety evidence is visible, explicit approval required',()=>{
 const calls=[];const group={id:'g',signature:{prefix:'ifrs-full',name:'Cash',role:'r'},target_ids:['a','d'],evidence:['exact QName']};
 const props={draft:{sources:[{id:'s',text:'1,234'}],review:{rows,metrics:{required:4,confirmed:0},groups:[group],progress:{},exception_counts:{}}},targetId:'a',filters:{},onDiscard:()=>calls.push('discard'),onPreview:ids=>calls.push(['preview',ids]),onConfirm:e=>calls.push(['confirm',e])};
 const h=harness('ReviewQueue.tsx',props);
 find(h,'일괄 검토 그룹').props.onChange({target:{value:'g'}});
 button(h,'그룹 전체 검토 미리보기').props.onClick();
 assert.equal(calls.filter(c=>c[0]==='confirm').length,0);
 props.preview={count:2,conflicts:0,stale:0,sheets:['BS'],roles:['r'],evidence:['exact QName'],hashes:{dsd:'source-hash'},items:[{target_id:'a',decision:{source_id:'s',taxonomy_id:'tax'}}]};
 assert.match(txt(h.render()),/source-hash/);assert.match(txt(h.render()),/1,234/);
 assert.equal(button(h,'그룹 전체 확정').props.disabled,true);
 find(h,'일괄 검토 근거').props.onChange({target:{value:'검토 완료'}});
 button(h,'그룹 전체 확정').props.onClick();assert.equal(calls.at(-1)[0],'confirm');
});
test('actual review component confirms then advances, preserves filters, and navigates candidates by keyboard',async()=>{
 const d={id:'id',revision:0,report:{company:'co',scope:'separate'},sources:[{id:'s',text:'1,234',label:'cash',candidates:[{id:'tax',evidence:[],ambiguity_reasons:[]}]}],taxonomy:[{id:'tax'}],targets:rows.map(r=>({...r,column:1,row:1,sample_text:'',source_candidates:[{source_id:'s'}]})),decisions:{},coverage:{required:4,confirmed:0},review:{rows}};
 let current=d;const calls=[];
 const h=harness('BindingReview.tsx',{},async(url,o)=>{calls.push([url,o]);if(o?.method==='PUT'){assert.equal(JSON.parse(o.body).compact,true);current={partial:true,id:d.id,revision:1,decision_updates:{a:{kind:'binding'}},coverage:d.coverage,review:{rows:rows.map(r=>r.id==='a'?{...r,state:'confirmed'}:r)}};}return current;});
 await button(h,'자동 후보 생성').props.onClick();
 let queue=()=>nodes(h.render()).find(n=>n.tag==='queue');
 queue().props.onFilters({state:'unresolved',sheet:'BS'});
 find(h,'DSD 원문 셀').props.onChange({target:{value:'s'}});
 h.render().props.onKeyDown({key:'1',altKey:true,target:{tagName:'DIV'},preventDefault(){}});
 assert.equal(find(h,'taxonomy 요소').props.value,'tax');
 await button(h,'검토 확정 · 저장').props.onClick();
 assert.equal(find(h,'대상 배치 셀').props.value,'d');assert.equal(queue().props.filters.sheet,'BS');
 h.render().props.onKeyDown({key:'ArrowUp',altKey:true,target:{tagName:'DIV'},preventDefault(){}});
 assert.equal(calls.filter(c=>c[1]?.method==='PUT').length,1);
});
test('filter changes select a visible target and prior suggestions stay unconfirmed',async()=>{
 const prior={source_id:'s',taxonomy_id:'tax',prefix:'ifrs-full',name:'Cash',role:'r',evidence:'이전 확정 기반 후보'};
 const d={id:'id',revision:0,report:{company:'co',scope:'separate'},sources:[{id:'s',text:'1,234',label:'cash',candidates:[]}],taxonomy:[{id:'tax'}],targets:rows.map(r=>({...r,column:1,row:1,sample_text:'',source_candidates:[]})),decisions:{},coverage:{required:4,confirmed:0},review:{rows:rows.map(r=>({...r,prior_suggestions:[prior]}))}};
 const calls=[];const h=harness('BindingReview.tsx',{},async(p,o)=>{calls.push([p,o]);return d;});
 await button(h,'자동 후보 생성').props.onClick();
 nodes(h.render()).find(n=>n.tag==='queue').props.onFilters({state:'unresolved',sheet:'Note'});
 assert.equal(find(h,'대상 배치 셀').props.value,'c');
 assert.match(txt(h.render()),/이전 확정 기반 후보/);
 const kind=()=>nodes(h.render()).find(n=>n.tag==='select'&&txt(n).includes('taxonomy 값 연결'));
 kind().props.onChange({target:{value:'static'}});
 button(h,'이전 확정 기반 후보').props.onClick();
 assert.equal(find(h,'taxonomy 요소').props.value,'tax');
 assert.equal(kind().props.value,'binding');
 assert.equal(calls.filter(c=>c[1]?.method==='PUT').length,0);
});
test('stale stored decisions are labelled invalid, never current confirmed coverage',async()=>{
 const d={id:'stale',report:{company:'co',scope:'separate'},sources:[],taxonomy:[],targets:[],decisions:{},coverage:{required:3,confirmed:3,stale:true,ready:false}};
 const h=harness('BindingReview.tsx',{},async()=>d);
 await button(h,'자동 후보 생성').props.onClick();
 assert.match(txt(h.render()),/저장된 확정 \(현재 무효\) 3/);
 assert.equal(button(h,'Golden 생성').props.disabled,true);
});
