// 서버가 진실 원천 — 화면은 job 폴링과 재조회로만 갱신 (낙관적 업데이트 금지)
export type Job = {
  job_id: string; kind: string;
  state: "queued" | "running" | "done" | "error" | "interrupted";
  progress: { message?: string; current?: number; total?: number };
  result: any; error_detail: { detail: string } | null;
};

export async function api(path: string, init?: RequestInit) {
  const r = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) {
    const msg = body?.detail || `${r.status} ${r.statusText}`;
    throw Object.assign(new Error(msg), { status: r.status });
  }
  return body;
}

export async function openFile(path: string) {
  try {
    await api("/api/fs/open", {
      method: "POST", body: JSON.stringify({ path }),
    });
  } catch (e: any) {
    window.alert(e.message || "파일을 열 수 없습니다");
  }
}

export async function pollJob(
  jobId: string,
  onTick?: (j: Job) => void,
): Promise<Job> {
  for (;;) {
    const j: Job = await api(`/api/jobs/${jobId}`);
    onTick?.(j);
    if (j.state === "done" || j.state === "error" || j.state === "interrupted")
      return j;
    await new Promise((res) => setTimeout(res, 2000));
  }
}
