const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');
const vm=require('node:vm');

function loadApi(responses){
  const calls=[];
  const code=ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/api.ts'),'utf8'),
    {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
  const context={exports:{},fetch:async url=>{
    calls.push(url);
    const response=responses.shift();
    if(response instanceof Error)throw response;
    return {ok:response.ok??true,status:response.status??200,statusText:'',json:async()=>response.body};
  },setTimeout:fn=>fn(),Promise,Error,Object};
  vm.createContext(context);vm.runInContext(code,context);
  return {pollJob:context.exports.pollJob,calls};
}

test('temporary polling failures retry and preserve completed result',async()=>{
  const {pollJob,calls}=loadApi([
    {ok:false,status:503,body:{detail:'busy'}},
    {body:{state:'running',progress:{message:'working'}}},
    {body:{state:'done',result:{id:'saved'}}},
  ]);
  const retry=[];
  const job=await pollJob('abc',undefined,n=>retry.push(n));
  assert.equal(job.result.id,'saved');assert.deepEqual(retry,[1]);assert.equal(calls.length,3);
});

test('real job failure returns terminal state without transport error',async()=>{
  const {pollJob}=loadApi([{body:{state:'error',error_detail:{detail:'actual failure'}}}]);
  const job=await pollJob('abc');
  assert.equal(job.state,'error');assert.equal(job.error_detail.detail,'actual failure');
});

test('persistent polling failure stops after bounded retries and retains job id',async()=>{
  const {pollJob,calls}=loadApi([new Error('offline'),new Error('offline'),new Error('offline')]);
  await assert.rejects(pollJob('abc'),e=>e.name==='JobPollingError'&&e.jobId==='abc');
  assert.equal(calls.length,3);
});
