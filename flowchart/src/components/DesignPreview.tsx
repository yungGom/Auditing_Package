import type { Activity, RcmRow } from "../types";
import { ActivityNodeBody } from "./ActivityNode";
import { ShapeNodeBody, ShapeNodeData } from "./ShapeNode";
import { canvasDesign } from "../design";

/**
 * 디자인 프리뷰 — ActivityNode 와 ShapeNode 의 모든 변종을 한 화면에서 본다.
 *
 * design.ts 의 토큰을 한 줄 바꾸면 여기 그리드 전체가 동시에 갱신되므로
 * "X 케이스에서는 어떻게 보이지?" 를 따로따로 시험할 필요가 없다.
 *
 * 두 섹션:
 *  1) ActivityNode 변종 (4분할 박스 + 통제유형 배지)
 *  2) 9종 도형 전체 (Activity 포함) — 회사 표준 양식 가이드와 1:1 대응
 */

function rcm(partial: Partial<RcmRow> & { rowNum: number }): RcmRow {
  return {
    process: "",
    processName: "",
    subProcessNo: "",
    subProcessName: "",
    narrative: "",
    riskNo: "",
    riskDesc: "",
    controlNo: "",
    controlName: "",
    controlDesc: "",
    itSystem: "",
    controlOwner: "",
    controlOrg: "",
    keyCa: "",
    controlType: "",
    ...partial,
  };
}

interface ActivityVariant {
  label: string;
  hint?: string;
  activity: Activity;
  selected?: boolean;
}

const ACTIVITY_VARIANTS: ActivityVariant[] = [
  {
    label: "통제 없음",
    hint: "단순 활동 — 우상단 배지 없음",
    activity: {
      actNo: 1,
      rcmRow: 4,
      actName: "구매요청 기안",
      teamOverride: "",
      subSteps: "현업이 ERP에 구매요청을 등록",
      docNames: "",
      branchInfo: "",
      note: "",
      rcm: rcm({
        rowNum: 4,
        controlOrg: "각 현업부서",
        itSystem: "전사 ERP",
      }),
    },
  },
  {
    label: "Manual · Non-Key",
    hint: "연분홍 M 배지, 흰 링 없음",
    activity: {
      actNo: 2,
      rcmRow: 5,
      actName: "팀장 1차 승인",
      teamOverride: "",
      subSteps: "팀장이 ERP 승인 대기 큐에서 결재",
      docNames: "",
      branchInfo: "",
      note: "",
      rcm: rcm({
        rowNum: 5,
        controlOrg: "각 현업부서 팀장",
        itSystem: "전사 ERP",
        controlNo: "FA21-C01",
        controlType: "Manual",
        keyCa: "N",
      }),
    },
  },
  {
    label: "Automated · Key",
    hint: "진분홍 A 배지 + 흰 링",
    activity: {
      actNo: 3,
      rcmRow: 6,
      actName: "한도 초과 자동 승인 라우팅",
      teamOverride: "재무팀",
      subSteps: "한도 초과 시 ERP가 자동으로 재무팀 결재 큐에 라우팅",
      docNames: "승인내역",
      branchInfo: "",
      note: "",
      rcm: rcm({
        rowNum: 6,
        controlOrg: "재무팀",
        itSystem: "전사 ERP",
        controlNo: "FA21-C02",
        controlType: "Automated",
        keyCa: "Y",
      }),
    },
  },
  {
    label: "ITDM · Key",
    hint: "노란 I 배지 + 흰 링 (글자 검정)",
    activity: {
      actNo: 4,
      rcmRow: 7,
      actName: "ERP 권한 변경 로그 모니터링",
      teamOverride: "IT보안팀",
      subSteps: "주기적으로 권한 변경 로그를 검토",
      docNames: "권한변경로그",
      branchInfo: "",
      note: "",
      rcm: rcm({
        rowNum: 7,
        controlOrg: "IT보안팀",
        itSystem: "전사 ERP",
        controlNo: "FA21-IT01",
        controlType: "ITDM",
        keyCa: "Y",
      }),
    },
  },
  {
    label: "긴 활동명 + 긴 서브스텝",
    hint: "줄바꿈/잘림 안 되는지 확인",
    activity: {
      actNo: 5,
      rcmRow: 8,
      actName: "거래처별 매출세금계산서 발행 및 부가세 신고 자료 생성",
      teamOverride: "",
      subSteps:
        "매월 말일 기준으로 ERP에서 거래처별 매출 집계를 받아\n세금계산서 발행 → 국세청 e-세로 전송 → 부가세 신고용 엑셀 자동 생성",
      docNames: "세금계산서, 부가세신고서",
      branchInfo: "",
      note: "",
      rcm: rcm({
        rowNum: 8,
        controlOrg: "회계팀",
        itSystem: "전사 ERP",
        controlNo: "FA21-C05",
        controlType: "Manual",
        keyCa: "Y",
      }),
    },
  },
  {
    label: "발생위치 Manual 디폴트",
    hint: "RCM 에 IT시스템이 비면 'Manual' 로 폴백",
    activity: {
      actNo: 6,
      rcmRow: 9,
      actName: "수기 결재서 작성",
      teamOverride: "",
      subSteps: "결재 라인 수기 서명",
      docNames: "",
      branchInfo: "",
      note: "",
      rcm: rcm({
        rowNum: 9,
        controlOrg: "총무팀",
        itSystem: "",
        controlNo: "",
        controlType: "",
        keyCa: "",
      }),
    },
  },
  {
    label: "선택 상태 (selected)",
    hint: "선택 시 진분홍 outline",
    selected: true,
    activity: {
      actNo: 7,
      rcmRow: 10,
      actName: "재고실사 차이 검토",
      teamOverride: "재고관리팀",
      subSteps: "실사 결과 vs ERP 차이 분석 후 조정 전표 작성",
      docNames: "재고실사보고서",
      branchInfo: "",
      note: "",
      rcm: rcm({
        rowNum: 10,
        controlOrg: "재고관리팀",
        itSystem: "전사 ERP",
        controlNo: "INV-C01",
        controlType: "Manual",
        keyCa: "Y",
      }),
    },
  },
  {
    label: "팀명 매우 김",
    hint: "team 박스가 줄바꿈/잘림 어떻게 되는지",
    activity: {
      actNo: 8,
      rcmRow: 11,
      actName: "월별 결산 마감 회의",
      teamOverride: "재무회계팀 / 경영지원실 / 외부감사인 합동",
      subSteps: "",
      docNames: "",
      branchInfo: "",
      note: "",
      rcm: rcm({
        rowNum: 11,
        itSystem: "수기",
        controlNo: "FA21-C09",
        controlType: "Manual",
        keyCa: "Y",
      }),
    },
  },
];

