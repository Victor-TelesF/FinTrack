"""Enforce normalized ticker identity in the asset catalog.

Revision ID: c41e7a29b603
Revises: 9d2a6c4e8f10
Create Date: 2026-10-02
"""

from alembic import context, op
import sqlalchemy as sa


revision = "c41e7a29b603"
down_revision = "9d2a6c4e8f10"
branch_labels = None
depends_on = None


INDEX_NAME = "uq_asset_ticker_normalized"


def upgrade() -> None:
    if context.is_offline_mode():
        op.execute(
            """
            DO $fintrack$
            DECLARE collision_groups bigint;
            BEGIN
                SELECT count(*) INTO collision_groups
                FROM (
                    SELECT upper(btrim(ticker))
                    FROM asset
                    GROUP BY upper(btrim(ticker))
                    HAVING count(*) > 1
                ) AS collisions;
                IF collision_groups > 0 THEN
                    RAISE EXCEPTION '% normalized ticker collision group(s) found; '
                        'resolve the catalog collisions before retrying', collision_groups;
                END IF;
            END
            $fintrack$;
            """
        )
    else:
        bind = op.get_bind()
        collision_groups = bind.execute(sa.text(
            """
            SELECT count(*)
            FROM (
                SELECT upper(btrim(ticker))
                FROM asset
                GROUP BY upper(btrim(ticker))
                HAVING count(*) > 1
            ) AS collisions
            """
        )).scalar_one()
        if collision_groups:
            raise RuntimeError(
                "Cannot add normalized ticker uniqueness: "
                f"{collision_groups} collision group(s) found. "
                "Resolve the catalog collisions before retrying; no asset rows were changed."
            )

    op.alter_column(
        "asset",
        "name",
        existing_type=sa.String(length=50),
        type_=sa.Text(),
        existing_nullable=False,
    )
    op.create_index(
        INDEX_NAME,
        "asset",
        [sa.text("upper(btrim(ticker))")],
        unique=True,
    )


def downgrade() -> None:
    if context.is_offline_mode():
        op.execute(
            """
            DO $fintrack$
            DECLARE long_names bigint;
            BEGIN
                SELECT count(*) INTO long_names FROM asset WHERE char_length(name) > 50;
                IF long_names > 0 THEN
                    RAISE EXCEPTION '% asset name(s) exceed the historical 50 character limit; '
                        'preserve or resolve those values before retrying', long_names;
                END IF;
            END
            $fintrack$;
            """
        )
    else:
        bind = op.get_bind()
        long_names = bind.execute(sa.text(
            "SELECT count(*) FROM asset WHERE char_length(name) > 50"
        )).scalar_one()
        if long_names:
            raise RuntimeError(
                "Cannot narrow asset.name to 50 characters: "
                f"{long_names} longer value(s) exist. "
                "Preserve or resolve those values before retrying; no schema changes were made."
            )

    op.drop_index(INDEX_NAME, table_name="asset")
    op.alter_column(
        "asset",
        "name",
        existing_type=sa.Text(),
        type_=sa.String(length=50),
        existing_nullable=False,
    )
