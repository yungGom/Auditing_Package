# -*- coding: utf-8 -*-
"""회귀 게이트 — final.py 출력을 파싱해 GATES 시드와 대조 (도구 코드 미변경)"""
import re, subprocess, sys, json

SEED = {  # CLAUDE.md 회귀 기준 (삼성 FY25 별도, tol=0)
 "A_total":277,"A_OK":256,"A_ROUND":0,"A_DIFF":17,"A_SKIP":4,
 "B_total":28,"B_OK":24,"B_DIFF":0,"B_SKIP":4,
 "C_link":51,"C_unlink":56,"C_diff":0,
 "C7_gap":"없음","C7_missing":"없음","C7_unref":7,
 "F1":0,"F2":3,"F3":9,"F4":4,
 "D_para":229,"D_flag":1,
 "consolidated":"False","nounit_pages":44,
}
# 방향성: +면 클수록 좋음, -면 작을수록 좋음, 0이면 반드시 동일
DIR = {"A_OK":1,"A_DIFF":-1,"A_SKIP":-1,"B_OK":1,"B_DIFF":-1,"B_SKIP":-1,
       "C_link":1,"C_diff":-1,"F4":-1,"D_flag":0}

def measure(pdf, tol="0"):
    out = subprocess.run([sys.executable,"final.py",pdf,tol],capture_output=True,text=True).stdout
    g=lambda p: re.search(p,out)
    m=g(r"A 산술 (\d+)건 → OK (\d+) \([\d.]+%\) / ROUND (\d+) / DIFF (\d+) / SKIP (\d+)")
    b=g(r"B 연계 (\d+)건 → OK (\d+) / 차이 (\d+) / 미검증 (\d+)")
    c=g(r"C 레퍼 → 성립 (\d+) / 미성립 (\d+) / 차이 (\d+)")
    f=g(r"F 일관성 → 단위누락 (\d+)p / 표현불일치 (\d+)그룹 / 라벨불일치 (\d+)건 / 다중공백 (\d+)건")
    d=g(r"D 줄글 → 검토완료\(/\) (\d+)문단 / 표기 지적 (\d+)건")
    c7=g(r"C7 주석 → 결번 (.+?) / 참조무주석 (.+)")
    cs=g(r"연결 감지 (\w+) · 단위 미표기 (.+?) · 허용오차")
    nu = cs.group(2)
    npages = 0 if nu.strip()=="없음" else len(eval(nu))
    import notes
    _,_,_,unref,_ = notes.run(pdf)
    return {"A_total":int(m.group(1)),"A_OK":int(m.group(2)),"A_ROUND":int(m.group(3)),
            "A_DIFF":int(m.group(4)),"A_SKIP":int(m.group(5)),
            "B_total":int(b.group(1)),"B_OK":int(b.group(2)),"B_DIFF":int(b.group(3)),"B_SKIP":int(b.group(4)),
            "C_link":int(c.group(1)),"C_unlink":int(c.group(2)),"C_diff":int(c.group(3)),
            "C7_gap":c7.group(1).strip(),"C7_missing":c7.group(2).strip(),"C7_unref":len(unref),
            "F1":int(f.group(1)),"F2":int(f.group(2)),"F3":int(f.group(3)),"F4":int(f.group(4)),
            "D_para":int(d.group(1)),"D_flag":int(d.group(2)),
            "consolidated":cs.group(1),"nounit_pages":npages}

def compare(cur, base=SEED, label="삼성 회귀"):
    bad=[]; changed=[]
    for k,v in base.items():
        c=cur.get(k)
        if c==v: continue
        dirn=DIR.get(k,0)
        if dirn==0: verdict="✗ 악화(불변 요구)"
        elif isinstance(c,int) and isinstance(v,int):
            better = (c>v) if dirn>0 else (c<v)
            verdict = "△ 개선" if better else "✗ 악화"
        else: verdict="✗ 악화"
        (changed if verdict.startswith("△") else bad).append((k,v,c,verdict))
    print(f"[{label}] 시드 {len(base)}개 지표 대조")
    if not bad and not changed:
        print("  ✅ 전 지표 동일 — 회귀 없음")
    for k,v,c,vd in changed: print(f"  {vd} {k}: {v} → {c}")
    for k,v,c,vd in bad:     print(f"  {vd} {k}: {v} → {c}")
    return not bad

if __name__=="__main__":
    cur=measure(sys.argv[1] if len(sys.argv)>1 else "SEC_감사보고서_FY25.pdf")
    print(json.dumps(cur,ensure_ascii=False))
    ok=compare(cur)
    sys.exit(0 if ok else 1)