interface ShapeVariant {
  label: string;
  hint?: string;
  data: ShapeNodeData;
  selected?: boolean;
}

const SHAPE_VARIANTS: ShapeVariant[] = [
  {
    label: "Link",
    hint: "소분류 이상 타 프로세스 연결 — 3분할 사각형",
    data: { shapeKey: "link", label: "" },
  },
  {
    label: "Start / End",
    hint: "프로세스 시작·끝 — 빈 사각형 (가이드 기준)",
    data: { shapeKey: "startEnd", label: "START" },
  },
  {
    label: "Start / End (선택)",
    hint: "선택 outline 진분홍",
    selected: true,
    data: { shapeKey: "startEnd", label: "END" },
  },
  {
    label: "분기점 (Diamond)",
    hint: "의사결정",
    data: { shapeKey: "diamond", label: "승인 한도 초과?" },
  },
  {
    label: "Risk",
    hint: "Risk Number 라벨 — 노란 작은 박스",
    data: { shapeKey: "risk", label: "R.FA21-1" },
  },
  {
    label: "Key Control",
    hint: "진분홍 작은 박스 — Control No.",
    data: { shapeKey: "keyControl", label: "C.FA21-2" },
  },
  {
    label: "Non-Key Control",
    hint: "연분홍 작은 박스",
    data: { shapeKey: "nonkeyControl", label: "C.FA21-1" },
  },
  {
    label: "통제구분 — A (Auto)",
    hint: "진분홍 정사각형",
    data: { shapeKey: "controlType", label: "A" },
  },
  {
    label: "통제구분 — M (Manual)",
    hint: "연분홍 정사각형",
    data: { shapeKey: "controlType", label: "M" },
  },
  {
    label: "통제구분 — I (ITDM)",
    hint: "노란 정사각형 (글자 검정)",
    data: { shapeKey: "controlType", label: "I" },
  },
  {
    label: "문서 (Document)",
    hint: "회색, 물결 사각형",
    data: { shapeKey: "document", label: "승인내역" },
  },
  {
    label: "DB",
    hint: "원통, 분홍, 흰 글자",
    data: {
      shapeKey: "db",
      label: "전사 ERP",
      sublabel: "구매원장",
    },
  },
  {
    label: "I/F (Interface)",
    hint: "작은 회색 원",
    data: { shapeKey: "interface", label: "I/F" },
  },
];

