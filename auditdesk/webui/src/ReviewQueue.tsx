import React, {useState} from 'react';
import {PrimaryBtn} from './ui';
import {filterRows, ReviewFilters} from './bindingReviewQueue';

export default function ReviewQueue({draft,targetId,filters,onFilters,onSelect,onNext,busy,preview,onPreview,onConfirm,onDiscard}:any) {
  const [groupId,setGroupId]=useState('');
  const [selected,setSelected]=useState<string[]>([]);
  const [evidence,setEvidence]=useState('');
  if(!draft.review) return null;
  const {rows,metrics:m,groups,progress,exception_counts:exceptions}=draft.review;
  const visible=filterRows(rows,filters);
  const group=groups.find((g:any)=>g.id===groupId);
  const states:any={high:'High confidence',medium:'Medium confidence',low:'Low confidence',conflict:'Conflict',source_insufficient:'Source insufficient',stale:'Stale',confirmed:'Confirmed'};
  const names:any={multiple_candidates:'복수 후보',period_mismatch:'기간 불일치',data_type_mismatch:'데이터 유형 불일치',dimension_uncertain:'dimension 불확실',company_extension:'회사 확장 요소',multiple_roles:'동일 QName 복수 Role',source_insufficient:'원천 부족',no_layout_candidate:'배치 후보 없음',stale:'stale',conflict:'conflict'};
  const change=(key:keyof ReviewFilters,value:string)=>onFilters({...filters,[key]:value});
  const options=(field:string)=>Array.from(new Set<string>(rows.flatMap((r:any)=>Array.isArray(r[field])?r[field]:[r[field]])));
  return <section aria-label="검토 큐">
    <p>확정 {m.confirmed}/{m.required} ({m.confirmation_pct}%) · 후보 있음 {m.candidate_available} ({m.candidate_coverage_pct}%) · 후보 없음 {m.no_candidate} · 남음 {m.remaining}</p>
    <p>High {m.high_confidence} · Medium {m.medium_confidence} · Low {m.low_confidence} · Conflict {m.conflict} · Source insufficient {m.source_insufficient} · Stale {m.stale} · Confirmed {m.confirmed}</p>
    <p>수동 지정 {m.manually_assigned} · 일괄 확정 {m.batch_confirmed} · 일괄 검토 가능 {m.batch_reviewable} ({m.high_confidence_reviewable_pct}%) · 개별 검토 필요 {m.individual_review_remaining} ({m.manual_review_required_pct}%)</p>
    <label>검토 상태 <select aria-label="검토 상태" value={filters.state} onChange={e=>change('state',e.target.value)}><option value="unresolved">미확정</option><option value="all">전체</option>{Object.entries(states).map(([k,v])=><option key={k} value={k}>{String(v)}</option>)}</select></label>
    <label>본문/주석 <select aria-label="본문/주석" value={filters.section} onChange={e=>change('section',e.target.value)}><option value="">전체</option><option value="body">본문</option><option value="notes">주석</option></select></label>
    {([['sheet','시트','sheet'],['role','Role','roles'],['data_type','데이터 유형','data_types']] as const).map(([key,label,field])=><label key={key}>{label} <select aria-label={label+' 필터'} value={filters[key]} onChange={e=>change(key,e.target.value)}><option value="">전체</option>{options(field).map(v=><option key={v} value={v}>{v}</option>)}</select></label>)}
    <label>예외 <select aria-label="예외 큐" value={filters.exception} onChange={e=>change('exception',e.target.value)}><option value="">전체</option>{Object.entries(names).map(([k,v])=><option key={k} value={k}>{String(v)} ({exceptions[k]||0})</option>)}</select></label>
    {draft.workflow?.mode==='rollforward' && <label>변경 검토 <select aria-label="변경 검토" value={filters.change||''} onChange={e=>change('change',e.target.value)}><option value="">전체 · 변경/불확실 우선</option><option value="needs_review">변경 / 재검토 필요</option><option value="reusable_candidate">변경 없음 · 재사용 후보 (미확정)</option></select></label>}
    <p>현재 위치 {Math.max(0,visible.findIndex(r=>r.id===targetId)+1)} / 필터 대상 {visible.length} / 전체 {m.required}</p>
    <PrimaryBtn disabled={busy} onClick={()=>onNext(-1)}>이전 미확정</PrimaryBtn><PrimaryBtn disabled={busy} onClick={()=>onNext(1)}>다음 미확정</PrimaryBtn>
    <p>단축키: Alt+↑/↓ 이전/다음 · Alt+1~4 후보 선택 · Ctrl+Enter 확정 · Alt+Backspace 취소. 입력 중에는 작동하지 않습니다.</p>
    <details><summary>시트별 / 본문·주석별 진행률</summary>{Object.entries(progress).map(([k,v]:[string,any])=><p key={k}>{k} · {v.confirmed}/{v.required} ({(100*v.confirmed/v.required).toFixed(1)}%)</p>)}</details>
    <details><summary>근거가 동일한 High-confidence 일괄 검토 ({groups.length}개 그룹)</summary>
      <p>선택이나 미리보기는 저장하지 않습니다. 대상·근거를 확인한 뒤 명시적으로 확정하세요.</p>
      <select aria-label="일괄 검토 그룹" value={groupId} disabled={busy} onChange={e=>{setGroupId(e.target.value);setSelected([]);setEvidence('');onDiscard();}}><option value="">그룹 선택</option>{groups.map((g:any)=><option key={g.id} value={g.id}>{g.signature.prefix}:{g.signature.name} · {g.signature.role} · {g.target_ids.length}개</option>)}</select>
      {group && <><p>{group.evidence.join(' / ')}</p><pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify(group.signature,null,2)}</pre>
        {group.target_ids.map((id:string)=><div key={id}><label><input type="checkbox" aria-label={'선택 '+id} checked={selected.includes(id)} disabled={busy} onChange={e=>{setSelected(e.target.checked?[...selected,id]:selected.filter(i=>i!==id));onDiscard();}}/>{id}</label> <PrimaryBtn disabled={busy} onClick={()=>onSelect(id)}>대상 확인</PrimaryBtn></div>)}
        <PrimaryBtn disabled={busy||!selected.length} onClick={()=>onPreview(selected)}>선택 항목 검토 미리보기</PrimaryBtn><PrimaryBtn disabled={busy} onClick={()=>onPreview(group.target_ids)}>그룹 전체 검토 미리보기</PrimaryBtn>
      </>}
      {preview && <div role="region" aria-label="일괄확정 안전 검사">
        <p>확정 대상 {preview.count}개 · conflict {preview.conflicts} · stale {preview.stale}</p>
        <p>영향 시트: {preview.sheets.join(', ')} / Role: {preview.roles.join(', ')}</p><p>동일 근거: {preview.evidence.join(' / ')}</p>
        <pre style={{whiteSpace:'pre-wrap'}}>현재 source hashes: {JSON.stringify(preview.hashes,null,2)}</pre>
        <ul>{preview.items.map((item:any)=><li key={item.target_id}>{item.target_id} ← {item.decision.source_id} · {draft.sources.find((s:any)=>s.id===item.decision.source_id)?.text} · {item.decision.taxonomy_id}</li>)}</ul>
        <label>일괄 검토 근거 <textarea aria-label="일괄 검토 근거" value={evidence} onChange={e=>setEvidence(e.target.value)}/></label>
        <PrimaryBtn disabled={busy||!evidence.trim()} onClick={()=>onConfirm(evidence)}>{group && preview.count===group.target_ids.length?'그룹 전체 확정':'선택 항목 일괄 확정'}</PrimaryBtn><PrimaryBtn disabled={busy} onClick={onDiscard}>미리보기 취소</PrimaryBtn>
      </div>}
    </details>
  </section>;
}
