from typing import Any, Dict
from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class Device(Base, TimestampMixin):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device_uuid: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    device_name: Mapped[str] = mapped_column(String(100), default="FLUX Desk Companion (ESP32)")
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DeviceLog(Base, TimestampMixin):
    __tablename__ = "device_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    telemetry: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
