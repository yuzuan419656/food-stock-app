from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import engine, Base
from app.models import Ingredient, Inventory
from app.routers import ingredients


Base.metadata.create_all(bind=engine)

app = FastAPI()


app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(ingredients.router)