// Execute the actual TSX component with controlled React hooks and API promises.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
global.window = { setInterval: () => 1, clearInterval: () => {} };

const source = fs.readFileSync(path.join(__dirname, '../src/Session.tsx'), 'utf8') +
  '\nexport { XbrlReconSub };\n';
const js = ts.transpileModule(source, { compilerOptions: {
  module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React,
  target: ts.ScriptTarget.ES2022,
} }).outputText;
let hooks, cursor, effects, pendingPackages, apiHandler, pollHandler;
const react = {
  createElement: (type, props, ...children) => ({ type, props: props || {}, children }),
  useState(initial) {
    const n = cursor++;
    if (!(n in hooks)) hooks[n] = initial;
    return [hooks[n], (value) => {
      hooks[n] = typeof value === 'function' ? value(hooks[n]) : value;
    }];
  },
  useEffect(fn) { cursor++; effects.push(fn); },
  useCallback: (fn) => { cursor++; return fn; },
  useMemo: (fn) => fn(),
  useRef(value) {
    const n = cursor++;
    if (!(n in hooks)) hooks[n] = { current: value };
    return hooks[n];
  },
};
react.default = react;
const api = {
  api: (url, init) => {
    if (apiHandler) return apiHandler(url, init);
    assert.equal(url, '/api/explorer/packages');
    return new Promise((resolve) => { pendingPackages = resolve; });
  },
  pollJob: (...args) => pollHandler(...args),
};
const ui = Object.fromEntries([
  'Card', 'ErrorBanner', 'GhostBtn', 'Icon', 'PrimaryBtn',
].map((name) => [name, name]));
Object.assign(ui, { chip: () => ({}), F_HEAD: 'sans', F_LABEL: 'sans', MONO: 'mono' });
const mod = new Module(path.join(__dirname, '../src/Session.tsx'), module);
mod.filename = path.join(__dirname, '../src/Session.tsx');
mod.paths = module.paths;
mod.require = (id) => ({ react, './api': api, './ui': ui }[id] || require(id));
mod._compile(js, mod.filename);
const { XbrlReconSub, default: Session } = mod.exports;

