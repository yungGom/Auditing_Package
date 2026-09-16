import React, { useEffect, useRef, useState } from "react";
import { api, openFile } from "./api";
import { PrimaryBtn, GhostBtn } from "./ui";

// Filing preparation is a review panel inside Mapping, not a Review Output.
export default function BindingReview() {
  const [paths, setPaths] = useState({dsd:"", taxonomy:"", layout:"", current_source:""});
  const [report, setReport] = useState({company:"", scope:"consolidated", period_end:"", fiscal_number:"", comparison:""});
  const [draft, setDraft] = useState<any>(null);
  const [saved, setSaved] = useState<any[]>([]);
  const [savedId, setSavedId] = useState("");
  const [reuse, setReuse] = useState(false);
  const [targetId, setTargetId] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [taxId, setTaxId] = useState("");
  const [filter, setFilter] = useState("unresolved");
  const [search, setSearch] = useState("");
  const [context, setContext] = useState({instant:"", start:"", end:"", unit:"", dimensions:"[]"});
  const [reviewed, setReviewed] = useState(false);
  const [evidence, setEvidence] = useState("");
  const [kind, setKind] = useState("binding");
  const [out, setOut] = useState("");
  const [result, setResult] = useState<any>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const pending = useRef(false);
  const base = "/api/studio/bindings";
  useEffect(() => { api(base).then(r=>setSaved(r.drafts)).catch(e=>setErr(e.message)); }, []);
  const run = async (fn:()=>Promise<void>) => {
    if (pending.current) return;
    pending.current=true; setBusy(true); setErr("");
    try { await fn(); } catch(e:any) { setErr(e.message); }
    finally { pending.current=false; setBusy(false); }
  };
  const selectTarget = (id:string, data:any=draft) => {
    setTargetId(id); setTaxId(""); setSourceId(""); setReviewed(false); setEvidence("");
    setContext({instant:"",start:"",end:"",unit:"",dimensions:"[]"});
    const d = data?.decisions[id];
    if(d) {
      setKind(d.kind); setSourceId(d.source_id); setTaxId(d.taxonomy_id || "");
      setEvidence(d.source_evidence); setReviewed(!!d.dimensions_reviewed);
      setContext({instant:d.context?.instant || "",start:d.context?.start || "",end:d.context?.end || "",
        unit:d.context?.unit || "",dimensions:JSON.stringify(d.context?.dimensions ?? [])});
    }
  };
  const acceptDraft = (d:any) => {setDraft(d); setResult(null); selectTarget(d.targets[0]?.id || "",d);};
  const create = () => run(async()=>{
    const {comparison,...r} = report;
    const d = await api(base,{method:"POST",body:JSON.stringify({...paths,
      report:{...r,comparison_ends:comparison.split(",").map(s=>s.trim()).filter(Boolean)},
      reuse_id:reuse?savedId:undefined})});
    acceptDraft(d); setSavedId(d.id);
    setSaved(s=>[{id:d.id,report:d.report},...s]);
  });
  const targets = draft?.targets || [];
  const target = targets.find((t:any)=>t.id===targetId);
  const source = draft?.sources.find((s:any)=>s.id===sourceId);
  const coverage = draft?.coverage;
  const save = (cancel=false) => run(async()=>{
    const decision = cancel?{kind:"unresolved"}:{kind,source_id:sourceId,taxonomy_id:taxId,
      source_evidence:evidence,dimensions_reviewed:reviewed,use_source_text:true,
      manual:!source?.candidates.some((c:any)=>c.id===taxId),
      context:{company:draft.report.company,scope:draft.report.scope,unit:context.unit,
        dimensions:JSON.parse(context.dimensions),...(context.instant?{instant:context.instant}:{start:context.start,end:context.end})}};
    const d = await api(`${base}/${draft.id}`,{method:"PUT",body:JSON.stringify({revision:draft.revision,target_id:targetId,decision})});
    setDraft(d); setResult(null);
  });
  const status = (t:any) => {
    const s = draft.target_states?.[t.id];
    const labels:any = {stale:"원천 변경 · 재검토",conflict:"충돌",manual:"수동 지정",confirmed:"사용자 확정",
      automatic_candidate:"자동 후보 · 미확정",source_missing:"원천 부족 · 미확정",unresolved:"미확정"};
    return s ? labels[s.state]+" · "+s.reason : draft.decisions[t.id]?"사용자 확정":"미확정";
  };
  const inputStyle = {padding:6,border:"1px solid #c3c6d1",borderRadius:6,maxWidth:"100%"};
  return <div style={{padding:20,overflow:"auto",height:"100%"}}>
    <h3>제출 준비 · Golden binding 검토</h3>
    <p>자동 후보는 확정되지 않습니다. 당기 원천을 검토하고 모든 대상 셀을 연결해야 생성할 수 있습니다.</p>
    <p>현재 회사의 배치 파일을 선택하세요. 다른 회사의 Golden 샘플을 제출 배치로 사용하지 마세요.</p>
    <div style={{display:"grid",gridTemplateColumns:"repeat(2, minmax(0, 1fr))",gap:8}}>
      {Object.entries(paths).map(([key,value])=><label key={key}>{({dsd:"당기 DSD",taxonomy:"당기 taxonomy.xls",layout:"당기 배치.xls",current_source:"선택: 검토된 현재 원천 index JSON"} as any)[key]}
        <input aria-label={key} value={value} style={{...inputStyle,width:"100%"}} onChange={e=>setPaths({...paths,[key]:e.target.value})}/></label>)}
      {([['company','회사 식별자'],['period_end','보고기말 YYYY-MM-DD'],['fiscal_number','기수'],['comparison','비교기말 (쉼표 구분)']] as const).map(([key,label])=><label key={key}>{label}<input aria-label={label} style={inputStyle} value={report[key]} onChange={e=>setReport({...report,[key]:e.target.value})}/></label>)}
      <label>범위 <select aria-label="범위" value={report.scope} onChange={e=>setReport({...report,scope:e.target.value})}><option value="consolidated">연결</option><option value="separate">별도</option></select></label>
    </div>
    <PrimaryBtn disabled={busy} onClick={create}>자동 후보 생성</PrimaryBtn>
    <select aria-label="저장된 검토" value={savedId} onChange={e=>setSavedId(e.target.value)}>
      <option value="">저장된 검토 선택</option>{saved.map(s=><option key={s.id} value={s.id}>{s.report.company} · {s.report.scope} · {s.report.period_end} · {s.id.slice(0,8)}</option>)}
    </select>
    <PrimaryBtn disabled={busy||!savedId} onClick={()=>run(async()=>acceptDraft(await api(`${base}/${savedId}`)))}>불러오기 / 새로고침</PrimaryBtn>
    <label><input type="checkbox" checked={reuse} onChange={e=>setReuse(e.target.checked)}/>선택한 과거 검토를 재사용 후보로만 참고</label>
    {busy && <p role="status">처리 중…</p>}{err && <p role="alert">{err}</p>}
    {draft && <>
      <p>필수 셀 {coverage.required} · 확정 {coverage.confirmed} · 미확정 {coverage.unresolved} · 충돌 {coverage.conflicts}</p>
      <p>정적 근거 없음 {coverage.static_without_evidence} · taxonomy 미확정 {coverage.taxonomy_unresolved} · 기간 미확정 {coverage.period_unresolved} · 차원 미확정 {coverage.dimension_unresolved}</p>
      {coverage.stale && <p role="alert">원천 변경: 기존 확정은 사용할 수 없습니다. 변경된 원천으로 자동 후보를 다시 생성하세요.</p>}
      <p>회사 {draft.report.company} · {draft.report.scope} · {draft.report.period_end}</p>
      <label>목록 <select value={filter} onChange={e=>setFilter(e.target.value)}><option value="unresolved">미확정</option><option value="all">전체</option><option value="confirmed">확정</option></select></label>
      <label>대상 배치 셀 <select aria-label="대상 배치 셀" value={targetId} onChange={e=>selectTarget(e.target.value)}>
        <option value="">선택</option>{targets.filter((t:any)=>filter==='all'||t.id===targetId||(filter==='confirmed')===!!draft.decisions[t.id]).map((t:any)=><option key={t.id} value={t.id}>{t.id} · {status(t)}</option>)}
      </select></label>
      {target && <><p>대상 {target.sheet} 행 {target.row} 열 {target.column} · 참고 표시(원천 아님): {target.sample_text}</p>
        <p>행축 {target.row_axis} / 열축 {JSON.stringify(target.column_axis)} · 기간/차원 방향은 검토 필요</p>
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}}>
          <div><h4>DSD 원문</h4>
            {target.source_candidates.map((c:any)=><PrimaryBtn key={c.source_id} disabled={busy} onClick={()=>{setSourceId(c.source_id);setTaxId("");setReviewed(false);}}>배치 후보 {c.source_id}</PrimaryBtn>)}
            <input aria-label="원문 검색" placeholder="레이블 또는 원문 검색" value={search} onChange={e=>setSearch(e.target.value)}/>
            <select aria-label="DSD 원문 셀" value={sourceId} style={{maxWidth:"100%"}} onChange={e=>{setSourceId(e.target.value);setTaxId("");setReviewed(false);}}>
              <option value="">원문 셀 선택</option>{draft.sources.filter((s:any)=>s.id===sourceId||!search||`${s.label} ${s.text}`.includes(search)).map((s:any)=><option key={s.id} value={s.id}>{s.section} 표{s.table} R{s.row}C{s.column} · {s.label} · {s.text.slice(0,60)}</option>)}
            </select>
            {source && <><pre style={{whiteSpace:"pre-wrap"}}>{source.text}</pre><p>{JSON.stringify(source.headers)}</p></>}
          </div>
          <div><h4>현재 taxonomy 추천 Top N</h4>
            {source?.candidates.map((c:any)=><div key={c.id}><PrimaryBtn disabled={busy} onClick={()=>setTaxId(c.id)}>{c.prefix}:{c.name} · {c.taxonomy_sheet}:{c.taxonomy_row}</PrimaryBtn>
              <p>{c.role} · {c.label_ko} · {c.data_type} · {c.period}</p>
              <p>확신도 {c.confidence} · 문자열 유사도 {c.score} · {c.evidence.join(' / ')}</p>
              <p>미확정 근거: {c.ambiguity_reasons.join(' / ')}</p></div>)}
            <label>수동 taxonomy 선택 <select aria-label="taxonomy 요소" value={taxId} style={{maxWidth:"100%"}} onChange={e=>setTaxId(e.target.value)}>
              <option value="">선택</option>{draft.taxonomy.map((c:any)=><option key={c.id} value={c.id}>{c.id} · {c.prefix}:{c.name} · {c.role}</option>)}
            </select></label>
          </div>
        </div>
        <label>셀 종류 <select value={kind} onChange={e=>setKind(e.target.value)}><option value="binding">taxonomy 값 연결</option><option value="static">DSD 원문을 정적 표시로 사용</option></select></label>
        {kind==='binding' && <div>
          {([['instant','시점 날짜 (기간형은 비우기)'],['start','기간 시작일'],['end','기간 종료일'],['unit','단위']] as const).map(([k,label])=><label key={k}>{label}<input aria-label={label} value={context[k]} onChange={e=>setContext({...context,[k]:e.target.value})}/></label>)}
          <label>차원/구성요소 <textarea aria-label="차원" value={context.dimensions} placeholder={'[{"axis":"prefix:Axis","member":"prefix:Member"}]'} onChange={e=>setContext({...context,dimensions:e.target.value})}/></label>
          <label><input type="checkbox" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/>현재 원천에서 차원을 검토함 (차원 없음은 []로 명시)</label>
        </div>}
        <label>검토 근거 <textarea aria-label="검토 근거" value={evidence} onChange={e=>setEvidence(e.target.value)}/></label>
        <PrimaryBtn disabled={busy||coverage.stale} onClick={()=>save()}>검토 확정 · 저장</PrimaryBtn>
        <PrimaryBtn disabled={busy||coverage.stale} onClick={()=>save(true)}>확정 취소 · 미확정으로</PrimaryBtn>
      </>}
      {draft.reuse_candidates?.length>0 && <details><summary>과거 사용자 확정 참고 (현재 유효성 재검토 필요)</summary>{draft.reuse_candidates.map((c:any,i:number)=><p key={i}>{c.source_label} · {c.taxonomy.role} · {c.taxonomy.prefix}:{c.taxonomy.name} · {c.state}</p>)}</details>}
      <hr/><label>새 산출 폴더 <input aria-label="산출 폴더" value={out} onChange={e=>setOut(e.target.value)}/></label>
      <PrimaryBtn disabled={busy||!coverage.ready} onClick={()=>run(async()=>setResult(await api(`${base}/${draft.id}/generate`,{method:"POST",body:JSON.stringify({revision:draft.revision,out_dir:out})})))}>검토 완료 Golden 생성</PrimaryBtn>
      {!coverage.ready && <p>미확정/충돌/원천 변경을 해결해야 생성할 수 있습니다. 샘플 값으로 채우지 않습니다.</p>}
      {result && <div><p>확정 binding 범위 생성 완료 · 편집기 호환성 검증은 별도입니다.</p>{[result.taxonomy,result.excel,out+"/review.json"].map((p:string)=><p key={p}>{p} <GhostBtn onClick={()=>run(async()=>{await openFile(p);})}>파일 열기</GhostBtn></p>)}</div>}
    </>}
  </div>;
}
