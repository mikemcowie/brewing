"""empty message

Revision ID: 203ab368ee5c
Revises:
Create Date: 2025-09-16 00:17:58.447855

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "203ab368ee5c"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
