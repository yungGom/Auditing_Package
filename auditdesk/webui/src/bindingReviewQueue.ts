export type ReviewFilters = {state?:string; sheet?:string; section?:string; role?:string; data_type?:string; exception?:string; change?:string};
export function applyReviewUpdate(draft:any, update:any) {
  if(update.id!==draft.id || update.revision<=draft.revision) throw Error('검토 상태가 변경되었습니다. 새로고침하세요.');
  const decisions={...draft.decisions};
  for(const [id,decision] of Object.entries(update.decision_updates)) {
    if(decision===null) delete decisions[id]; else decisions[id]=decision;
  }
  return {...draft,revision:update.revision,decisions,coverage:update.coverage,
    target_states:update.target_states,review:update.review,
    ...(update.workflow_update?{workflow:{...draft.workflow,...update.workflow_update}}:{})};
}
export function filterRows(rows:any[], f:ReviewFilters) {
  return rows.filter(r=>(!f.state || f.state==='all' || (f.state==='unresolved'?r.state!=='confirmed':r.state===f.state))
    && (!f.sheet || r.sheet===f.sheet) && (!f.section || r.section===f.section)
    && (!f.role || r.roles.includes(f.role)) && (!f.data_type || r.data_types.includes(f.data_type))
    && (!f.exception || r.exceptions.includes(f.exception)) && (!f.change || r.workflow_status===f.change));
}
export function nextUnresolved(rows:any[], id:string, filters:ReviewFilters, direction:number) {
  const visible=new Set(filterRows(rows,filters).filter(r=>r.state!=='confirmed').map(r=>r.id));
  const start=rows.findIndex(r=>r.id===id);
  for(let step=1;step<=rows.length;step++) {
    const i=(start+direction*step+rows.length*2)%rows.length;
    if(visible.has(rows[i].id) && rows[i].id!==id) return rows[i].id;
  }
  return '';
}
export function shortcut(e:any):string|null {
  const tag=e.target?.tagName?.toUpperCase();
  if(e.isComposing || e.repeat || e.target?.isContentEditable || ['INPUT','TEXTAREA','SELECT','BUTTON'].includes(tag)) return null;
  if(e.altKey && e.key==='ArrowDown') return 'next';
  if(e.altKey && e.key==='ArrowUp') return 'previous';
  if(e.altKey && /^[1-4]$/.test(e.key)) return 'candidate:'+(Number(e.key)-1);
  if(e.ctrlKey && e.key==='Enter') return 'confirm';
  if(e.altKey && e.key==='Backspace') return 'cancel';
  return null;
}
