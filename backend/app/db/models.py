from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class FileAsset(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    path = Column(String(512), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

class ChatMessage(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db(url: str):
    engine = create_engine(url, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return engine, SessionLocal

def get_session(SessionLocal):
    def _get():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    return _get
