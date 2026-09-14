const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

function harness(file, name, extra={}) {
  const source = fs.readFileSync(path.join(__dirname, '../src', file), 'utf8');
  const parsed = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const declaration = parsed.statements.find(s=>ts.isFunctionDeclaration(s) && s.name?.text===name);
  const code = ts.transpileModule(declaration.getText(parsed).replace(/^export default |^export /,''),
    {compilerOptions:{jsx:ts.JsxEmit.React,target:ts.ScriptTarget.ES2020}}).outputText;
  let index=0; const values=[], effects=[], deps=[];
  const context={React:{createElement:(tag,props,...children)=>({tag,props:props||{},children})},
    useState:init=>{const i=index++; if(!(i in values))values[i]=init; return [values[i],v=>values[i]=typeof v==='function'?v(values[i]):v];},
    useRef:init=>{const i=index++; return values[i]??=( {current:init} );},
    useEffect:(fn,d)=>{const i=index++; if(JSON.stringify(deps[i])!==JSON.stringify(d)){deps[i]=d;effects.push(fn);}},
    F_LABEL:'',F_HEAD:'',Card:'card',Icon:'icon',PrimaryBtn:'primary',GhostBtn:'ghost',RecCard:'rec',
    MAP_STATE_META:{manual:{variant:'recommend'}}, ...extra};
  vm.createContext(context); vm.runInContext(code,context);
  return {effects,render:props=>{index=0;return context[name](props);}};
}
function all(tree) {return tree && typeof tree==='object' ? [tree,...(tree.children||[]).flat(Infinity).flatMap(all)] : [];}
const flush=()=>new Promise(r=>setImmediate(r));

test('M-11: one automatic diff, failed initial request can retry once without duplicate requests', async()=>{
  let calls=0, resolve, reloads=0; const errors=[];
  const h=harness('Session.tsx','ChangeReview',{api:()=>{calls++;return calls===1?Promise.reject(new Error('locked')):new Promise(r=>resolve=r);}});
  const props={sessionId:'s',s:{xlsx_path:'input.xlsx',diff:null},setErr:e=>errors.push(e),reload:()=>reloads++,onRepack:async()=>{}};
  h.render(props);h.effects.splice(0).forEach(f=>f());await flush();
  assert.equal(calls,1);assert.ok(errors.includes('locked'));
  const buttons=all(h.render(props)).filter(n=>typeof n.props.onClick==='function');
  assert.equal(buttons.length,1,'failed initial diff needs an explicit retry action');
  buttons[0].props.onClick();buttons[0].props.onClick();
  assert.equal(calls,2,'in-flight retry must not be submitted twice');
  resolve({});await flush();assert.equal(reloads,1);
  assert.equal(h.effects.length,0,'no automatic retry loop');
});

test('M-13: alternative candidate selection is used by the existing confirm callback',()=>{
  const candidates=['ifrs-full_First','ifrs-full_Second'].map(element=>({element,label:element,firms:1,similarity:0.8,score:0.8}));
  const confirmed=[];const props={item:{account:'account',state:'manual',candidates},onConfirm:e=>confirmed.push(e)};
  const h=harness('Studio.tsx','MappingCard');
  let card=h.render(props);card.props.onConfirm();assert.equal(confirmed.pop(),candidates[0].element);
  assert.equal(typeof card.props.onSelect,'function');
  card.props.onSelect('ifrs-full:Second');card=h.render(props);card.props.onConfirm();
  assert.equal(confirmed.pop(),candidates[1].element);
  assert.equal(card.props.elementId,'ifrs-full:Second');
  assert.equal(card.props.selectionLabel,'선택한 대안');
  assert.equal(card.props.alts[0].rank,1,'original recommendation rank must be preserved');
});

test('M-15: server open error becomes a user-facing API error',async()=>{
  const source=fs.readFileSync(path.join(__dirname,'../src/api.ts'),'utf8');
  const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
  const context={exports:{},fetch:async()=>({ok:false,status:404,json:async()=>({detail:'파일을 찾을 수 없습니다'})})};
  vm.createContext(context);vm.runInContext(code,context);
  await assert.rejects(context.exports.api('/api/fs/open'),e=>e.status===404 && e.message.includes('파일'));
});

test('M-15: file open action displays failure instead of an unhandled rejection',async()=>{
  const source=fs.readFileSync(path.join(__dirname,'../src/api.ts'),'utf8');
  const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
  const alerts=[];const context={exports:{},window:{alert:m=>alerts.push(m)},fetch:async()=>({ok:false,status:409,json:async()=>({detail:'파일을 열 수 없습니다'})})};
  vm.createContext(context);vm.runInContext(code,context);
  assert.equal(typeof context.exports.openFile,'function');
  await context.exports.openFile('locked.xlsx');
  assert.deepEqual(alerts,['파일을 열 수 없습니다']);
});

test('M-11: successful automatic diff runs once and does not expose failure retry',async()=>{
  let calls=0, reloads=0;
  const h=harness('Session.tsx','ChangeReview',{api:async()=>{calls++;return {};}});
  const props={sessionId:'s',s:{xlsx_path:'input.xlsx',diff:null},setErr:()=>{},reload:()=>reloads++,onRepack:async()=>{}};
  h.render(props);h.effects.splice(0).forEach(f=>f());await flush();h.render(props);
  assert.equal(calls,1);assert.equal(reloads,1);assert.equal(h.effects.length,0);
  assert.equal(all(h.render(props)).filter(n=>n.props.onClick).length,0);
});

test('M-13: actual alternative row supports pointer and keyboard; confirmed card is locked',()=>{
  const selected=[];
  const h=harness('RecCard.tsx','RecCard',{
    MONO:'',VARIANTS:{recommend:{label:'추천 1순위'}},BADGE_KINDS:{},
  });
  const props={variant:'recommend',elementId:'First',labelKo:'first',alts:[{id:'Second',label:'second',badge:'score 0.8'}],onSelect:id=>selected.push(id)};
  all(h.render(props)).find(n=>n.props.onClick).props.onClick();
  const row=all(h.render(props)).find(n=>n.props.role==='button');
  assert.ok(row,'alternative must be operable');assert.equal(row.props.tabIndex,0);
  row.props.onClick();let prevented=0;
  for(const key of ['Enter',' ']) row.props.onKeyDown({key,preventDefault:()=>prevented++});
  assert.deepEqual(selected,['Second','Second','Second']);assert.equal(prevented,2);
  assert.equal(all(h.render({...props,variant:'confirmed'})).filter(n=>n.props.role==='button').length,0);
});

test('M-15: successful open sends the path and shows no error; all file buttons use the handler',async()=>{
  const source=fs.readFileSync(path.join(__dirname,'../src/api.ts'),'utf8');
  const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
  const calls=[], alerts=[];
  const context={exports:{},window:{alert:m=>alerts.push(m)},fetch:async(...args)=>{calls.push(args);return {ok:true,json:async()=>({ok:true})};}};
  vm.createContext(context);vm.runInContext(code,context);await context.exports.openFile('output.xlsx');
  assert.equal(calls[0][0],'/api/fs/open');assert.equal(JSON.parse(calls[0][1].body).path,'output.xlsx');assert.equal(alerts.length,0);
  for(const file of ['Session.tsx','Studio.tsx','Explorer.tsx']) {
    const source=fs.readFileSync(path.join(__dirname,'../src',file),'utf8');
    assert.ok(!source.includes('api("/api/fs/open"'),'unhandled open action in '+file);
    assert.ok(source.includes('openFile('));
  }
});
