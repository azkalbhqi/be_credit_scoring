from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from fastapi.responses import FileResponse
from api.schemas import CreditInput, CreditResponse, RulesTestInput, RagTestInput, ReportTestInput
from pipeline.step1_ocr import extract_data_from_documents
from pipeline.step2_rules import check_hard_rules
from pipeline.step3_scoring import run_ml_scoring
from pipeline.step4_rag import generate_action_plan
from pipeline.step5_report import generate_pdf_report
from core.database import save_application_record, Base, engine
import os
import shutil

router = APIRouter()

@router.post("/process-credit", response_model=CreditResponse)
async def process_credit_pipeline(
    file: UploadFile = File(...),
    produk: str = Form("KUR")
):
    """
    Endpoint utama untuk memproses pipeline 5 langkah credit scoring bertenaga AI dari file PDF tunggal.
    """
    # 1. Simpan file PDF secara sementara
    temp_dir = "temp_uploads"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        
    temp_file_path = os.path.join(temp_dir, file.filename)
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengunggah berkas PDF: {str(e)}")
        
    try:
        # 1. OCR & AI Parameter Extraction Layer
        ocr_result = extract_data_from_documents(temp_file_path)
        if ocr_result.get("status") == "ERROR":
            # Hapus file sementara
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            
            response = CreditResponse(
                status="REJECT",
                message=f"OCR Validation Error: {', '.join(ocr_result.get('errors', []))}",
                ai_summary=ocr_result.get("data", {}).get("summary", ""),
                detected_anomalies=ocr_result.get("data", {}).get("anomalies", [])
            )
            return response
        
        ocr_data = ocr_result.get("data", {})
        full_name = ocr_data.get("full_name", "Nasabah")
        
        # Tambahkan produk ke merged_data agar dibaca check_hard_rules
        merged_data = {**ocr_data, "produk": produk}
        
        # 2. Hard Rules / Pre-screening Layer
        is_passed, reason = check_hard_rules(merged_data)
        if not is_passed:
            response_dict = {
                "status": "REJECT",
                "message": reason,
                "full_name": full_name,
                "nama_hasil_analisis": f"Analisis Kredit - {full_name} (Rejected by Hard Rules)",
                "file_pdf": None,
                "ai_summary": ocr_data.get("summary", ""),
                "detected_anomalies": ocr_data.get("anomalies", [])
            }
            save_application_record(response_dict)
            return CreditResponse(**response_dict)
            
        # 3. ML Scoring Layer (Random Forest)
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
        
        # 5. Generate PDF Report Layer
        report_data = {
            **ocr_data,
            "credit_score": credit_score,
            "kategori_risiko": kategori,
            "analisis": analisis,
            "narasi_rag": narasi,
            "action_plan": action_plan
        }
        
        try:
            pdf_path = generate_pdf_report(report_data)
            pdf_filename = os.path.basename(pdf_path)
        except Exception as e:
            print(f"PDF Error: {e}")
            pdf_filename = None

        # Final Output Preparation
        response_data = {
            "status": "APPROVE" if credit_score >= 500 else "REJECT",
            "credit_score": credit_score,
            "kategori_risiko": kategori,
            "analisis": analisis,
            "narasi_rag": narasi,
            "action_plan": action_plan,
            "message": f"Pipeline berhasil. Report PDF: {pdf_filename}" if pdf_filename else "Pipeline berhasil tanpa PDF.",
            "full_name": full_name,
            "nama_hasil_analisis": f"Analisis Kredit - {full_name}",
            "file_pdf": pdf_filename,
            "ai_summary": ocr_data.get("summary", ""),
            "detected_anomalies": ocr_data.get("anomalies", [])
        }
        
        # Simpan ke Database
        save_application_record(response_data)
        
        return CreditResponse(**response_data)
        
    finally:
        # Selalu bersihkan temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@router.get("/download-report/{filename}")
async def download_report(filename: str):
    """
    Endpoint untuk mendownload file PDF report.
    """
    file_path = os.path.join("reports", filename)
    if os.path.exists(file_path):
        return FileResponse(path=file_path, filename=filename, media_type='application/pdf')
    raise HTTPException(status_code=404, detail="File report tidak ditemukan.")

# =====================================================================
# ADMIN & TESTING ENDPOINTS (STEP-BY-STEP TESTING FOR SWAGGER)
# =====================================================================

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
async def test_step1_ocr(file: UploadFile = File(...)):
    """
    Test Step 1: OCR & Data Extraction Layer.
    Extracts text variables and runs AI analysis from an uploaded PDF.
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
async def test_step2_rules(data: RulesTestInput):
    """
    Test Step 2: Hard Rules Pre-screening Layer.
    Takes loan details and verifies against pre-screening policy logic.
    """
    is_passed, reason = check_hard_rules(data.dict())
    return {
        "passed": is_passed,
        "reason": reason
    }

@router.post("/test/step3-scoring", tags=["Step-by-Step Testing"])
async def test_step3_scoring(data: CreditInput):
    """
    Test Step 3: Refinement ML Scoring Layer.
    Runs the input features through the Random Forest model and generates credit score & key indicators.
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
async def test_step4_rag(data: RagTestInput):
    """
    Test Step 4: Contextual Reasoning Layer (RAG).
    Queries OpenRouter API for credit recommendation narratives and action plan. Falls back gracefully if LLM offline.
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
async def test_step5_report(data: ReportTestInput):
    """
    Test Step 5 (PDF): Report Generation Layer.
    Generates a PDF analysis report and returns details.
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
async def test_step5_db(data: CreditResponse):
    """
    Test Step 5 (DB): Database Persistence Layer.
    Saves credit scoring result to PostgreSQL.
    """
    success = save_application_record(data.dict())
    if success:
        return {"status": "SUCCESS", "message": "Successfully saved to database."}
    raise HTTPException(status_code=500, detail="Failed to save record to database.")
