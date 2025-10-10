"""Create Base Sequences

Revision ID: 0001
Revises:
Create Date: 2025-06-17 17:38:53.495779

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create the pseudo_encrypt function
    op.execute("""
               CREATE
               OR REPLACE FUNCTION date_mask_pseudo_encrypt(value bigint) RETURNS bigint
                IMMUTABLE
                STRICT
                LANGUAGE plpgsql
                    AS
                    $$
                DECLARE
               l1 bigint;
                     l2
               bigint;
                     r1
               bigint;
                     r2
               bigint;
                     i
               bigint := 0;
                     ds
               text := to_char(current_timestamp, 'YYMMDD');
               BEGIN
                      l1
               := (VALUE >> 16) & 65535;
                      r1
               := VALUE & 65535;
                      WHILE
               i < 3 LOOP
                        l2 := r1;
                        r2
               := l1 # ((((1366 * r1 + 150889) % 714025) / 714025.0) * 32767)::bigint;
                        l1
               := l2;
                        r1
               := r2;
                        i
               := i + 1;
               END LOOP;
               RETURN concat(ds, ((r1 << 16) + l1)::text)::bigint;
               END;
                $$;
               """)
    op.execute("""
               CREATE
               OR REPLACE FUNCTION pseudo_encrypt(value bigint) RETURNS bigint
                    IMMUTABLE
                    STRICT
                LANGUAGE plpgsql
                    AS
                    $$
                DECLARE
               l1 bigint;
                    l2
               bigint;
                    r1
               bigint;
                    r2
               bigint;
                    i
               bigint := 0;
               BEGIN
                    l1
               := (value >> 16) & 65535;
                    r1
               := value & 65535;
                    WHILE
               i < 3 LOOP
                        l2 := r1;
                        r2
               := l1 # ((((1366 * r1 + 150889) % 714025) / 714025.0) * 32767)::bigint;
                        l1
               := l2;
                        r1
               := r2;
                        i
               := i + 1;
               END LOOP;
               RETURN ((r1 << 16) + l1);
               END;
                $$;
               """)


def downgrade() -> None:
    """Downgrade schema."""
    pass
