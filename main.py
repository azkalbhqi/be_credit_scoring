from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router as credit_router
from pipeline.step3_scoring import load_models
from core.database import init_db
from core.supabase_storage import storage_client

app = FastAPI(title="BNI Credit Scoring System - 5 Layer Architecture")

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development ease, or specify ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("Memulai aplikasi...")
    init_db()  # Inisialisasi Tabel Database
    load_models()
    try:
        storage_client.init_buckets()  # Inisialisasi Bucket Supabase Storage
    except Exception as e:
        print(f"Gagal menginisialisasi bucket Supabase Storage: {e}")

app.include_router(credit_router, tags=["Credit Scoring Pipeline"])

@app.get("/")
async def root():
    return {
        "message": "Selamat datang di BNI Credit Scoring API (5-Step Pipeline).",
        "docs_url": "/docs",
        "pipeline_endpoint": "/process-credit"
    }