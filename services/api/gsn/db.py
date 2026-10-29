import os
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import create_engine, String, Text, JSON, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

def now():
    return datetime.now(timezone.utc)

def uid():
    return str(uuid4())

class Base(DeclarativeBase):
    pass

class Tenant(Base):
    __tablename__ = 'tenants'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120))

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey('tenants.id'), index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)

class SessionToken(Base):
    __tablename__ = 'sessions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class Record(Base):
    """Tenant-scoped Phase 1 entities. Payloads validated by endpoint schemas."""
    __tablename__ = 'records'
    __table_args__ = (UniqueConstraint('tenant_id', 'kind', 'request_key'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey('tenants.id'), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    request_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

engine = create_engine(os.getenv('DATABASE_URL', 'sqlite:///./gsn.db'))
Session = sessionmaker(engine, expire_on_commit=False)

def get_db():
    with Session() as db:
        yield db
