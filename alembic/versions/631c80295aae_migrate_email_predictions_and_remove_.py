"""migrate email predictions and remove old columns

Revision ID: 631c80295aae
Revises: aec7d2f0f7f8
Create Date: 2026-09-22 14:13:37.846686

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '631c80295aae'
down_revision: Union[str, Sequence[str], None] = 'aec7d2f0f7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Move old single-label data into email_predictions
    # without creating duplicate predictions.
    op.execute(
        """
        INSERT INTO email_predictions (email_id, category, confidence)
        SELECT
            e.id,
            e.category,
            e.confidence
        FROM emails AS e
        WHERE e.category IS NOT NULL
          AND e.confidence IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM email_predictions AS p
              WHERE p.email_id = e.id
                AND p.category = e.category
          )
        """
    )

    # Prevent duplicate category predictions for the same email
    op.create_unique_constraint(
        "uq_email_prediction_email_category",
        "email_predictions",
        ["email_id", "category"]
    )

    # Remove the old single-label columns
    op.drop_column("emails", "confidence")
    op.drop_column("emails", "category")


def downgrade() -> None:
    # Restore the old columns
    op.add_column(
        "emails",
        sa.Column(
            "category",
            sa.String(length=100),
            nullable=True
        )
    )

    op.add_column(
        "emails",
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=True
        )
    )

    # If an email has multiple predictions, restore the
    # highest-confidence one into the old single-label columns.
    op.execute(
        """
        UPDATE emails AS e
        SET
            category = p.category,
            confidence = p.confidence
        FROM (
            SELECT DISTINCT ON (email_id)
                email_id,
                category,
                confidence
            FROM email_predictions
            ORDER BY email_id, confidence DESC
        ) AS p
        WHERE e.id = p.email_id
        """
    )

    op.drop_constraint(
        "uq_email_prediction_email_category",
        "email_predictions",
        type_="unique"
    )
