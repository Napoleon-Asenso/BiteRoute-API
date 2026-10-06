"""Aggregated API router for v1 endpoints."""

from fastapi import APIRouter
from app.api.v1 import health, orders, restaurants

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(restaurants.router)
api_router.include_router(orders.router)
