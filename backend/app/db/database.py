from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

db_url="postgresql://postgres:root@localhost:5432/campusmind"
engine=create_engine(db_url)
session = sessionmaker(autoflush=False,bind=engine)