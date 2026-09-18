from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EnergyDaily(Base):
    __tablename__ = "energy_dailies"
    __table_args__ = (
        UniqueConstraint("workshop_id", "work_date", name="uq_energy_workshop_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workshop_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workshops.id", ondelete="CASCADE"), nullable=False
    )
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    kwh: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    peak_kw: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    workshop: Mapped["Workshop"] = relationship("Workshop", back_populates="energy_dailies")
