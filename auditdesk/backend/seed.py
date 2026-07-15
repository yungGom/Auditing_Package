"""Optional seed script — populates the DB with the sample data from the design
prototype (한빛제조 등) for demos and manual testing.

The app itself starts empty (per the brief: no mock data, real API, empty arrays).
Run this only when you want demo content:

    python seed.py            # seed if empty
    python seed.py --reset    # wipe all rows, then seed
"""
import sys

from app.database import Base, SessionLocal, engine
from app import models

Base.metadata.create_all(bind=engine)


def reset(db):
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()


def seed(db):
    if db.query(models.FiscalYear).count() > 0:
        print("DB already has data; use --reset to reseed. Skipping.")
        return

    fy = models.FiscalYear(label="FY2025", start_date="2025-01-01", end_date="2025-12-31", is_active=True)
    fy_old = models.FiscalYear(label="FY2024", start_date="2024-01-01", end_date="2024-12-31", is_active=False)
    db.add_all([fy, fy_old])
    db.flush()

    # 한빛제조 — 기말감사(audit) with 기중감사/기말감사 phases
    hanbit = models.Client(fy_id=fy.id, name="한빛제조", industry="제조업")
    db.add(hanbit)
    db.flush()

    eng = models.Engagement(client_id=hanbit.id, name="기말감사 FY2025", eng_type="audit")
    db.add(eng)
    db.flush()

    interim = models.Phase(engagement_id=eng.id, name="기중감사", kind="phase", order_index=0)
    final = models.Phase(engagement_id=eng.id, name="기말감사", kind="phase", order_index=1)
    db.add_all([interim, final])
    db.flush()

    ar = models.Account(phase_id=interim.id, name="매출채권", order_index=0)
    inv = models.Account(phase_id=interim.id, name="재고자산", order_index=1)
    db.add_all([ar, inv])
    db.flush()

    t1 = models.Task(account_id=ar.id, title="매출채권 확인서 발송", status="in_progress",
                     assignee="김감사", deadline="2025-03-26", priority="high", memo="거래처 30곳 대상")
    t2 = models.Task(account_id=ar.id, title="대손충당금 적정성 검토", status="todo",
                     assignee="이주임", deadline="2025-03-28", priority="mid")
    db.add_all([t1, t2])
    db.flush()
    db.add_all([
        models.TaskHistory(task_id=t1.id, status="todo", at="2025-03-18"),
        models.TaskHistory(task_id=t1.id, status="in_progress", at="2025-03-22"),
        models.TaskHistory(task_id=t2.id, status="todo", at="2025-03-20"),
    ])

    db.add(models.PBCItem(account_id=ar.id, name="매출처별 채권 잔액 명세서", dept="재무팀 · 김부장",
                          requested="2025-03-10", due="2025-03-20", status="received",
                          recv_date="2025-03-19", done="full"))

    iv = models.Interview(account_id=ar.id, date="2025-03-18", person="김재무", title="부장",
                          dept="재무팀", place="본사 3층 회의실", attendees="김감사",
                          topic="수익인식 프로세스 이해", status="done",
                          memo="계약 검토 절차 전반 확인.")
    db.add(iv)
    db.flush()
    db.add_all([
        models.InterviewQuestion(interview_id=iv.id, q="수익인식 조건 검토는 누가?", a="재무팀 2차 검토.",
                                 answerer="김재무 부장", order_index=0),
        models.InterviewQuestion(interview_id=iv.id, q="수기 승인 단계가 있는 구간은?", a="특수 거래는 부장 수기 승인.",
                                 answerer="김재무 부장", follow_up=True,
                                 follow_up_note="수기 승인 건 표본 테스트 설계.", order_index=1),
    ])

    db.add(models.IcfrControl(
        client_id=hanbit.id, code="RV-01", process="수익",
        description="매출 인식 전 계약조건 검토·승인", ctrl_type="operating",
        owner="김감사", due="2025-04-20", status="in_progress",
        risk="수익인식 기준 미충족 거래의 조기 인식 위험", objective="재무보고 신뢰성",
        org="재무팀", nature="예방통제", frequency="거래별", residual_risk="보통",
        mrc=True, ipe=True, accounts=["매출", "매출채권"],
        assertions=["발생사실", "기간귀속", "측정"], test_types=["질문", "검사", "재수행"],
        eval_result="평가중", sample_size="25건",
    ))

    db.add(models.Template(name="제조업 기본", industry="제조업", accounts=[
        models.TemplateAccount(name="매출채권", task_count=4),
        models.TemplateAccount(name="재고자산", task_count=4),
        models.TemplateAccount(name="유형자산", task_count=3),
    ]))

    db.add(models.Settings(id=1, user_name="김감사", org="한길회계법인 감사1본부",
                           email="auditor@hangil.co.kr"))

    db.commit()
    print("Seeded sample data (FY2025 활성, 한빛제조).")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        if "--reset" in sys.argv:
            reset(db)
            print("Reset all tables.")
        seed(db)
    finally:
        db.close()
