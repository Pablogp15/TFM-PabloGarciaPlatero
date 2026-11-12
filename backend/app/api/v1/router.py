"""Router agregador de la versión 1 de la API."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, generations, guides, inventory, paints, projects, wishlist

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(paints.router)
api_router.include_router(inventory.router)
api_router.include_router(projects.router)
api_router.include_router(generations.router)

api_router.include_router(wishlist.router)

api_router.include_router(guides.router)
