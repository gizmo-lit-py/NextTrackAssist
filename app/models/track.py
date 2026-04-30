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
        # Camelot Wheel: 1A〜12A / 1B〜12B の 24 値のみ許容。
        # regex はDB方言差が大きいので、ポータブルな IN 列挙で表現する。
        CheckConstraint(
            "key IN ('1A','1B','2A','2B','3A','3B','4A','4B','5A','5B','6A','6B',"
            "'7A','7B','8A','8B','9A','9B','10A','10B','11A','11B','12A','12B')",
            name="check_key_camelot",
        ),
    )