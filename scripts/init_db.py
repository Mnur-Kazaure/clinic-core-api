from app.models.base import Base
from app.models.clinic import Clinic
# import other models here...

def init_db(engine):
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    from app.core.database import engine

    # Import models so SQLAlchemy registers them
    import app.models.clinic
    # import other models...

    print("Creating database tables...")
    init_db(engine)
    print("✅ Tables created")