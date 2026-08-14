"""Entry point: python -m app — menjalankan FastAPI + scheduler."""
from __future__ import annotations

import uvicorn

from app.api.main import create_default_app
from app.services.scheduler import start_scheduler


def main() -> None:
    app = create_default_app()
    start_scheduler()
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()