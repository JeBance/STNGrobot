"""Initial migration - create all tables."""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    user_role = sa.Enum("ROOT", "ADMIN", "SPEC", "USER", name="userrole")
    user_role.create(op.get_bind())

    request_status = sa.Enum("NEW", "ASSIGNED", "COMPLETED", "CANCELLED", name="requeststatus")
    request_status.create(op.get_bind())

    assignment_status = sa.Enum("PENDING", "COMPLETED", "CANCELLED", name="assignmentstatus")
    assignment_status.create(op.get_bind())

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("role", user_role, nullable=False, default="USER"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)
    op.create_index("ix_users_role", "users", ["role"], unique=False)

    # Create groups table
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
    )

    # Create specialists table
    op.create_table(
        "specialists",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("assigned_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"]),
    )
    op.create_index("ix_specialists_group_id", "specialists", ["group_id"], unique=False)

    # Create requests table
    op.create_table(
        "requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", request_status, nullable=False, default="NEW"),
        sa.Column("assigned_to", sa.Integer(), nullable=True),
        sa.Column("assigned_group", sa.Integer(), nullable=True),
        sa.Column("completed_by", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["assigned_to"], ["specialists.id"]),
        sa.ForeignKeyConstraint(["assigned_group"], ["groups.id"]),
        sa.ForeignKeyConstraint(["completed_by"], ["specialists.id"]),
    )
    op.create_index("ix_requests_user_id", "requests", ["user_id"], unique=False)
    op.create_index("ix_requests_status", "requests", ["status"], unique=False)
    op.create_index("ix_requests_assigned_group", "requests", ["assigned_group"], unique=False)

    # Create request_assignments table
    op.create_table(
        "request_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("specialist_id", sa.Integer(), nullable=False),
        sa.Column("status", assignment_status, nullable=False, default="PENDING"),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", "specialist_id", name="uq_request_specialist"),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"]),
        sa.ForeignKeyConstraint(["specialist_id"], ["specialists.id"]),
    )
    op.create_index("ix_request_assignments_request_id", "request_assignments", ["request_id"], unique=False)
    op.create_index("ix_request_assignments_specialist_id", "request_assignments", ["specialist_id"], unique=False)


def downgrade() -> None:
    op.drop_table("request_assignments")
    op.drop_table("requests")
    op.drop_table("specialists")
    op.drop_table("groups")
    op.drop_table("users")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS assignmentstatus")
    op.execute("DROP TYPE IF EXISTS requeststatus")
    op.execute("DROP TYPE IF EXISTS userrole")
