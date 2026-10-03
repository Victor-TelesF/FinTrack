"""Run real Alembic migrations; never substitute metadata.create_all here."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, create_engine, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateSchema, DropSchema

PREVIOUS = "72768f7801ec"
CURRENT = "c41e7a29b603"
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
    assert columns["name"]["type"].__class__.__name__ == "TEXT"
    with engine.connect() as connection:
        indexdef = connection.scalar(text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE schemaname = current_schema() AND indexname = 'uq_asset_ticker_normalized'"
        ))
        assert "UNIQUE INDEX" in indexdef
        assert "upper" in indexdef and "btrim" in indexdef and "ticker" in indexdef
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
        payloads = [dict(item) for item in legacy_http_examples["admin_catalog"]["request"]["json"]["assets"]]
        legacy_stock = next(item for item in payloads if item["type"] == "national_stock")
        legacy_stock["ticker"] = " petr4 "
        for payload in payloads:
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
        legacy_stock = next(row for row in rows if row["type_column"] == "national_stock")
        assert legacy_stock["ticker"] == " petr4 "
        for row in rows:
            assert row["quote_currency"] == {
                "national_stock": "BRL", "international_stock": "USD",
            }.get(row["type_column"])
            assert row["price_provider"] is None
            assert row["external_price_id"] is None
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(upgraded.tables["asset"].insert().values(
                id=uuid4(), name="Duplicate", ticker="PETR4",
                current_price=Decimal("1"), type_column="national_stock"))
    command.downgrade(config, PREVIOUS)
    assert snapshot(engine) == before
    assert QUOTE_FIELDS.isdisjoint(column["name"] for column in inspect(engine).get_columns("asset"))
    command.upgrade(config, "head")
    assert snapshot(engine) == before


def test_migration_stops_on_normalized_ticker_collisions(migration_database):
    config, engine = migration_database
    command.upgrade(config, PREVIOUS)
    metadata = MetaData()
    metadata.reflect(engine)
    asset = metadata.tables["asset"]
    ids = [uuid4(), uuid4()]
    with engine.begin() as connection:
        connection.execute(asset.insert(), [
            {"id": ids[0], "name": "First", "ticker": "PETR4",
             "current_price": Decimal("1"), "type_column": "national_stock"},
            {"id": ids[1], "name": "Second", "ticker": " petr4 ",
             "current_price": Decimal("2"), "type_column": "national_stock"},
        ])

    with pytest.raises(RuntimeError, match=r"1 collision group"):
        command.upgrade(config, "head")

    with engine.connect() as connection:
        rows = list(connection.execute(select(asset.c.id, asset.c.ticker)).all())
        version = connection.scalar(select(metadata.tables["alembic_version"].c.version_num))
        index_exists = connection.scalar(text(
            "SELECT count(*) FROM pg_indexes "
            "WHERE schemaname = current_schema() AND indexname = 'uq_asset_ticker_normalized'"
        ))
    assert {row.id for row in rows} == set(ids)
    assert {row.ticker for row in rows} == {"PETR4", " petr4 "}
    assert version == PREVIOUS
    assert index_exists == 0


def test_downgrade_refuses_to_truncate_long_asset_names(migration_database):
    config, engine = migration_database
    command.upgrade(config, PREVIOUS)
    command.upgrade(config, "head")
    metadata = MetaData()
    metadata.reflect(engine)
    asset = metadata.tables["asset"]
    name = "Asset name longer than fifty characters that must remain intact"
    with engine.begin() as connection:
        connection.execute(asset.insert().values(
            id=uuid4(), name=name, ticker="LONG1", current_price=Decimal("1"),
            type_column="national_stock"))
    with pytest.raises(RuntimeError, match="longer value"):
        command.downgrade(config, PREVIOUS)
    with engine.connect() as connection:
        stored_name = connection.scalar(select(asset.c.name))
        version = connection.scalar(select(metadata.tables["alembic_version"].c.version_num))
    assert stored_name == name
    assert version == CURRENT
