from sqlalchemy import Column, Integer, String, CheckConstraint
from app.extensions import Base

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
        CheckConstraint(
            "key ~ '^(1[0-2]|[1-9])[AB]$'",
            name="check_camelot_key_format"
        )
    )