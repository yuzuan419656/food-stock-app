from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import (
    ingredient_duplicates,
    ingredients,
    inventory,
)


app = FastAPI()

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)

app.include_router(ingredients.router)
app.include_router(ingredient_duplicates.router)
app.include_router(inventory.router)