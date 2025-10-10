import asyncio
from logging.config import fileConfig
from typing import Union, TYPE_CHECKING

import alembic_postgresql_enum  # noqa
from alembic import context
from alembic.operations.ops import MigrationScript
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic_postgresql_enum.operations import CreateEnumOp
from alembic_postgresql_enum.operations.sync_enum_values import SyncEnumValuesOp
from sqlalchemy import Connection, engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine

from models.bases import BaseSQLAlchemyModel as Base
import models  # noqa
from settings.conf import databases
from utils.helpers import convert_database_url
from sqlalchemy.engine.base import Connection
from sqlalchemy.engine.url import URL
# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

db_url = config.get_main_option("sqlalchemy.url")
# Если не было переопределено
if not db_url or db_url == "driver://user:pass@localhost/dbname":
    config.set_main_option("sqlalchemy.url", convert_database_url(databases._get_db()))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    if obj.info.get("skip_autogen", False):
        return False

    return True

from alembic.operations.ops import CreateTableOp

def process_revision_directives(context: MigrationContext, revision, directives: list[MigrationScript]):
    # extract Migration
    migration_script: MigrationScript = directives[0]

    # Reorder columns in tabel
    if hasattr(migration_script, 'upgrade_ops'):
        for op in migration_script.upgrade_ops.ops:
            if isinstance(op, CreateTableOp):
                reordered = reorder_columns(op.columns)
                op.columns[:] = reordered  # in-place mutation

    # Create message for migration
    if migration_script.message is None:
        changes = migration_script.upgrade_ops.ops
        if changes:
            first_change: CreateEnumOp = changes[0]
            if isinstance(first_change, SyncEnumValuesOp):  # alembic_postgresql_enum
                message = f"change_{first_change.name}"
            elif isinstance(first_change, CreateEnumOp):
                message = f"create_{first_change.name}"
            else:
                message = f"change_{first_change.table_name}"
            if len(changes) > 1:
                message += "_and_more"
            migration_script.message = message

    # extract current head revision
    head_revision = ScriptDirectory.from_config(context.config).get_current_head()

    if head_revision is None:
        # edge case with first migration
        new_rev_id = 1
    else:
        # default branch with incrementation
        last_rev_id = int(head_revision.lstrip("0"))
        new_rev_id = last_rev_id + 1
    # fill zeros up to 4 digits: 1 -> 00001
    migration_script.rev_id = f"{new_rev_id:04}"


def reorder_columns(columns):
    # Поставить id, created, updated в начало
    order = {'id': 0, 'created': 1, 'updated': 2}
    default_val = len(order) + 1
    def sort_key(col) -> int:
        name = getattr(col, "name", None) or ""
        return order.get(name) or default_val
    return sorted(columns, key=sort_key)


def base_do_run_migrations(
    connection: Connection | None = None,
    url: Union[str, URL, None] = None,
) -> None:

    if connection is None and url is None:
        raise ValueError("connection or url is required")

    context.configure(
        url=url,
        connection=connection,
        target_metadata=target_metadata,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
        process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    base_do_run_migrations(url=url)


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = AsyncEngine(
        engine_from_config(
            config.get_section(config.config_ini_section) or {},
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
            # Suppress the following errors to run in a local Docker container
            # ConnectionError: PostgreSQL server at "localhost:5432" rejected SSL upgrade
            connect_args={"ssl": None},
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(base_do_run_migrations)


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
