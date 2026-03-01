from sqlalchemy import Column, Integer, String, CheckConstraint
from db import Base


class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True)

    title = Column(String(255), nullable=False)
    artist = Column(String(255), nullable=False)

    bpm = Column(
        Integer,
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

    __table_args__ = (
        CheckConstraint("bpm BETWEEN 40 AND 250", name="check_bpm_range"),
        CheckConstraint("energy BETWEEN 1 AND 10", name="check_energy_range"),
    )