import app.core.models  # noqa: F401  models must be imported before Base.metadata registers tables

from app.core.db import engine, Base, SessionLocal, get_session


def test_settings_defaults():
    # Instance bersih (tanpa file .env ambient) agar nilai default teruji deterministik.
    from app.core.config import Settings

    clean = Settings(_env_file=None)
    assert clean.approval_threshold == 10000.0
    assert clean.database_url.startswith("sqlite")


def test_models_have_expected_columns():
    table_names = set(Base.metadata.tables.keys())
    assert {
        "inventory_items",
        "purchase_orders",
        "po_events",
    }.issubset(table_names)
    po_cols = {c.name for c in Base.metadata.tables["purchase_orders"].columns}
    assert {"po_no", "sku", "total_value", "status", "thread_id"}.issubset(po_cols)


def test_session_context():
    with SessionLocal() as session:
        assert session is not None