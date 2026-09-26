"""Enterprise ORM models (Phase 4)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover
    Vector = None  # type: ignore


def _uuid() -> str:
    return uuid.uuid4().hex


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="active")
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal(0))
    credit_used: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal(0))
    country: Mapped[str] = mapped_column(String(64), default="US")

    contracts: Mapped[list[CustomerContract]] = relationship(back_populates="customer")
    orders: Mapped[list[Order]] = relationship(back_populates="customer")


class CustomerContract(Base, TimestampMixin):
    __tablename__ = "customer_contracts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    contract_number: Mapped[str] = mapped_column(String(64), unique=True)
    discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal(0))
    payment_terms: Mapped[str] = mapped_column(String(64), default="NET30")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    customer: Mapped[Customer] = relationship(back_populates="contracts")


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(64), default="general")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    inventory: Mapped[Inventory | None] = relationship(back_populates="product", uselist=False)
    pricing_conditions: Mapped[list[PricingCondition]] = relationship(back_populates="product")


class Inventory(Base, TimestampMixin):
    __tablename__ = "inventory"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), unique=True, index=True)
    warehouse: Mapped[str] = mapped_column(String(64), default="MAIN")
    on_hand: Mapped[int] = mapped_column(Integer, default=0)
    reserved: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped[Product] = relationship(back_populates="inventory")

    @property
    def available(self) -> int:
        return max(self.on_hand - self.reserved, 0)


class PricingCondition(Base, TimestampMixin):
    __tablename__ = "pricing_conditions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal(0))
    min_qty: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    product: Mapped[Product | None] = relationship(back_populates="pricing_conditions")


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    order_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal(0))
    discount_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal(0))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal(0))
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    workflow_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    customer: Mapped[Customer] = relationship(back_populates="orders")
    items: Mapped[list[OrderItem]] = relationship(back_populates="order", cascade="all, delete-orphan")
    approvals: Mapped[list[Approval]] = relationship(back_populates="order")


class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    sku: Mapped[str] = mapped_column(String(64))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal(0))
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal(0))

    order: Mapped[Order] = relationship(back_populates="items")


class Approval(Base, TimestampMixin):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    workflow_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|approved|rejected
    approval_type: Mapped[str] = mapped_column(String(64), default="general")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped[Order | None] = relationship(back_populates="approvals")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(128))
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    workflow_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    description: Mapped[str] = mapped_column(String(255), default="")


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))

    permissions: Mapped[list[RolePermission]] = relationship(back_populates="role", cascade="all, delete-orphan")
    users: Mapped[list[User]] = relationship(back_populates="role")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), index=True)
    permission_id: Mapped[str] = mapped_column(ForeignKey("permissions.id"), index=True)

    role: Mapped[Role] = relationship(back_populates="permissions")
    permission: Mapped[Permission] = relationship()


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    role_id: Mapped[str | None] = mapped_column(ForeignKey("roles.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    role: Mapped[Role | None] = relationship(back_populates="users")


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), default="")

    messages: Mapped[list[ConversationMessage]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class WorkflowExecution(Base, TimestampMixin):
    __tablename__ = "workflow_executions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    workflow_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="running")
    intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_request: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    steps_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class PolicyDocument(Base, TimestampMixin):
    __tablename__ = "policy_documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255))
    source_file: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    body: Mapped[str] = mapped_column(Text)

    chunks: Mapped[list[PolicyChunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class PolicyChunk(Base, TimestampMixin):
    __tablename__ = "policy_chunks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("policy_documents.id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    start_char: Mapped[int] = mapped_column(Integer, default=0)
    end_char: Mapped[int] = mapped_column(Integer, default=0)
    # pgvector column when extension available; also kept as JSON for portability
    embedding: Mapped[list | None] = mapped_column(Vector(384) if Vector else Text, nullable=True)

    document: Mapped[PolicyDocument] = relationship(back_populates="chunks")
