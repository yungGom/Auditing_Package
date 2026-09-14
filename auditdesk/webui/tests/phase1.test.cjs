// Execute the real component with a minimal hook/JSX harness; no DOM dependency.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const source = fs.readFileSync(require('node:path').join(__dirname, '../src/Session.tsx'), 'utf8');
const start = source.indexOf('function XbrlReconSub(');
const end = source.indexOf('\nfunction ', start + 1);
const component = ts.transpileModule(source.slice(start, end), {compilerOptions: {jsx: ts.JsxEmit.React, target: ts.ScriptTarget.ES2020}}).outputText;

function harness(result = null, api = async () => ({})) {
  const states = ['', '', result, true, []];
  const effects = [];
  let index = 0;
  const context = {
    React: {createElement: (tag, props, ...children) => ({tag, props, children})},
    useState: initial => { const i = index++; if (!(i in states)) states[i] = initial; return [states[i], v => {states[i] = typeof v === 'function' ? v(states[i]) : v;}]; },
    useEffect: (fn, deps) => effects.push({fn, deps}),
    useRef: v => ({current:v}), api,
    F_LABEL:'', F_HEAD:'', PrimaryBtn:'button', GhostBtn:'button', Icon:'icon', chip:()=>({}), _tdL:{}, _tdR:{},
  };
  vm.createContext(context);
  vm.runInContext(component, context);
  return {states, effects, render: (id='B') => {index=0; return context.XbrlReconSub({sessionId:id, runJob: async()=>null});}};
}

function text(tree) {
  if (tree == null || typeof tree === 'boolean') return '';
  if (Array.isArray(tree)) return tree.map(text).join('');
  if (typeof tree === 'object') return text(tree.children);
  return String(tree);
}

test('M-04: session B never restores global session A job', async () => {
  const a = {session_id:'A', rows:{}, total:1, matched:1, false:0};
  const h = harness(null, async path => path.includes('/jobs') ? {jobs:[{state:'done',result:a}]} : {xbrl_recon:null,packages:[]});
  h.render();
  for (const e of h.effects) e.fn();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.states[2], null);
  assert.ok(h.effects.some(e => e.deps?.includes('B')), 'reload when session changes');
});

test('M-05: FALSE zero with unmapped rows is incomplete', () => {
  const h = harness({session_id:'B', total:2, matched:1, false:0, true:1, counts:{'매핑 없음':1}, rows:{BS:[{label:'mapped',true:true},{label:'unmapped',true:null}]}});
  const output = text(h.render());
  assert.ok(!output.includes('태깅·본문 전수 일치'), output);
  assert.match(output, /미판정|검증 미완료/);
});

test('M-05: complete all TRUE retains success message', () => {
  const h = harness({session_id:'B', total:1, matched:1, false:0, true:1, counts:{'매핑 없음':0}, rows:{BS:[{label:'mapped',true:true}]}});
  assert.match(text(h.render()), /태깅·본문 전수 일치/);
});

test('M-04: own persisted result is restored', async () => {
  const b = {session_id:'B', rows:{}, false:0};
  const h = harness(null, async () => ({xbrl_recon:b,packages:[]}));
  h.render();
  for (const e of h.effects) e.fn();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.states[2], b);
});

test('M-04: late response after session switch is ignored', async () => {
  let resolve;
  const h = harness(null, path => path.includes('/sessions/') ? new Promise(r=>{resolve=r;}) : Promise.resolve({packages:[]}));
  h.render('A');
  const cleanup = h.effects.find(e => e.deps?.includes('A')).fn();
  cleanup();
  resolve({xbrl_recon:{session_id:'A',rows:{}}});
  await new Promise(r => setImmediate(r));
  assert.equal(h.states[2], null);
});

test('M-05: zero rows and unclassified verdicts cannot claim success', () => {
  for (const rows of [[], [{true:undefined}]]) {
    const h = harness({session_id:'B', total:rows.length, matched:rows.length, false:0, counts:{}, rows:{BS:rows}});
    const output = text(h.render());
    assert.ok(!output.includes('태깅·본문 전수 일치'));
    assert.match(output, /검증 미완료/);
  }
});
