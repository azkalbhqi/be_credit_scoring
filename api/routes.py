from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Depends
from fastapi.responses import FileResponse, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from api.schemas import (
    CreditInput, CreditResponse, RulesTestInput, RagTestInput, ReportTestInput,
    UserCreate, UserResponse, Token
)
from pipeline.step1_ocr import extract_data_from_documents
from pipeline.step2_rules import check_hard_rules
from pipeline.step3_scoring import run_ml_scoring
from pipeline.step4_rag import generate_action_plan
from pipeline.step5_report import generate_pdf_report
from core.database import save_application_record, Base, engine, SessionLocal, CreditApplication, User
from core.supabase_storage import storage_client
from core.config import settings
from sqlalchemy.orm import Session
import os
import shutil
import hashlib
import jwt
import uuid
from datetime import datetime, timedelta

router = APIRouter()


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + ":" + key.hex()

def verify_password(password: str, hashed: str) -> bool:
    try:
        salt_hex, key_hex = hashed.split(":")
        salt = bytes.fromhex(salt_hex)
        key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return new_key == key
    except Exception:
        return False

JWT_SECRET = settings.JWT_SECRET
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 600

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_db():
    if not SessionLocal:
        raise HTTPException(
            status_code=500,
            detail="Database connection is not configured. Please set the DATABASE_URL environment variable."
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Token tidak valid atau telah kedaluwarsa.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

def require_role(allowed_roles: list):
    async def role_dependency(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Akses ditolak. Peran Anda ({current_user.role}) tidak memiliki izin untuk tindakan ini."
            )
        return current_user
    return role_dependency

@router.post("/auth/register", response_model=UserResponse, tags=["Authentication"])
async def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Mendaftarkan pengguna baru dengan peran (manager atau staff).
    """
    if user_in.role not in ["manager", "staff"]:
        raise HTTPException(status_code=400, detail="Peran harus berupa 'manager' atau 'staff'.")
        
    existing_user = db.query(User).filter(User.username == user_in.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username sudah terdaftar.")
        
    existing_email = db.query(User).filter(User.email == user_in.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email sudah terdaftar.")
        
    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        role=user_in.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/auth/login", response_model=Token, tags=["Authentication"])
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login untuk mendapatkan access token JWT (OAuth2 Form). Supports logging in via username or email.
    """
    user = db.query(User).filter(
        (User.username == form_data.username) | (User.email == form_data.username)
    ).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Username/Email atau password salah.")
        
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/auth/me", response_model=UserResponse, tags=["Authentication"])
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Mendapatkan profil pengguna yang sedang login.
    """
    return current_user


@router.post("/process-credit", response_model=CreditResponse, tags=["Credit Scoring Pipeline"])
async def process_credit_pipeline(
    file: UploadFile = File(...),
    produk: str = Form("KUR"),
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint utama untuk memproses pipeline 5 langkah credit scoring bertenaga AI dari file PDF tunggal.
    Mengunggah berkas ke Supabase bucket 'screening_docs' dan hasil laporan PDF ke 'scoring_docs'.
    """
    # temp file sementara sebelum di up
    temp_dir = "temp_uploads"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        
    temp_file_path = os.path.join(temp_dir, file.filename)
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengunggah berkas PDF secara lokal: {str(e)}")
        
    # upload(screening_docs)
    unique_id = str(uuid.uuid4())[:8]
    screening_filename = f"{unique_id}_{file.filename}"
    try:
        storage_client.upload_file("screening_docs", temp_file_path, screening_filename)
    except Exception as e:
        # del temp
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(
            status_code=500,
            detail=f"Gagal mengunggah berkas ke Supabase Storage (screening_docs): {str(e)}"
        )
        
    try:
        # ocr
        ocr_result = extract_data_from_documents(temp_file_path)
        if ocr_result.get("status") == "ERROR":
            response_dict = {
                "status": "REJECT",
                "message": f"OCR Validation Error: {', '.join(ocr_result.get('errors', []))}",
                "ai_summary": ocr_result.get("data", {}).get("summary", ""),
                "detected_anomalies": ocr_result.get("data", {}).get("anomalies", []),
                "screening_file": screening_filename,
                "approval": "PENDING"
            }
            save_application_record(response_dict)
            return CreditResponse(**response_dict)
        
        ocr_data = ocr_result.get("data", {})
        full_name = ocr_data.get("full_name", "Nasabah")
        
        merged_data = {**ocr_data, "produk": produk}
        
        # hard rules
        is_passed, reason = check_hard_rules(merged_data)
        if not is_passed:
            response_dict = {
                "status": "REJECT",
                "message": reason,
                "full_name": full_name,
                "nama_hasil_analisis": f"Analisis Kredit - {full_name} (Rejected by Hard Rules)",
                "file_pdf": None,
                "screening_file": screening_filename,
                "ai_summary": ocr_data.get("summary", ""),
                "detected_anomalies": ocr_data.get("anomalies", []),
                "approval": "PENDING"
            }
            save_application_record(response_dict)
            return CreditResponse(**response_dict)
            
        # ml scoring
        try:
            credit_score, kategori, analisis = run_ml_scoring(ocr_data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Scoring Error: {str(e)}")
            
        # 4. Contextual Reasoning Layer (RAG)
        try:
            narasi, action_plan = generate_action_plan(credit_score, kategori, analisis, produk)
        except Exception as e:
            print(f"RAG Error: {e}")
            narasi = "Gagal mendapatkan narasi dari AI."
            action_plan = "Lakukan peninjauan manual oleh analis."
        
        # pdf report
        report_data = {
            **ocr_data,
            "credit_score": credit_score,
            "kategori_risiko": kategori,
            "analisis": analisis,
            "narasi_rag": narasi,
            "action_plan": action_plan
        }
        
        pdf_filename = None
        try:
            pdf_path = generate_pdf_report(report_data)
            pdf_filename = os.path.basename(pdf_path)
            
            # Upload PDF report ke Supabase Storage (scoring_docs)
            storage_client.upload_file("scoring_docs", pdf_path, pdf_filename)
            
            # del local
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        except Exception as e:
            print(f"PDF Generation/Upload Error: {e}")
            # pdf_filename tetap None jika gagal

        # Final Output Preparation
        response_data = {
            "status": "APPROVE" if credit_score >= 500 else "REJECT",
            "credit_score": credit_score,
            "kategori_risiko": kategori,
            "analisis": analisis,
            "narasi_rag": narasi,
            "action_plan": action_plan,
            "message": f"Pipeline berhasil. Report PDF diunggah ke Supabase Storage: {pdf_filename}" if pdf_filename else "Pipeline berhasil tanpa PDF.",
            "full_name": full_name,
            "nama_hasil_analisis": f"Analisis Kredit - {full_name}",
            "file_pdf": pdf_filename,
            "screening_file": screening_filename,
            "ai_summary": ocr_data.get("summary", ""),
            "detected_anomalies": ocr_data.get("anomalies", []),
            "approval": "PENDING"
        }
        
        # Simpan ke Database
        save_application_record(response_data)
        
        return CreditResponse(**response_data)
        
    finally:
        # del temp
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@router.get("/download-report/{filename}", tags=["Credit Scoring Pipeline"])
async def download_report(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint untuk mendownload file PDF report langsung dari Supabase Storage.
    """
    try:
        file_bytes = storage_client.download_file("scoring_docs", filename)
        return Response(
            content=file_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Berkas report '{filename}' tidak ditemukan di Supabase Storage: {str(e)}"
        )

@router.get("/download-screening/{filename}", tags=["Credit Scoring Pipeline"])
async def download_screening(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint untuk mendownload file PDF screening langsung dari Supabase Storage.
    """
    try:
        file_bytes = storage_client.download_file("screening_docs", filename)
        media_type = "application/pdf"
        if filename.lower().endswith(".png"):
            media_type = "image/png"
        elif filename.lower().endswith((".jpg", ".jpeg")):
            media_type = "image/jpeg"
            
        return Response(
            content=file_bytes,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Berkas screening '{filename}' tidak ditemukan di Supabase Storage: {str(e)}"
        )

@router.get("/applications", response_model=list[CreditResponse], tags=["Credit Scoring Pipeline"])
async def get_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mendapatkan semua riwayat pengajuan kredit dari database, diurutkan dari yang terbaru.
    """
    try:
        records = db.query(CreditApplication).order_by(CreditApplication.created_at.desc()).all()
        return records
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal melakukan query database: {str(e)}")

@router.get("/applications/{id}", response_model=CreditResponse, tags=["Credit Scoring Pipeline"])
async def get_application_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mendapatkan detail pengajuan kredit berdasarkan ID.
    """
    application = db.query(CreditApplication).filter(CreditApplication.id == id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Pengajuan kredit tidak ditemukan.")
    return application

@router.post("/applications/{id}/approve", response_model=CreditResponse, tags=["Manager Approval"])
async def approve_credit_application(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["manager"]))
):
    """
    Menyetujui pengajuan kredit berdasarkan analisis (Hanya untuk peran Manager).
    """
    application = db.query(CreditApplication).filter(CreditApplication.id == id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Pengajuan kredit tidak ditemukan.")
        
    application.approval = "APPROVED"
    application.approved_by = current_user.username
    db.commit()
    db.refresh(application)
    return application

@router.post("/applications/{id}/reject", response_model=CreditResponse, tags=["Manager Approval"])
async def reject_credit_application(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["manager"]))
):
    """
    Menolak pengajuan kredit berdasarkan analisis (Hanya untuk peran Manager).
    """
    application = db.query(CreditApplication).filter(CreditApplication.id == id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Pengajuan kredit tidak ditemukan.")
        
    application.approval = "REJECTED"
    application.approved_by = current_user.username
    db.commit()
    db.refresh(application)
    return application

@router.post("/admin/recreate-db", tags=["Admin Utilities"])
async def recreate_database():
    """
    Drop all tables and recreate them to align PostgreSQL database schema with models.
    """
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        return {"status": "SUCCESS", "message": "Database tables dropped and recreated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Recreation Failed: {str(e)}")

@router.post("/test/step1-ocr", tags=["Step-by-Step Testing"])
async def test_step1_ocr(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Test Step 1: OCR & Data Extraction Layer.
    """
    temp_dir = "temp_uploads"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        
    temp_file_path = os.path.join(temp_dir, file.filename)
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        result = extract_data_from_documents(temp_file_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR Test Failed: {str(e)}")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@router.post("/test/step2-rules", tags=["Step-by-Step Testing"])
async def test_step2_rules(
    data: RulesTestInput,
    current_user: User = Depends(get_current_user)
):
    """
    Test Step 2: Hard Rules Pre-screening Layer.
    """
    is_passed, reason = check_hard_rules(data.dict())
    return {
        "passed": is_passed,
        "reason": reason
    }

@router.post("/test/step3-scoring", tags=["Step-by-Step Testing"])
async def test_step3_scoring(
    data: CreditInput,
    current_user: User = Depends(get_current_user)
):
    """
    Test Step 3: Refinement ML Scoring Layer.
    """
    try:
        credit_score, kategori, analisis = run_ml_scoring(data.dict())
        return {
            "credit_score": credit_score,
            "kategori_risiko": kategori,
            "analisis": analisis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML Scoring Error: {str(e)}")

@router.post("/test/step4-rag", tags=["Step-by-Step Testing"])
async def test_step4_rag(
    data: RagTestInput,
    current_user: User = Depends(get_current_user)
):
    """
    Test Step 4: Contextual Reasoning Layer (RAG).
    """
    try:
        narasi, action_plan = generate_action_plan(data.credit_score, data.kategori_risiko, data.analisis, data.produk)
        return {
            "narasi_rag": narasi,
            "action_plan": action_plan
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG Reasoning Error: {str(e)}")

@router.post("/test/step5-report", tags=["Step-by-Step Testing"])
async def test_step5_report(
    data: ReportTestInput,
    current_user: User = Depends(get_current_user)
):
    """
    Test Step 5 (PDF): Report Generation Layer.
    """
    try:
        pdf_path = generate_pdf_report(data.dict())
        pdf_filename = os.path.basename(pdf_path)
        return {
            "pdf_filename": pdf_filename,
            "download_url": f"/download-report/{pdf_filename}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF Generation Error: {str(e)}")

@router.post("/test/step5-db", tags=["Step-by-Step Testing"])
async def test_step5_db(
    data: CreditResponse,
    current_user: User = Depends(get_current_user)
):
    """
    Test Step 5 (DB): Database Persistence Layer.
    """
    success = save_application_record(data.dict())
    if success:
        return {"status": "SUCCESS", "message": "Successfully saved to database."}
    raise HTTPException(status_code=500, detail="Failed to save record to database.")

