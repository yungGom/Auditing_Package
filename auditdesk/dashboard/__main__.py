"""python -m dashboard → http://localhost:8700 (읽기 전용, localhost 전용)."""
import uvicorn

from .app import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8700, log_level="warning")
