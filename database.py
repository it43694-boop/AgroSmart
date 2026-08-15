import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
if not DATABASE_URL:
    if ENVIRONMENT == "production":
        raise RuntimeError("DATABASE_URL must be configured in production and must not use the local SQLite fallback.")
    DATABASE_URL = "sqlite:///./agro_smart.db"
elif ENVIRONMENT == "production" and DATABASE_URL.startswith("sqlite"):
    raise RuntimeError("DATABASE_URL must point to a production database URL in production, not SQLite.")

engine_kwargs = {
    "echo": False,
    "future": True,
    "pool_pre_ping": True,
}
if not DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update(
        {
            "pool_size": int(os.getenv("DB_POOL_SIZE", "20")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
        }
    )

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def validate_database_url() -> None:
    if ENVIRONMENT == "production":
        if not DATABASE_URL or DATABASE_URL.startswith("sqlite"):
            raise RuntimeError("DATABASE_URL must be configured to a production database URL in production.")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from models import (
        User,
        Crop,
        Field,
        FinanceRecord,
        Loan,
        Insurance,
        SensorReading,
        RefreshToken,
        PasswordResetToken,
        AuditLog,
        MarketplaceListing,
        MarketplaceOrder,
        MarketplaceReview,
        MarketplacePayment,
        PaymentIdempotency,
        BlockchainTrace,
        CommunityToken,
        MarketplaceTransaction,
        Cooperative,
        CooperativeMember,
        CooperativeContribution,
        CooperativeGroupPurchase,
        CooperativePurchaseParticipant,
        ResourceExchange,
        RecyclingRecord,
        SocialPost,
        SocialComment,
        SocialGroup,
        SocialGroupMember,
        LearningCourse,
        Webinar,
        WebinarRegistration,
        CooperativeTraining,
        TrainingParticipant,
        SocialPostLike,
        LearningEnrollment,
        SatelliteObservation,
        PaymentIdempotency,
    )
    # In development/testing we create tables automatically and apply lightweight
    # compatibility migrations. In production, schema must be managed with Alembic
    # and PostgreSQL. Do NOT perform runtime ALTER TABLE in production.
    if ENVIRONMENT == "production":
        # ensure alembic_version table exists (user must run `alembic upgrade head`)
        conn = engine.connect()
        try:
            # SQLite uses sqlite_master; Postgres exposes regclass via to_regclass
            if DATABASE_URL.startswith("sqlite"):
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"))
                found = bool(result.fetchone())
            else:
                # to_regclass returns None when missing
                result = conn.execute(text("SELECT to_regclass('public.alembic_version')"))
                row = result.fetchone()
                found = bool(row and row[0])
            if not found:
                raise RuntimeError("Production environments must apply migrations via Alembic. Run: alembic upgrade head")
        finally:
            conn.close()
    else:
        Base.metadata.create_all(bind=engine)
        _run_runtime_compatibility_migrations()


def _run_runtime_compatibility_migrations() -> None:
    """Run best-effort compatibility migrations only for local development/testing.

    Production schema governance must remain Alembic-only. This helper intentionally
    keeps runtime ALTER TABLE operations isolated behind an explicit non-production
    gate so the production bootstrap path cannot silently rely on them.
    """
    if ENVIRONMENT == "production":
        return
    if not DATABASE_URL or not DATABASE_URL.startswith("sqlite"):
        return

    _migrate_users_table()
    _migrate_sensor_readings_table()
    _migrate_marketplace_payments_table()
    _migrate_refresh_tokens_table()
    _migrate_password_reset_tokens_table()


def _migrate_users_table():
    conn = engine.connect()
    try:
        result = conn.execute(text("PRAGMA table_info(users)"))
        existing_columns = {row[1] for row in result.fetchall()}
        migration_statements = []

        if "role" not in existing_columns:
            migration_statements.append("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'farmer'")
        if "username" not in existing_columns:
            migration_statements.append("ALTER TABLE users ADD COLUMN username VARCHAR")
        if "failed_login_attempts" not in existing_columns:
            migration_statements.append("ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0")
        if "locked_until" not in existing_columns:
            migration_statements.append("ALTER TABLE users ADD COLUMN locked_until DATETIME")
        if "mfa_enabled" not in existing_columns:
            migration_statements.append("ALTER TABLE users ADD COLUMN mfa_enabled BOOLEAN DEFAULT 0")
        if "mfa_secret" not in existing_columns:
            migration_statements.append("ALTER TABLE users ADD COLUMN mfa_secret VARCHAR")
        if "mfa_backup_codes" not in existing_columns:
            migration_statements.append("ALTER TABLE users ADD COLUMN mfa_backup_codes VARCHAR")
        if "updated_at" not in existing_columns:
            migration_statements.append("ALTER TABLE users ADD COLUMN updated_at DATETIME")
        if "account_type" not in existing_columns:
            migration_statements.append("ALTER TABLE users ADD COLUMN account_type VARCHAR DEFAULT 'farmer'")
        if "village" not in existing_columns:
            migration_statements.append("ALTER TABLE users ADD COLUMN village VARCHAR")

        for stmt in migration_statements:
            conn.execute(text(stmt))
    finally:
        conn.close()


def _migrate_sensor_readings_table():
    conn = engine.connect()
    try:
        result = conn.execute(text("PRAGMA table_info(sensor_readings)"))
        existing_columns = {row[1] for row in result.fetchall()}
        stmts = []
        if 'crop_id' not in existing_columns:
            stmts.append("ALTER TABLE sensor_readings ADD COLUMN crop_id INTEGER")
        if 'device_id' not in existing_columns:
            stmts.append("ALTER TABLE sensor_readings ADD COLUMN device_id VARCHAR")
        if 'metadata' not in existing_columns:
            stmts.append("ALTER TABLE sensor_readings ADD COLUMN metadata TEXT")
        for s in stmts:
            try:
                conn.execute(text(s))
            except Exception:
                # best-effort migration in dev only
                pass

        result = conn.execute(text("PRAGMA table_info(blockchain_traces)"))
        existing_columns = {row[1] for row in result.fetchall()}
        blockchain_stmts = []
        if 'product_type' not in existing_columns:
            blockchain_stmts.append("ALTER TABLE blockchain_traces ADD COLUMN product_type VARCHAR")
        if 'origin_info' not in existing_columns:
            blockchain_stmts.append("ALTER TABLE blockchain_traces ADD COLUMN origin_info VARCHAR")
        if 'carbon_score' not in existing_columns:
            blockchain_stmts.append("ALTER TABLE blockchain_traces ADD COLUMN carbon_score FLOAT")
        if 'durability_label' not in existing_columns:
            blockchain_stmts.append("ALTER TABLE blockchain_traces ADD COLUMN durability_label VARCHAR")
        if 'qr_code_data' not in existing_columns:
            blockchain_stmts.append("ALTER TABLE blockchain_traces ADD COLUMN qr_code_data VARCHAR")
        if 'verified' not in existing_columns:
            blockchain_stmts.append("ALTER TABLE blockchain_traces ADD COLUMN verified BOOLEAN DEFAULT 0")
        if 'metadata' not in existing_columns:
            blockchain_stmts.append("ALTER TABLE blockchain_traces ADD COLUMN metadata TEXT")
        if 'tx_hash' not in existing_columns:
            blockchain_stmts.append("ALTER TABLE blockchain_traces ADD COLUMN tx_hash VARCHAR")
        if 'crop_id' not in existing_columns:
            blockchain_stmts.append("ALTER TABLE blockchain_traces ADD COLUMN crop_id INTEGER")
        for s in blockchain_stmts:
            try:
                conn.execute(text(s))
            except Exception:
                # best-effort migration in dev only
                pass

        try:
            conn.execute(text("PRAGMA table_info(blockchain_traces)"))
        except Exception:
            pass

        # Make crop_id nullable for compatibility with existing schema variants.
        try:
            conn.execute(text("ALTER TABLE blockchain_traces RENAME COLUMN crop_id TO crop_id_old"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE blockchain_traces ADD COLUMN crop_id INTEGER"))
        except Exception:
            pass
        for s in blockchain_stmts:
            try:
                conn.execute(text(s))
            except Exception:
                # best-effort migration in dev only
                pass
    finally:
        conn.close()


def _migrate_marketplace_payments_table():
    conn = engine.connect()
    try:
        result = conn.execute(text("PRAGMA table_info(marketplace_payments)"))
        existing_columns = {row[1] for row in result.fetchall()}
        stmts = []

        if 'payment_gateway_response' not in existing_columns:
            stmts.append("ALTER TABLE marketplace_payments ADD COLUMN payment_gateway_response VARCHAR")
        if 'failure_reason' not in existing_columns:
            stmts.append("ALTER TABLE marketplace_payments ADD COLUMN failure_reason VARCHAR")

        for stmt in stmts:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass
    finally:
        conn.close()


def _migrate_refresh_tokens_table():
    conn = engine.connect()
    try:
        result = conn.execute(text("PRAGMA table_info(refresh_tokens)"))
        existing_columns = {row[1] for row in result.fetchall()}
        stmts = []

        if 'jti' not in existing_columns:
            stmts.append("ALTER TABLE refresh_tokens ADD COLUMN jti VARCHAR")
        if 'token_hash' not in existing_columns:
            stmts.append("ALTER TABLE refresh_tokens ADD COLUMN token_hash VARCHAR")

        for stmt in stmts:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass

        try:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_refresh_tokens_token_hash ON refresh_tokens (token_hash)"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_refresh_tokens_jti ON refresh_tokens (jti)"))
        except Exception:
            pass
    finally:
        conn.close()


def _migrate_password_reset_tokens_table():
    conn = engine.connect()
    try:
        result = conn.execute(text("PRAGMA table_info(password_reset_tokens)"))
        existing_columns = {row[1] for row in result.fetchall()}
        stmts = []

        if 'token_hash' not in existing_columns:
            stmts.append("ALTER TABLE password_reset_tokens ADD COLUMN token_hash VARCHAR")

        for stmt in stmts:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass

        try:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_password_reset_tokens_token_hash ON password_reset_tokens (token_hash)"))
        except Exception:
            pass
    finally:
        conn.close()
