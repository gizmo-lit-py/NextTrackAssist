from sqlalchemy import Column, Integer, Float, String, CheckConstraint, ForeignKey
from sqlalchemy.orm import relationship
from app.extensions import Base


class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(255), nullable=False)

    artist = Column(String(255), nullable=False)

    # BPM は小数も許容（例: 80.5）。整数値もそのまま保存可能。
    bpm = Column(
        Float,
        nullable=False
    )

    key = Column(
        String(3),
        nullable=False
    )

    energy = Column(
        Integer,
        nullable=False
    )

    user = relationship("User", back_populates="tracks")

    __table_args__ = (
        CheckConstraint("bpm BETWEEN 40 AND 250", name="check_bpm_range"),
        CheckConstraint("energy BETWEEN 1 AND 10", name="check_energy_range"),
    )