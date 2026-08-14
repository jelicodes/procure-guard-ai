"""Entry point: python -m app — menjalankan FastAPI + scheduler."""
from __future__ import annotations

import uvicorn

from app.api.main import create_default_app
from app.core.config import settings
from app.services.scheduler import start_scheduler


def main() -> None:
    app = create_default_app()
    # Pakai deps yang SAMA dengan API layer (cache graph keyed id(deps)),
    # agar resume approval PO hasil scan scheduler bekerja di dev.
    start_scheduler(interval_minutes=settings.scan_interval_minutes, deps=app.state.deps)
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()