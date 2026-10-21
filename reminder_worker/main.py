from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from notification.scheduler import start_scheduler,stop_scheduler, router
load_dotenv()

@asynccontextmanager
async def lifespan(app:FastAPI):
        start_scheduler()
        yield
        stop_scheduler()

app=FastAPI(lifespan=lifespan)
app.include_router(router, tags=["notification"])