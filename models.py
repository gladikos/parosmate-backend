# models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship

from datetime import datetime, timedelta

SQLALCHEMY_DATABASE_URL = "sqlite:///./database.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    surname = Column(String)
    mobile = Column(String)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    favorites = relationship("FavoritePlace", back_populates="user")
    created_at = Column(DateTime, default=datetime.utcnow)

class Itinerary(Base):
    __tablename__ = "itineraries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    days = Column(Integer)
    adults = Column(Integer)
    children = Column(Integer)
    transportation = Column(String)
    age_range = Column(String)
    budget = Column(String)
    priorities = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class FavoritePlace(Base):
    __tablename__ = "favorite_places"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    description = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="favorites")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
