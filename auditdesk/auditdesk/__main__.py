import argparse

import uvicorn


def main():
    p = argparse.ArgumentParser(prog="auditdesk",
                                description="AuditDesk 로컬 웹 앱")
    p.add_argument("--port", type=int, default=8710)
    args = p.parse_args()
    uvicorn.run("auditdesk.app:app", host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