export function DesignPreview() {
  return (
    <div className="h-full overflow-auto bg-slate-100 p-6">
      <div className="mx-auto max-w-7xl space-y-10">
        <header>
          <h2 className="text-base font-bold text-slate-900">
            디자인 프리뷰 — 노드 변종
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            <code className="rounded bg-slate-200 px-1 py-0.5">
              src/design.ts
            </code>{" "}
            의 토큰을 바꾸면 아래 모든 케이스가 즉시 갱신됩니다 (HMR).
            저장 후 새로고침 없이 확인하세요. 회사 가이드의 도형 11종과 1:1
            대응합니다.
          </p>
        </header>

        <section>
          <SectionTitle
            title="1. 회사 표준 도형 11종"
            sub="Link · Start/End · Activity · DB · 분기점 · Document · I/F · Risk · Key/Non-Key Control · 통제구분(A/M/I)"
          />
          <div className="grid grid-cols-2 gap-6 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
            {SHAPE_VARIANTS.map((v) => (
              <VariantCard key={v.label} label={v.label} hint={v.hint}>
                <ShapeNodeBody data={v.data} selected={v.selected} />
              </VariantCard>
            ))}
          </div>
        </section>

        <section>
          <SectionTitle
            title="2. 활동 위 라벨 띠 [R][C][M]"
            sub="회사 산출물 예시처럼 Risk · Key/Non-Key Control · 통제구분이 활동 위 한 줄에 묶이는 패턴"
          />
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <VariantCard
              label="Key · Automated 통제"
              hint="R.FA21-1 + C.FA21-2 + A"
            >
              <LabelBandWithActivity letter="A" variant="key" />
            </VariantCard>
            <VariantCard
              label="Non-Key · Manual 통제"
              hint="R.FA21-3 + C.FA21-1 + M"
            >
              <LabelBandWithActivity letter="M" variant="nonkey" />
            </VariantCard>
            <VariantCard label="ITDM · Key 통제" hint="R + C + I">
              <LabelBandWithActivity letter="I" variant="key" />
            </VariantCard>
            <VariantCard
              label="통제 없음 (라벨 띠 없음)"
              hint="Activity 단독"
            >
              <ActivityOnly />
            </VariantCard>
          </div>
        </section>

        <section>
          <SectionTitle
            title="3. 엣지(화살표) 스타일"
            sub="회사 가이드의 두 가지 흐름: 프로세스(실선) · 데이터/정보(점선). 캔버스에서는 직선/꺾은선/곡선 모양 중 선택."
          />
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <VariantCard
              label="프로세스 흐름"
              hint="실선 + 화살촉 — 활동 간 진행 순서"
            >
              <ArrowSample dashed={false} />
            </VariantCard>
            <VariantCard
              label="데이터 / 정보 흐름"
              hint="점선 + 화살촉 — DB 입출력·문서 생성 등"
            >
              <ArrowSample dashed={true} />
            </VariantCard>
            <VariantCard label="모양 옵션" hint="캔버스 좌상단에서 선택">
              <EdgeShapesSample />
            </VariantCard>
          </div>
        </section>

        <section>
          <SectionTitle
            title="4. ActivityNode 변종"
            sub="다양한 본문/팀명/통제 케이스의 4분할 박스 자체 모양"
          />
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {ACTIVITY_VARIANTS.map((v) => (
              <VariantCard key={v.label} label={v.label} hint={v.hint}>
                <ActivityNodeBody
                  activity={v.activity}
                  selected={v.selected}
                />
              </VariantCard>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
 * 엣지(화살표) 샘플 — design.ts 토큰을 그대로 사용
 * ───────────────────────────────────────────── */

const ARROW_W = 220;
const ARROW_H = 24;

function ArrowSample({ dashed }: { dashed: boolean }) {
  const stroke = canvasDesign.edgeStroke;
  const sw = canvasDesign.edgeStrokeWidth;
  return (
    <svg width={ARROW_W} height={ARROW_H} viewBox={`0 0 ${ARROW_W} ${ARROW_H}`}>
      <defs>
        <marker
          id={dashed ? "arrow-dashed" : "arrow-solid"}
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="7"
          markerHeight="7"
          orient="auto"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill={stroke} />
        </marker>
      </defs>
      <line
        x1={4}
        y1={ARROW_H / 2}
        x2={ARROW_W - 12}
        y2={ARROW_H / 2}
        stroke={stroke}
        strokeWidth={sw}
        strokeDasharray={dashed ? canvasDesign.edgeDashedPattern : undefined}
        markerEnd={`url(#${dashed ? "arrow-dashed" : "arrow-solid"})`}
      />
    </svg>
  );
}

function EdgeShapesSample() {
  const stroke = canvasDesign.edgeStroke;
  const sw = canvasDesign.edgeStrokeWidth;
  const w = 180;
  const h = 80;
  const id = "arrow-shape-sample";

  // 세 가지 경로: 직선(대각), 꺾은선(스텝), 곡선(베지어)
  const straight = `M 4 ${h - 4} L ${w - 8} 4`;
  const step = `M 4 ${h - 4} L ${w / 2} ${h - 4} L ${w / 2} 4 L ${w - 8} 4`;
  const bezier = `M 4 ${h - 4} C ${w / 2} ${h - 4}, ${w / 2} 4, ${w - 8} 4`;

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
      <defs>
        <marker
          id={id}
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill={stroke} />
        </marker>
      </defs>
      <path d={straight} fill="none" stroke={stroke} strokeWidth={sw} markerEnd={`url(#${id})`} />
      <text x={w / 2 - 30} y={h - 8} fontSize="9" fill={stroke}>
        직선
      </text>
      <path d={step} fill="none" stroke={stroke} strokeWidth={sw} opacity={0.55} />
      <path d={bezier} fill="none" stroke={stroke} strokeWidth={sw} opacity={0.35} />
    </svg>
  );
}

/* ─────────────────────────────────────────────
 * 라벨 띠 + 활동 — 회사 산출물 예시의 핵심 패턴
 * ───────────────────────────────────────────── */
function LabelBandWithActivity({
  letter,
  variant,
}: {
  letter: "A" | "M" | "I";
  variant: "key" | "nonkey";
}) {
  const activity: Activity = {
    actNo: 4,
    rcmRow: 7,
    actName: "재무팀 최종 승인",
    teamOverride: "재무팀",
    subSteps: "",
    docNames: "",
    branchInfo: "",
    note: "",
    rcm: rcm({
      rowNum: 7,
      controlOrg: "재무팀",
      itSystem: "전사 ERP",
      controlNo: variant === "key" ? "FA21-C02" : "FA21-C01",
      controlType: letter === "A" ? "Automated" : letter === "I" ? "ITDM" : "Manual",
      keyCa: variant === "key" ? "Y" : "N",
    }),
  };
  const riskNo = "R.FA21-1";
  const ctrlNo = variant === "key" ? "C.FA21-2" : "C.FA21-1";

  return (
    <div className="flex flex-col items-center">
      <div className="flex gap-[2px]">
        <ShapeNodeBody data={{ shapeKey: "risk", label: riskNo }} />
        <ShapeNodeBody
          data={{
            shapeKey: variant === "key" ? "keyControl" : "nonkeyControl",
            label: ctrlNo,
          }}
        />
        <ShapeNodeBody data={{ shapeKey: "controlType", label: letter }} />
      </div>
      <div className="mt-1">
        <ActivityNodeBody activity={activity} />
      </div>
    </div>
  );
}

function ActivityOnly() {
  const activity: Activity = {
    actNo: 1,
    rcmRow: 4,
    actName: "구매요청 기안",
    teamOverride: "",
    subSteps: "",
    docNames: "",
    branchInfo: "",
    note: "",
    rcm: rcm({
      rowNum: 4,
      controlOrg: "각 현업부서",
      itSystem: "전사 ERP",
    }),
  };
  return <ActivityNodeBody activity={activity} />;
}

function SectionTitle({ title, sub }: { title: string; sub: string }) {
  return (
    <div className="mb-4">
      <h3 className="text-sm font-bold text-slate-900">{title}</h3>
      <p className="text-[11px] text-slate-500">{sub}</p>
    </div>
  );
}

function VariantCard({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-3">
        <div className="text-xs font-semibold text-slate-900">{label}</div>
        {hint && <div className="text-[11px] text-slate-500">{hint}</div>}
      </div>
      <div className="flex min-h-[80px] items-center justify-center pt-3 pr-3">
        {children}
      </div>
    </div>
  );
}
