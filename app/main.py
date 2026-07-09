from fastapi import FastAPI

from app.database import engine, Base
from app.models import Ingredient, Inventory

Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Hello, food-stock-app!"}