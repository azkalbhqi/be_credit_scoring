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

from fastapi.responses import HTMLResponse
from core.config import missing_vars

startup_error = None

@app.middleware("http")
async def check_startup_status(request, call_next):
    # If there are missing environment variables, display a detailed config error page
    if missing_vars:
        error_html = f"""
        <html>
            <head>
                <title>Configuration Error</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 40px; background-color: #fcf8f2; color: #4a3728; }}
                    .card {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border-left: 5px solid #d9534f; }}
                    h1 {{ color: #d9534f; margin-top: 0; }}
                    ul {{ padding-left: 20px; }}
                    li {{ margin-bottom: 8px; font-weight: bold; font-family: monospace; font-size: 1.1em; color: #c9302c; }}
                    .info {{ line-height: 1.6; color: #5a5a5a; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>Configuration Error (Missing Environment Variables)</h1>
                    <p class="info">The application cannot start because the following required environment variables are not set in the Vercel dashboard:</p>
                    <ul>
                        {"".join(f"<li>{var}</li>" for var in missing_vars)}
                    </ul>
                    <p class="info"><strong>Action Required:</strong> Please log in to your Vercel Dashboard, navigate to your Project Settings -> Environment Variables, add these keys, and redeploy.</p>
                </div>
            </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=500)

    # If there was a database initialization or model loading error, display it
    global startup_error
    if startup_error:
        error_html = f"""
        <html>
            <head>
                <title>Startup Initialization Error</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 40px; background-color: #fcf8f2; color: #4a3728; }}
                    .card {{ max-width: 700px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border-left: 5px solid #f0ad4e; }}
                    h1 {{ color: #d9534f; margin-top: 0; }}
                    pre {{ background: #f8f9fa; padding: 15px; border-radius: 6px; border: 1px solid #e1e4e8; overflow-x: auto; font-family: monospace; font-size: 0.9em; }}
                    .info {{ line-height: 1.6; color: #5a5a5a; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>Startup Error</h1>
                    <p class="info">FastAPI started successfully, but an error occurred during the startup event:</p>
                    <pre>{startup_error}</pre>
                    <p class="info">Please verify that your database server (Supabase/PostgreSQL) is running, and that the credentials (especially <strong>DATABASE_URL</strong>) are correct and valid.</p>
                </div>
            </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=500)

    response = await call_next(request)
    return response

@app.on_event("startup")
async def startup_event():
    global startup_error
    print("Memulai aplikasi...")
    
    # If config variables are missing, do not attempt DB connection
    if missing_vars:
        print("Skipping DB and model load due to missing environment variables.")
        return

    try:
        init_db()  # Inisialisasi Tabel Database
    except Exception as e:
        import traceback
        startup_error = f"Database initialization failed:\n{traceback.format_exc()}"
        print(startup_error)
        return
        
    try:
        load_models()
    except Exception as e:
        import traceback
        startup_error = f"Model loading failed:\n{traceback.format_exc()}"
        print(startup_error)
        return
        
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