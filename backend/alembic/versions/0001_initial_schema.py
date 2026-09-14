"""Baseline schema for FLUX ONE v0.1

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Enums
    subject_type_enum = sa.Enum('THEORY', 'LAB', 'SEMINAR', 'PROJECT', name='subject_type_enum')
    identity_provider_enum = sa.Enum('LOCAL', 'GOOGLE', name='identity_provider_enum')
    enrollment_status_enum = sa.Enum('ACTIVE', 'DROPPED', 'COMPLETED', name='enrollment_status_enum')
    session_status_enum = sa.Enum('CREATED', 'ACTIVE', 'PAUSED', 'COMPLETED', 'ABANDONED', name='session_status_enum')
    session_source_enum = sa.Enum('MANUAL', 'MOBILE', 'ESP32', 'API', name='session_source_enum')

    # 2. Institutional Hierarchy
    op.create_table(
        'colleges',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('time_zone', sa.String(length=50), server_default='Asia/Kolkata', nullable=False),
        sa.Column('erp_portal_url', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_colleges_code'), 'colleges', ['code'], unique=True)
    op.create_index(op.f('ix_colleges_id'), 'colleges', ['id'], unique=False)

    op.create_table(
        'departments',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('college_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['college_id'], ['colleges.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('college_id', 'code', name='uq_department_college_code')
    )
    op.create_index('ix_departments_college_id', 'departments', ['college_id'], unique=False)
    op.create_index(op.f('ix_departments_id'), 'departments', ['id'], unique=False)

    op.create_table(
        'semesters',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('department_id', sa.BigInteger(), nullable=False),
        sa.Column('semester_number', sa.SmallInteger(), nullable=False),
        sa.Column('academic_year', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('department_id', 'semester_number', 'academic_year', name='uq_semester_dept_num_year')
    )
    op.create_index('ix_semesters_department_id', 'semesters', ['department_id'], unique=False)
    op.create_index(op.f('ix_semesters_id'), 'semesters', ['id'], unique=False)

    op.create_table(
        'divisions',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('semester_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('semester_id', 'name', name='uq_division_semester_name')
    )
    op.create_index('ix_divisions_semester_id', 'divisions', ['semester_id'], unique=False)
    op.create_index(op.f('ix_divisions_id'), 'divisions', ['id'], unique=False)

    op.create_table(
        'subjects',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('semester_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('code', sa.String(length=30), nullable=False),
        sa.Column('credits', sa.SmallInteger(), server_default='3', nullable=False),
        sa.Column('subject_type', subject_type_enum, server_default='THEORY', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('semester_id', 'code', name='uq_subject_semester_code')
    )
    op.create_index('ix_subjects_semester_id', 'subjects', ['semester_id'], unique=False)
    op.create_index(op.f('ix_subjects_id'), 'subjects', ['id'], unique=False)

    op.create_table(
        'topics',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('subject_id', sa.BigInteger(), nullable=False),
        sa.Column('unit_number', sa.SmallInteger(), server_default='1', nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('subject_id', 'unit_number', 'title', name='uq_topic_subject_unit_title')
    )
    op.create_index('ix_topics_subject_id', 'topics', ['subject_id'], unique=False)
    op.create_index(op.f('ix_topics_id'), 'topics', ['id'], unique=False)

    op.create_table(
        'timetable_slots',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('semester_id', sa.BigInteger(), nullable=False),
        sa.Column('division_id', sa.BigInteger(), nullable=False),
        sa.Column('subject_id', sa.BigInteger(), nullable=False),
        sa.Column('day_of_week', sa.SmallInteger(), nullable=False, comment='1=Monday, 7=Sunday'),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('location', sa.String(length=100), nullable=False),
        sa.Column('instructor_name', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['division_id'], ['divisions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('division_id', 'day_of_week', 'start_time', name='uq_timetable_slot_division_day_time')
    )
    op.create_index('ix_timetable_slots_division_day', 'timetable_slots', ['division_id', 'day_of_week'], unique=False)
    op.create_index(op.f('ix_timetable_slots_id'), 'timetable_slots', ['id'], unique=False)

    # 3. Student Identity & Profile
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('college_id', sa.BigInteger(), nullable=False),
        sa.Column('department_id', sa.BigInteger(), nullable=False),
        sa.Column('division_id', sa.BigInteger(), nullable=True),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('prn_number', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('version_id', sa.Integer(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['college_id'], ['colleges.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['division_id'], ['divisions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('prn_number', name='uq_users_prn_number')
    )
    op.create_index('ix_users_college_dept_div', 'users', ['college_id', 'department_id', 'division_id'], unique=False)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_prn_number'), 'users', ['prn_number'], unique=False)

    op.create_table(
        'user_identities',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('provider', identity_provider_enum, server_default='LOCAL', nullable=False),
        sa.Column('provider_user_id', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('email_verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('token_version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', name='uq_user_identities_email'),
        sa.UniqueConstraint('provider', 'provider_user_id', name='uq_user_identities_provider_user')
    )
    op.create_index(op.f('ix_user_identities_email'), 'user_identities', ['email'], unique=False)
    op.create_index(op.f('ix_user_identities_id'), 'user_identities', ['id'], unique=False)
    op.create_index('ix_user_identities_user_id', 'user_identities', ['user_id'], unique=False)

    op.create_table(
        'enrollments',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('subject_id', sa.BigInteger(), nullable=False),
        sa.Column('status', enrollment_status_enum, server_default='ACTIVE', nullable=False),
        sa.Column('enrolled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'subject_id', name='uq_enrollment_user_subject')
    )
    op.create_index('ix_enrollments_subject_id', 'enrollments', ['subject_id'], unique=False)
    op.create_index('ix_enrollments_user_id', 'enrollments', ['user_id'], unique=False)
    op.create_index(op.f('ix_enrollments_id'), 'enrollments', ['id'], unique=False)

    op.create_table(
        'streaks',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('current_streak', sa.Integer(), server_default='0', nullable=False),
        sa.Column('longest_streak', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_study_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_streaks_user_id')
    )
    op.create_index(op.f('ix_streaks_id'), 'streaks', ['id'], unique=False)

    op.create_table(
        'academic_brains',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('total_study_minutes', sa.Integer(), server_default='0', nullable=False),
        sa.Column('average_focus_rating', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('consistency_score', sa.Float(), server_default='100.0', nullable=False),
        sa.Column('average_quiz_score', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('last_ai_update', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_academic_brains_user_id')
    )
    op.create_index(op.f('ix_academic_brains_id'), 'academic_brains', ['id'], unique=False)

    # 4. Study Sessions with Partial Index
    op.create_table(
        'study_sessions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('subject_id', sa.BigInteger(), nullable=False),
        sa.Column('topic_id', sa.BigInteger(), nullable=True),
        sa.Column('status', session_status_enum, server_default='ACTIVE', nullable=False),
        sa.Column('source', session_source_enum, server_default='MOBILE', nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_heartbeat_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('accumulated_active_seconds', sa.Integer(), server_default='0', nullable=False),
        sa.Column('target_duration_minutes', sa.Integer(), server_default='45', nullable=True),
        sa.Column('focus_rating', sa.SmallInteger(), nullable=True),
        sa.Column('reflection_note', sa.Text(), nullable=True),
        sa.Column('version_id', sa.Integer(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('focus_rating IS NULL OR (focus_rating >= 1 AND focus_rating <= 5)', name='ck_focus_rating_range'),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_study_sessions_id'), 'study_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_study_sessions_user_id'), 'study_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_study_sessions_subject_id'), 'study_sessions', ['subject_id'], unique=False)
    op.create_index(op.f('ix_study_sessions_topic_id'), 'study_sessions', ['topic_id'], unique=False)
    op.create_index(op.f('ix_study_sessions_status'), 'study_sessions', ['status'], unique=False)
    op.create_index('ix_study_sessions_user_start', 'study_sessions', ['user_id', 'start_time'], unique=False)

    # Partial unique index
    op.create_index(
        'uq_user_active_session',
        'study_sessions',
        ['user_id'],
        unique=True,
        postgresql_where=sa.text("status IN ('ACTIVE', 'PAUSED')"),
    )


def downgrade() -> None:
    op.drop_index('uq_user_active_session', table_name='study_sessions')
    op.drop_index('ix_study_sessions_user_start', table_name='study_sessions')
    op.drop_table('study_sessions')
    op.drop_table('academic_brains')
    op.drop_table('streaks')
    op.drop_table('enrollments')
    op.drop_table('user_identities')
    op.drop_table('users')
    op.drop_table('timetable_slots')
    op.drop_table('topics')
    op.drop_table('subjects')
    op.drop_table('divisions')
    op.drop_table('semesters')
    op.drop_table('departments')
    op.drop_table('colleges')
    op.execute('DROP TYPE IF EXISTS session_source_enum')
    op.execute('DROP TYPE IF EXISTS session_status_enum')
    op.execute('DROP TYPE IF EXISTS enrollment_status_enum')
    op.execute('DROP TYPE IF EXISTS identity_provider_enum')
    op.execute('DROP TYPE IF EXISTS subject_type_enum')
