import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
db_url = os.getenv("DATABASE_URL", "postgresql://postgres:root@localhost:5432/campusmind")
engine=create_engine(db_url)
session = sessionmaker(autoflush=False,bind=engine)

#This is not put in asynccontextmanager like Postgressaver, because this will open/close a connection for each request, but that state connection is opened only once
def get_db():
    with session() as db:
        yield db
