"""Run real Alembic migrations; never substitute metadata.create_all here."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, create_engine, inspect, select
from sqlalchemy.schema import CreateSchema, DropSchema

PREVIOUS = "72768f7801ec"
CURRENT = "9d2a6c4e8f10"
QUOTE_FIELDS = {"price_provider", "external_price_id", "quote_currency"}


@pytest.fixture
def migration_database(sync_engine, test_settings, monkeypatch):
    # Isolate migration history/tables from create_all fixtures and CI's public schema.
    schema = f"migration_test_{uuid4().hex}"
    with sync_engine.begin() as connection:
        connection.execute(CreateSchema(schema))
    monkeypatch.setattr("app.config.settings", test_settings)
    monkeypatch.setenv("PGOPTIONS", f"-csearch_path={schema}")
    engine = create_engine(test_settings.database_url)
    config = Config("alembic.ini")
    try:
        yield config, engine
    finally:
        engine.dispose()
        with sync_engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))


def snapshot(engine):
    metadata = MetaData()
    metadata.reflect(engine)
    with engine.connect() as connection:
        return {
            name: sorted([
                {key: value for key, value in row.items() if key not in QUOTE_FIELDS}
                for row in connection.execute(select(table)).mappings()
            ], key=str)
            for name, table in metadata.tables.items() if name != "alembic_version"
        }


def test_migration_from_empty_database(migration_database):
    config, engine = migration_database
    command.upgrade(config, "head")
    columns = {column["name"]: column for column in inspect(engine).get_columns("asset")}
    assert QUOTE_FIELDS <= columns.keys()
    assert all(columns[name]["nullable"] for name in QUOTE_FIELDS)
    assert {name: columns[name]["type"].length for name in QUOTE_FIELDS} == {
        "price_provider": 20, "external_price_id": 100, "quote_currency": 3,
    }
    metadata = MetaData()
    metadata.reflect(engine)
    with engine.connect() as connection:
        assert connection.scalar(select(metadata.tables["alembic_version"])) == CURRENT


def test_upgrade_and_downgrade_preserve_legacy_rows(migration_database, legacy_http_examples):
    config, engine = migration_database
    command.upgrade(config, PREVIOUS)
    metadata = MetaData()
    metadata.reflect(engine)
    tables = metadata.tables
    user_id, portfolio_id = uuid4(), uuid4()
    with engine.begin() as connection:
        connection.execute(tables["user"].insert().values(
            user_id=user_id, user_name="migration_owner", hash_password="synthetic"))
        connection.execute(tables["portfolio"].insert().values(id_portfolio=portfolio_id, user_id=user_id))
        for payload in legacy_http_examples["admin_catalog"]["request"]["json"]["assets"]:
            asset_id = uuid4()
            connection.execute(tables["asset"].insert().values(
                id=asset_id, name=payload["name"], ticker=payload["ticker"],
                current_price=Decimal(payload["current_price"]), type_column=payload["type"]))
            if payload["type"] in {"cdb", "government_bond"}:
                connection.execute(tables["fixed_income"].insert().values(
                    id=asset_id, rate=Decimal(payload["rate"]),
                    maturity_date=date.fromisoformat(payload["maturity_date"])))
                values = {"id": asset_id, "liquidity_type": payload["liquidity_type"].upper()}
                if payload["type"] == "cdb":
                    values.update(fgc_covered=payload["fgc_covered"], index_type=payload["index_type"].upper())
                else:
                    values["bond_index_type"] = payload["bond_index_type"].upper()
                connection.execute(tables[payload["type"]].insert().values(**values))
            connection.execute(tables["transaction"].insert().values(
                id_transaction=uuid4(), asset_id=asset_id, id_portfolio=portfolio_id,
                quantity=Decimal("2.12345678"), price=Decimal("30.87654321"),
                transaction_type="BUY", transaction_date=date(2026, 9, 25)))
    before = snapshot(engine)
    command.upgrade(config, "head")
    assert snapshot(engine) == before
    upgraded = MetaData()
    upgraded.reflect(engine)
    with engine.connect() as connection:
        rows = list(connection.execute(select(upgraded.tables["asset"])).mappings())
        assert len(rows) == 6
        for row in rows:
            assert row["quote_currency"] == {
                "national_stock": "BRL", "international_stock": "USD",
            }.get(row["type_column"])
            assert row["price_provider"] is None
            assert row["external_price_id"] is None
    command.downgrade(config, PREVIOUS)
    assert snapshot(engine) == before
    assert QUOTE_FIELDS.isdisjoint(column["name"] for column in inspect(engine).get_columns("asset"))
    command.upgrade(config, "head")
    assert snapshot(engine) == before
