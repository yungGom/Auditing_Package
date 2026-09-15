const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
function harness(runJob) {
  const source = fs.readFileSync(path.join(__dirname,'../src/Session.tsx'),'utf8');
  const ast = ts.createSourceFile('Session.tsx',source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
  const fn = ast.statements.find(s=>ts.isFunctionDeclaration(s)&&s.name?.text==='XbrlReconSub');
  const code = ts.transpileModule(fn.getText(ast),{compilerOptions:{jsx:ts.JsxEmit.React,target:ts.ScriptTarget.ES2020}}).outputText;
  let index=0;const states=[];
  const ctx={React:{createElement:(tag,props,...children)=>({tag,props:props||{},children})},
    useState:init=>{const i=index++;if(!(i in states))states[i]=init;return [states[i],v=>states[i]=typeof v==='function'?v(states[i]):v];},
    useEffect:()=>{},useRef:init=>{const i=index++;return states[i]??={current:init};},
    api:async()=>({}),openFile:async()=>{},F_LABEL:'',F_HEAD:'',PrimaryBtn:'button',GhostBtn:'button',Icon:'icon',chip:()=>({}),_tdL:{},_tdR:{}};
  vm.createContext(ctx);vm.runInContext(code,ctx);
  return {render:()=>{index=0;return ctx.XbrlReconSub({sessionId:'s',runJob});}};
}
function all(t){return t&&typeof t==='object'?[t,...(t.children||[]).flat(Infinity).flatMap(all)]:[];}
function text(t){return Array.isArray(t)?t.map(text).join(''):t&&typeof t==='object'?text(t.children):t==null?'':String(t);}
function field(h,label,value){const node=all(h.render()).find(n=>n.props['aria-label']===label);assert.ok(node,label);node.props.onChange({target:{value}});}
function button(h,label){const node=all(h.render()).find(n=>n.tag==='button'&&text(n).includes(label));assert.ok(node,label);return node;}
test('M-22 current default, prior request and excluded scope visible',async()=>{
  const calls=[];const h=harness(async(p,b)=>{calls.push(b);return {state:'done',result:{session_id:'s',target:b.target,target_ends:{instant:'2024-12-31',duration:null},skipped_sheets:['PL'],counts:{},rows:{},total:0,false:0}};});
  await button(h,'태깅 대사 실행').props.onClick();assert.equal(calls[0].target,'current');
  field(h,'비교 context','prior');await button(h,'재실행').props.onClick();
  assert.equal(calls[1].target,'prior');assert.match(text(h.render()),/비교 기간 없음/);assert.match(text(h.render()),/PL/);
});
test('M-18 and M-19 user inputs execute separate jobs and expose Excel result',async()=>{
  const calls=[];const h=harness(async(p,b)=>{calls.push([p,b]);return {state:'done',result:{session_id:'s',out_path:'result.xlsx',summary:{period:{false:0,na:1},unit:{false:1,na:0},name:{false:0,na:0}}}};});
  field(h,'대사 조서 우측 Excel','right.xlsx');field(h,'시트 짝 목록','[{"left":"BS","right":"BS","name":"BS"}]');
  await button(h,'대사 조서 생성').props.onClick();
  assert.equal(calls[0][0],'/api/studio/mapping-workbook');assert.equal(calls[0][1].pairs[0].left,'BS');
  await button(h,'속성 검증 실행').props.onClick();assert.equal(calls[1][0],'/api/studio/attr-check');
  assert.match(text(h.render()),/result.xlsx/);assert.match(text(h.render()),/판정 불가/);
  assert.match(text(h.render()),/unit: FALSE 1/);assert.match(text(h.render()),/period: FALSE 0 · 판정 불가 1/);
});

test('M-18 malformed pairs can be corrected and in-flight requests are not duplicated',async()=>{
  let calls=0,resolve;const h=harness(()=>{calls++;return new Promise(r=>resolve=r);});
  field(h,'시트 짝 목록','invalid');await button(h,'대사 조서 생성').props.onClick();
  assert.equal(calls,0);assert.match(text(h.render()),/JSON 형식/);
  field(h,'시트 짝 목록','[{"left":"BS","right":null,"name":"BS"}]');
  const click=button(h,'대사 조서 생성').props.onClick;
  const pending=click();await click();assert.equal(calls,1);
  assert.match(text(h.render()),/진행 중/);resolve(null);await pending;
  assert.equal(typeof button(h,'대사 조서 생성').props.onClick,'function');
});
