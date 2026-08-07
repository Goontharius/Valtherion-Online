"""add guilds experience for legacy schemas

Revision ID: 1ee73d334dac
Revises: f23dd71e6f47
Create Date: 2026-08-06 11:43:56.083190

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1ee73d334dac'
down_revision: Union[str, None] = 'f23dd71e6f47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing databases created before migrations landed (via create_all) are
    # missing guilds.experience, which was added to the model after the guilds
    # table was first created. On a fresh database the baseline already ships
    # this column, so this is a no-op there.
    op.execute("ALTER TABLE guilds ADD COLUMN IF NOT EXISTS experience INTEGER NOT NULL DEFAULT 0")


def downgrade() -> None:
    op.execute("ALTER TABLE guilds DROP COLUMN IF EXISTS experience")
