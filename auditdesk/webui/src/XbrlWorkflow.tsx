import React, {useEffect, useRef, useState} from 'react';
import {api, pollJob} from './api';
import {PrimaryBtn, GhostBtn} from './ui';
import BindingReview from './BindingReview';

const base='/api/studio/workflows';
const states:any={waiting:'대기',running:'진행 중',done:'완료',needs_review:'사용자 확인 필요',failed:'실패'};

export default function XbrlWorkflow() {
  const [mode,setMode]=useState('first');
  const [paths,setPaths]=useState({dsd:'',taxonomy:'',layout:'',current_source:'',current_package:'',corpus:'',reuse_id:''});
  const [report,setReport]=useState({company:'',scope:'consolidated',period_end:'',fiscal_number:''});
  const [authority,setAuthority]=useState('');
  const [comparisons,setComparisons]=useState('');
  const [reportType,setReportType]=useState('half');
  const [fetchPrior,setFetchPrior]=useState(true);
  const [receipt,setReceipt]=useState('');
  const [search,setSearch]=useState<any>(null);
  const [analysis,setAnalysis]=useState<any>(null);
  const [draft,setDraft]=useState<any>(null);
  const [saved,setSaved]=useState<any[]>([]);
  const [savedId,setSavedId]=useState('');
  const [assets,setAssets]=useState<any>(null);
  const [busy,setBusy]=useState(false);
  const [progress,setProgress]=useState('');
  const [stage,setStage]=useState(0);
  const [error,setError]=useState('');
  const [activeJobId,setActiveJobId]=useState('');
  const [statusCheckFailed,setStatusCheckFailed]=useState(false);
  const pending=useRef(false);
  useEffect(()=>{api(base).then(r=>setSaved(r.workflows)).catch(e=>setError(e.message));api(base+'/assets').then(setAssets).catch(e=>setError(e.message));},[]);
  const run=async(fn:()=>Promise<void>)=>{
    if(pending.current)return;pending.current=true;setBusy(true);setError('');
    try{await fn();}catch(e:any){setError(e.message);if(e.name==='JobPollingError'){setStatusCheckFailed(true);setProgress('작업 상태 확인 중단 — 상태 다시 확인을 눌러주세요');}else{setProgress('실패 — 입력을 확인한 뒤 다시 실행하세요');}}
    finally{pending.current=false;setBusy(false);}
  };
  const body=()=>({...paths,mode,report:{...report,comparison_ends:comparisons.split(',').map(s=>s.trim()).filter(Boolean)},current_authority:authority,report_type:reportType,fetch_prior:fetchPrior,prior_receipt:receipt});
  const findPrior=()=>run(async()=>{setReceipt('');setSearch(await api(base+'/prior-search',{method:'POST',body:JSON.stringify({...report,report_type:reportType})}));});
  const finishJob=async(jobId:string)=>{
    setStatusCheckFailed(false);
    const done=await pollJob(jobId,j=>{setProgress(j.progress?.message||states[j.state]||j.state);setStage(j.progress?.current||0);},()=>setProgress('상태 확인 일시 실패 — 다시 시도 중'));
    setActiveJobId('');
    if(done.state!=='done'||done.result?.state==='failed')throw Error(done.result?.message||done.error_detail?.detail||'작업이 중단되었습니다. 다시 실행하세요');
    const result=await api(base+'/'+done.result.id);setDraft(result);setSavedId(result.id);setProgress('분석·추천 완료 — 사용자 검토 필요');
    setSaved(s=>[{id:result.id,report:result.report||report,mode},...s]);
  };
  const start=()=>run(async()=>{
    setDraft(null);setStage(0);setProgress('대기');
    const job=await api(base+'/start',{method:'POST',body:JSON.stringify(body())});
    setActiveJobId(job.job_id);
    await finishJob(job.job_id);
  });
  const inputStyle={padding:6,border:'1px solid #c3c6d1',borderRadius:6,maxWidth:'100%'};
  return <div style={{padding:20,overflow:'auto',height:'100%'}}>
    <h3>XBRL 전환 · 작성 준비</h3>
    <label>전환 모드 <select aria-label="전환 모드" value={mode} disabled={busy} onChange={e=>{setMode(e.target.value);setSearch(null);setReceipt('');}}>
      <option value="first">최초 XBRL 전환</option><option value="rollforward">반기/전기→당기 전환</option>
    </select></label>
    <p>당기 DSD → 현재 taxonomy 확인 → {mode==='first'?'유사 공시 근거':'전기 공시 수신·현재 정의 비교'} → 후보 검토 → 사용자 확정 → taxonomy.xls / Excel.xls</p>
    <p>당기 DSD와 적용 taxonomy export, 현재 회사의 검토된 배치가 필요합니다. 다른 회사 Golden 샘플을 제출 배치로 사용하지 마세요. 후보는 자동 확정되지 않습니다.</p>
    <p>{mode==='first'?'회사 전기 XBRL은 필요하지 않습니다. 로컬 OpenDART corpus가 있으면 타사 참고 근거를 연결합니다.':'회사·기간으로 전기 동기 공시를 탐색합니다. 전기 정의·값은 현재 원천을 대신하지 않습니다.'}</p>
    <fieldset disabled={busy}><legend>당기 입력</legend>
      {Object.entries(paths).map(([k,v])=><label key={k} style={{display:'block'}}>{({dsd:'당기 DSD',taxonomy:'당기 taxonomy.xls',layout:'현재 회사 배치.xls',current_source:'선택: 검토된 당기 원천 index',current_package:'선택: 당기 XBRL 패키지 폴더',corpus:'선택: corpus DB (비우면 로컬 기본값)',reuse_id:'선택: 동일 회사 이전 확정 작업 ID'} as any)[k]} <input aria-label={'workflow '+k} style={inputStyle} value={v} onChange={e=>setPaths({...paths,[k]:e.target.value})}/></label>)}
      <GhostBtn onClick={()=>run(async()=>{const r=await api('/api/fs/pick',{method:'POST'});if(r.path)setPaths({...paths,dsd:r.path});})}>DSD 파일 선택</GhostBtn>
      <PrimaryBtn onClick={()=>run(async()=>{setProgress('DSD 분석 중');setAnalysis(await api(base+'/analyze',{method:'POST',body:JSON.stringify({dsd:paths.dsd})}));setProgress('DSD 분석 완료 — 회사·기간을 확인하세요');})}>DSD 분석</PrimaryBtn>
      {(['company','period_end','fiscal_number'] as const).map(k=><label key={k} style={{display:'block'}}>{({company:'회사명 (OpenDART 검색)',period_end:'보고기말 YYYY-MM-DD',fiscal_number:'기수'} as any)[k]} <input aria-label={'workflow '+k} style={inputStyle} value={report[k]} onChange={e=>{setReport({...report,[k]:e.target.value});setSearch(null);setReceipt('');}}/></label>)}
      <label>범위 <select aria-label="workflow scope" value={report.scope} onChange={e=>setReport({...report,scope:e.target.value})}><option value="consolidated">연결</option><option value="separate">별도</option></select></label>
      <label style={{display:'block'}}>비교기말 (전기말·전반기말을 각각 쉼표로 구분) <input aria-label="workflow comparison" value={comparisons} onChange={e=>setComparisons(e.target.value)}/></label>
      <label style={{display:'block'}}>당기 적용 확인 근거 <textarea aria-label="당기 적용 확인 근거" value={authority} onChange={e=>setAuthority(e.target.value)} placeholder="적용 보고기간, 현재 taxonomy/배치의 출처와 확인 근거"/></label>
    </fieldset>
    {analysis&&<details open><summary>DSD 분석 결과 · 회사/기간 확인 필요</summary><p>본문 {analysis.statements?.join(', ')} · 주석 {analysis.notes?.length} · 표 {analysis.tables?.length}</p><p>회사 후보 {analysis.company_candidates?.join(', ')||'없음: 직접 확인'} · 날짜 후보 {analysis.period_candidates?.join(', ')}</p></details>}
    {assets&&<details><summary>로컬 현재 원천 후보</summary><p>{assets.message}</p>{assets.taxonomy_assets?.map((p:string)=><p key={p}>{p}</p>)}<p>corpus: {assets.corpus||'없음 — 공시 조회에서 수신·구축 가능'}</p><p>표준 xlsm은 당기 회사 taxonomy.xls의 대체 파일이 아닙니다.</p></details>}
    {mode==='rollforward'&&<fieldset disabled={busy}><legend>전기 참고자료 자동 수신</legend>
      <label>보고서 종류 <select value={reportType} onChange={e=>{setReportType(e.target.value);setSearch(null);setReceipt('');}}><option value="half">반기</option><option value="annual">사업보고서</option><option value="q1">1분기</option><option value="q3">3분기</option></select></label>
      <PrimaryBtn onClick={findPrior}>전기 공시 찾기</PrimaryBtn>
      {search&&<><p>{search.message}</p><select aria-label="전기 공시 선택" value={receipt} onChange={e=>setReceipt(e.target.value)}><option value="">{search.documents?.length===1?'1건: 실행 시 회사·기간 재검증 후 수신':'접수번호를 선택하세요'}</option>{search.documents?.map((d:any)=><option key={d.rcept_no} value={d.rcept_no}>{d.report_nm} · {d.period_end} · {d.rcept_no}</option>)}</select></>}
      <label><input type="checkbox" checked={fetchPrior} onChange={e=>setFetchPrior(e.target.checked)}/>전기 공시 수신 (해제하면 전기 없음 상태로 당기 원천만 검토)</label>
    </fieldset>}
    <PrimaryBtn disabled={busy||!!activeJobId} onClick={start}>분석·추천 실행</PrimaryBtn>
    {statusCheckFailed&&activeJobId&&<PrimaryBtn disabled={busy} onClick={()=>run(()=>finishJob(activeJobId))}>상태 다시 확인</PrimaryBtn>}
    <select aria-label="저장된 전환 작업" value={savedId} onChange={e=>setSavedId(e.target.value)}><option value="">작업 선택</option>{saved.map(s=><option key={s.id} value={s.id}>{s.report?.company} · {s.report?.period_end} · {s.id.slice(0,8)}</option>)}</select>
    <PrimaryBtn disabled={busy||!savedId} onClick={()=>run(async()=>setDraft(await api(base+'/'+savedId)))}>작업 불러오기</PrimaryBtn>
    {progress&&<p role="status">{progress}</p>}{error&&<p role="alert">{error}</p>}
    {!draft&&progress&&<ol aria-label="실행 단계">{(['DSD 분석',...(mode==='rollforward'?['전기 공시 찾기']:[]),'현재 taxonomy 확인','유사 공시 근거','추천 생성','사용자 검토','Golden 생성']).map((name,i)=><li key={name}>{name}: {i+1<stage?'완료':i+1===stage?(statusCheckFailed?'상태 확인 필요':error?'실패':busy?'진행 중':'사용자 확인 필요'):'대기'}</li>)}</ol>}
    {draft&&<><p>작업 ID: {draft.id}</p><BindingReview key={draft.id} workflowId={draft.id}/></>}
  </div>;
}
