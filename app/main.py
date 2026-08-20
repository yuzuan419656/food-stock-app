from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import (
    ingredients,
    ingredient_duplicates,
    inventory,
    shopping_list,
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
app.include_router(shopping_list.router)