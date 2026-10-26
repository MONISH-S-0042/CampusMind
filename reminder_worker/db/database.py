import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
load_dotenv()
db_url = os.environ["DATABASE_URL"]
engine=create_engine(db_url)
session = sessionmaker(autoflush=False,bind=engine)

#This is not put in asynccontextmanager like Postgressaver, because this will open/close a connection for each request, but that state connection is opened only once
def get_db():
    with session() as db:
        yield db
