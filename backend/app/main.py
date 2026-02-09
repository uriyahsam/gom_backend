from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .settings import settings
from .init_db import init_db
from .routes import auth, plans, me, vendor, products, cart, wishlist, checkout, orders, admin, webhooks, telegram

app = FastAPI(title="Ghana Online Market API")

origins = ["*"] if settings.CORS_ORIGINS == "*" else [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(plans.router, prefix="/api", tags=["plans"])
app.include_router(me.router, prefix="/api", tags=["me"])
app.include_router(vendor.router, prefix="/api/vendor", tags=["vendor"])
app.include_router(products.router, prefix="/api", tags=["products"])
app.include_router(cart.router, prefix="/api", tags=["cart"])
app.include_router(wishlist.router, prefix="/api", tags=["wishlist"])
app.include_router(checkout.router, prefix="/api/checkout", tags=["checkout"])
app.include_router(orders.router, prefix="/api", tags=["orders"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(webhooks.router, prefix="/api", tags=["webhooks"])
app.include_router(telegram.router, prefix="/telegram", tags=["telegram"])

@app.get("/health")
def health():
    return {"ok": True}