function render(props) {
  cursor = 0; effects = [];
  return XbrlReconSub(props);
}
function flatten(node) {
  if (node == null || typeof node === 'boolean') return '';
  if (Array.isArray(node)) return node.map(flatten).join(' ');
  if (typeof node !== 'object') return String(node);
  return flatten(node.children);
}
function nodes(node, predicate, found = []) {
  if (node && typeof node === 'object') {
    if (predicate(node)) found.push(node);
    for (const child of node.children || []) nodes(child, predicate, found);
  }
  return found;
}
async function main() {
  hooks = [];
  const calls = [];
  let tree = render({ sessionId: 'B', result: null,
    runJob: async (...args) => { calls.push(args); return { state: 'done' }; } });
  assert.doesNotMatch(flatten(tree), /99|A-output/);
  const cleanup = effects[0]();
  cleanup();
  pendingPackages({ packages: [{ path: 'late-A', name: 'A' }] });
  await Promise.resolve();
  assert.deepEqual(hooks[3], []); // late package response cannot update unmounted tab

  hooks = [];
  const a = { session_id: 'A', revision: 'r-a', counts: { '일치': 99 },
    rows: {}, matched: 99, total: 99, match_rate: 1, false: 0,
    out_path: 'A-output' };
  tree = render({ sessionId: 'A', result: a,
    runJob: async (...args) => { calls.push(args); return { state: 'done' }; } });
  assert.match(flatten(tree), /99/);
  const download = nodes(tree, (n) => n.type === 'GhostBtn');
  assert.ok(download.length);
  const run = nodes(tree, (n) => n.type === 'PrimaryBtn')[0];
  await run.props.onClick();
  assert.equal(calls[0][1].session_id, 'A');

  hooks = [];
  tree = render({ sessionId: 'B', result: null, runJob: async () => null });
  assert.doesNotMatch(flatten(tree), /99|A-output/);
  assert.equal(nodes(tree, (n) => n.type === 'GhostBtn').length, 0);

  // The parent must reject a delayed A session load after switching to B.
  hooks = [];
  const loads = {};
  apiHandler = (url) => new Promise((resolve) => { loads[url] = resolve; });
  cursor = 0; effects = [];
  Session({ sessionId: 'A' });
  const cleanupA = effects[0]();
  cleanupA();
  cursor = 0; effects = [];
  Session({ sessionId: 'B' });
  effects[0]();
  loads['/api/workbench/sessions/B']({ session_id: 'B', meta: {}, pipeline: [] });
  await Promise.resolve();
  loads['/api/workbench/sessions/A']({ session_id: 'A', meta: {}, pipeline: [] });
  await Promise.resolve();
  assert.equal(hooks[0].session_id, 'B');

  // An A job completing after the switch cannot update B progress or errors.
  hooks[1] = 'footing';
  hooks[0] = { ...hooks[0], xbrl_result: {
    session_id: 'B', counts: { '일치': 7 }, out_path: 'old-B-output', rows: {},
  } };
  cursor = 0; effects = [];
  tree = Session({ sessionId: 'B' });
  const footing = nodes(tree, (n) => n.type?.name === 'FootingTab')[0];
  assert.ok(footing);
  let finishJob;
  apiHandler = async () => ({ job_id: 'old-job' });
  pollHandler = () => new Promise((resolve) => { finishJob = resolve; });
  const running = footing.props.runJob('/api/studio/xbrl-recon', { session_id: 'B' });
  assert.equal(hooks[0].xbrl_result, null);
  await Promise.resolve();
  const cleanupB = effects[0]();
  cleanupB();
  cursor = 0; effects = [];
  Session({ sessionId: 'A' });
  effects[0]();
  finishJob({ state: 'error', error_detail: { detail: 'old error' } });
  await running;
  assert.equal(hooks[2], '');
  assert.equal(hooks[3], null);

  // React StrictMode replays setup after cleanup on the same component.
  hooks = []; cursor = 0; effects = [];
  const strictLoads = [];
  apiHandler = (url) => new Promise((resolve) => strictLoads.push([url, resolve]));
  Session({ sessionId: 'S' });
  const strictSetup = effects[0];
  const strictCleanup = strictSetup();
  strictCleanup();
  const strictCleanupAgain = strictSetup();
  for (const [url, resolve] of strictLoads) {
    if (url === '/api/workbench/sessions/S')
      resolve({ session_id: 'S', meta: {}, xbrl_result: null });
  }
  await Promise.resolve();
  assert.equal(hooks[0]?.session_id, 'S');
  strictCleanupAgain();

  // Finishing another kind of job must not leave XBRL hidden forever.
  hooks = []; cursor = 0; effects = [];
  let savedResult = null;
  apiHandler = (url) => url === '/api/workbench/sessions/C'
    ? Promise.resolve({ session_id: 'C', meta: {}, xbrl_result: savedResult })
    : Promise.resolve({ job_id: url === '/api/studio/xbrl-recon' ? 'xbrl' : 'foot' });
  let finishXbrl;
  pollHandler = (id) => id === 'xbrl'
    ? new Promise((resolve) => { finishXbrl = resolve; })
    : Promise.resolve({ state: 'done' });
  Session({ sessionId: 'C' });
  const cleanupC = effects[0]();
  await Promise.resolve();
  hooks[1] = 'footing';
  cursor = 0; effects = [];
  tree = Session({ sessionId: 'C' });
  const runningTab = nodes(tree, (n) => n.type?.name === 'FootingTab')[0];
  assert.ok(runningTab);
  const xbrl = runningTab.props.runJob('/api/studio/xbrl-recon', { session_id: 'C' });
  await Promise.resolve();
  await runningTab.props.runJob('/api/workbench/sessions/C/foot');
  savedResult = { session_id: 'C', request_id: 'latest', rows: {}, out_path: 'C-output' };
  finishXbrl({ state: 'done', result: savedResult });
  await xbrl;
  await Promise.resolve();
  assert.equal(hooks[0]?.xbrl_result?.request_id, 'latest');
  cleanupC();
  console.log('AD-03 frontend component scenarios completed');
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
