from app.extensions import Base
from app.models.track import Track  # noqa: F401
from app.models.user import User  # noqa: F401


def upgrade(engine):
    Base.metadata.create_all(bind=engine)