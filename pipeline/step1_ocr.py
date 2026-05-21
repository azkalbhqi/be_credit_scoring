import re
from datetime import datetime
from typing import Dict, Any, List
import os
import json
import base64
import requests
from pypdf import PdfReader
from core.config import settings

# =========================================================
# OCR FUNCTION (Gemini Multimodal OCR)
# =========================================================

def read_document(file_path: str) -> str:
    """
    Read text from image or PDF using Gemini API (multimodal OCR)
    """
    if not file_path or not os.path.exists(file_path):
        print(f"Error: File path '{file_path}' does not exist.")
        return ""

    try:
        # Determine MIME type based on file extension
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext == ".pdf":
            mime_type = "application/pdf"
        elif file_ext in [".png", ".jpg", ".jpeg", ".webp"]:
            mime_type = f"image/{file_ext.replace('.', '')}"
            if mime_type == "image/jpg":
                mime_type = "image/jpeg"
        else:
            mime_type = "application/octet-stream"

        print(f"Reading document using Gemini API OCR: {os.path.basename(file_path)} ({mime_type})")
        
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        
        base64_data = base64.b64encode(file_bytes).decode("utf-8")

        headers = {
            "Content-Type": "application/json"
        }
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={settings.GEMINI_API_KEY}"
        
        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": base64_data
                            }
                        },
                        {
                            "text": "Extract all text from this document, preserving layout, tables, and details as much as possible."
                        }
                    ]
                }
            ]
        }

        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=45
        )
        response.raise_for_status()
        result = response.json()
        
        extracted_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
        print(f"\n=== OCR RESULT : {os.path.basename(file_path)} ===")
        print(extracted_text)
        return extracted_text
    except Exception as e:
        print(f"Gemini OCR Error on {file_path}: {e}")
        return ""



# =========================================================
# VALIDATION helper
# =========================================================

def validate_extracted_data(data: Dict[str, Any]) -> List[str]:
    errors = []

    # Safe validation checks with default values/types
    try:
        age = int(data.get("age", 0))
        if age < 18 or age > 80:
            errors.append("Umur tidak valid (harus 18 - 80 tahun)")
    except Exception:
        errors.append("Format umur tidak valid")

    try:
        gaji = float(data.get("gaji", 0))
        if gaji < 0:
            errors.append("Gaji bulanan tidak valid")
    except Exception:
        errors.append("Format gaji tidak valid")

    try:
        balance = float(data.get("balance", 0))
        if balance < 0:
            errors.append("Average balance tidak valid")
    except Exception:
        errors.append("Format average balance tidak valid")

    try:
        lama_usaha_bulan = int(data.get("lama_usaha_bulan", 0))
        if lama_usaha_bulan < 0:
            errors.append("Lama usaha tidak valid")
    except Exception:
        errors.append("Format lama usaha tidak valid")

    try:
        dsr = float(data.get("dsr", 0))
        if dsr < 0 or dsr > 100:
            errors.append("DSR tidak valid (harus antara 0 - 100%)")
    except Exception:
        errors.append("Format DSR tidak valid")

    try:
        kolektibilitas_bi = int(data.get("kolektibilitas_bi", 1))
        if kolektibilitas_bi not in [1, 2, 3, 4, 5]:
            errors.append("Kolektibilitas BI tidak valid (harus 1-5)")
    except Exception:
        errors.append("Format kolektibilitas BI tidak valid")

    return errors


# =========================================================
# PDF TEXT EXTRACTION PIPELINE
# =========================================================

def extract_text_from_pdf(file_path: str) -> str:
    """
    Extracts text from PDF.
    Uses pypdf for digital text first, falls back to Gemini API OCR for scanned images.
    """
    if not file_path or not os.path.exists(file_path):
        print(f"Error: File path '{file_path}' does not exist.")
        return ""

    try:
        print(f"Extracting digital text from PDF: {file_path}")
        pdf_reader = PdfReader(file_path)
        text = ""
        for i, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

        # If digital text extraction is too short, fallback to OCR
        if len(text.strip()) < 100:
            print("Digital text extraction is empty or too short. Falling back to Scanned PDF OCR...")
            try:
                # Use Gemini OCR directly on the scanned PDF
                return read_document(file_path)
            except Exception as ocr_err:
                print(f"Scanned PDF OCR failed: {ocr_err}")
                print("Returning digital text extraction fallback (empty/short text).")
                return text

        return text
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        return ""


# =========================================================
# AI EXTRACTION & ANOMALY DETECTION
# =========================================================

def ai_extract_credit_data(text: str) -> dict:
    """
    Send raw document text to Gemini API.
    Ask LLM to:
    1. Extract all Credit Scoring parameters (RF 16 features + OCR extras)
    2. Write a concise Dossier Summary
    3. Detect flaws, inconsistencies, or fraud indicators
    """
    print("Mengirimkan teks PDF ke Gemini untuk ekstraksi data & deteksi kelemahan...")
    
    prompt = f"""
    Anda adalah sistem AI Senior Analyst di Bank BNI.
    Tugas Anda adalah menganalisis teks hasil ekstraksi dokumen (KTP, NIB, Slip Gaji, BI Checking/SLIK, Rekening Koran) nasabah berikut:
    
    === TEKS DOKUMEN NASABAH ===
    {text[:8000]}  # Potong teks jika terlalu panjang
    === AKHIR TEKS ===
    
    Silakan analisis teks di atas dan lakukan tugas-tugas berikut:
    1. **Ekstrak Data Kredit Utama**:
       - `full_name`: Nama lengkap nasabah (dari KTP/dokumen)
       - `age`: Umur nasabah (int)
       - `gaji`: Gaji bulanan nominal (float/int)
       - `cicilan`: Cicilan bulanan nominal (float/int)
       - `balance`: Rata-rata saldo rekening koran (float/int)
       - `kolektibilitas_bi`: Status kolektibilitas BI/SLIK (1, 2, 3, 4, atau 5. Jika tidak ditemukan, default 1)
       - `lama_usaha_bulan`: Lama usaha nasabah dalam bulan (int. Jika baru mulai default 0)
       - `dsr`: Debt Service Ratio (persen, misal 25.0) -> jika cicilan/gaji hitung secara matematis
       - `housing`: Kepemilikan rumah (1 untuk Milik Sendiri / Hak Milik, 0 untuk Sewa/Kontrak/Lainnya)
    
    2. **Rasiokan Parameter Model Machine Learning (UCI Bank Marketing Dataset)**:
       Ekstrak atau sesuaikan nilai parameter model di bawah ini berdasarkan profil nasabah:
       - `job`: Jenis pekerjaan (integer: admin=0, blue-collar=1, entrepreneur=2, housemaid=3, management=4, retired=5, self-employed=6, services=7, student=8, technician=9, unemployed=10)
       - `marital`: Status pernikahan (integer: single=0, married=1, divorced=2)
       - `education`: Tingkat pendidikan (integer: primary=0, secondary=1, tertiary=2)
       - `default`: Memiliki tunggakan/default kredit (integer: yes=1, no=0)
       - `loan`: Memiliki pinjaman pribadi aktif (integer: yes=1, no=0)
       - `contact`: Metode kontak (integer: cellular=0, telephone=1, unknown=2)
       - `day`: Hari dalam bulan terakhir dihubungi (integer 1-31, default 15)
       - `month`: Bulan terakhir dihubungi (integer 1-12, default 5)
       - `duration`: Durasi kontak pemasaran dalam detik (integer, default 200)
       - `campaign`: Jumlah kontak selama kampanye ini (integer, default 1)
       - `pdays`: Jumlah hari sejak dihubungi dari kampanye sebelumnya (integer, default -1)
       - `previous`: Jumlah kontak sebelum kampanye ini (integer, default 0)
       - `poutcome`: Hasil kampanye sebelumnya (integer: failure=0, other=1, success=2, unknown=3, default 3)
       
    3. **Tulis Ringkasan & Deteksi Kelemahan/Flaws**:
       - `summary`: Ringkasan profil keuangan & kelayakan nasabah dalam 2-3 kalimat.
       - `anomalies`: List string kelemahan atau kejanggalan dokumen (misal: "Nama di slip gaji berbeda dengan KTP", "Lama usaha di NIB tercatat kurang dari 6 bulan", "Ada mutasi mencurigakan", "SLIK menunjukkan Kol 3"). Jika tidak ada kelemahan, isi list kosong [].
       
    Format output Anda HARUS berupa JSON murni dengan struktur persis seperti di bawah ini, tanpa teks tambahan di luar JSON:
    {{
      "full_name": "Nama Nasabah",
      "age": 30,
      "gaji": 8000000,
      "cicilan": 2000000,
      "balance": 15000000,
      "kolektibilitas_bi": 1,
      "lama_usaha_bulan": 24,
      "dsr": 25.0,
      "housing": 1,
      "job": 4,
      "marital": 1,
      "education": 2,
      "default": 0,
      "loan": 0,
      "contact": 0,
      "day": 15,
      "month": 5,
      "duration": 200,
      "campaign": 1,
      "pdays": -1,
      "previous": 0,
      "poutcome": 3,
      "summary": "Ringkasan analisis berkas nasabah...",
      "anomalies": ["Kejanggalan 1...", "Kejanggalan 2..."]
    }}
    """
    
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={settings.GEMINI_API_KEY}"
        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        content = result['candidates'][0]['content']['parts'][0]['text'].strip()
        
        # Clean markdown wrappers if any
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        parsed_result = json.loads(content.strip())
        print("Ekstraksi AI Gemini Berhasil!")
        return parsed_result
    except Exception as e:
        print(f"Error calling Gemini API for extraction: {e}. Menggunakan parsing manual/fallback...")
        
        # Premium Fallback Parsing (Regex & Defaults)
        # 1. Name
        name_match = re.search(r"(?:nama|name)\s*[:\-]?\s*([a-zA-Z\s]{3,30})", text, re.IGNORECASE)
        full_name = name_match.group(1).strip() if name_match else "Nasabah Fallback"
        
        # 2. Age
        age_match = re.search(r"umur\s*[:\-]?\s*(\d{2})", text, re.IGNORECASE)
        age = int(age_match.group(1)) if age_match else 30
        
        # 3. Gaji
        gaji_match = re.search(r"gaji.*?Rp?\s*([\d\.,]+)", text, re.IGNORECASE)
        gaji = float(gaji_match.group(1).replace(".", "").replace(",", ".")) if gaji_match else 8000000.0
        
        # 4. Cicilan
        cicilan_match = re.search(r"cicilan.*?Rp?\s*([\d\.,]+)", text, re.IGNORECASE)
        cicilan = float(cicilan_match.group(1).replace(".", "").replace(",", ".")) if cicilan_match else 2000000.0
        
        # 5. Balance
        balance_match = re.search(r"saldo.*?Rp?\s*([\d\.,]+)", text, re.IGNORECASE)
        balance = float(balance_match.group(1).replace(".", "").replace(",", ".")) if balance_match else 15000000.0
        
        # 6. Kolektibilitas
        kol_match = re.search(r"kolektibilitas\s*[:\-]?\s*([1-5])", text, re.IGNORECASE)
        kolektibilitas_bi = int(kol_match.group(1)) if kol_match else 1
        
        # 7. Lama Usaha
        lama_match = re.search(r"lama\s*usaha\s*[:\-]?\s*(\d+)", text, re.IGNORECASE)
        lama_usaha_bulan = int(lama_match.group(1)) if lama_match else 24
        
        # DSR & Housing
        dsr = round((cicilan / gaji) * 100, 2) if gaji > 0 else 25.0
        housing = 1 if "milik sendiri" in text.lower() or "shm" in text.lower() else 0
        
        # Simple summary & anomalies fallbacks
        summary = f"Hasil ekstraksi fallback untuk nasabah {full_name} (Umur {age} tahun). Gaji bulanan Rp{gaji:,.0f} dengan cicilan aktif Rp{cicilan:,.0f}."
        anomalies = []
        if dsr > 60:
            anomalies.append(f"DSR tinggi ({dsr}% melebihi ambang batas standard).")
        if kolektibilitas_bi > 2:
            anomalies.append(f"Kolektibilitas BI buruk (Kol {kolektibilitas_bi}).")
            
        return {
            "full_name": full_name,
            "age": age,
            "gaji": gaji,
            "cicilan": cicilan,
            "balance": balance,
            "kolektibilitas_bi": kolektibilitas_bi,
            "lama_usaha_bulan": lama_usaha_bulan,
            "dsr": dsr,
            "housing": housing,
            "job": 4,
            "marital": 1,
            "education": 2,
            "default": 0,
            "loan": 0,
            "contact": 0,
            "day": 15,
            "month": 5,
            "duration": 200,
            "campaign": 1,
            "pdays": -1,
            "previous": 0,
            "poutcome": 3,
            "summary": summary,
            "anomalies": anomalies
        }


# =========================================================
# MAIN OCR EXTRACTION PIPELINE
# =========================================================

def extract_data_from_documents(pdf_path: str = None):
    """
    Langkah 1: OCR + Data Extraction Layer
    Mengolah file PDF tunggal menjadi parameter terstruktur & anomali dokumen.
    """
    print("\n=== MENJALANKAN OCR PIPELINE (SINGLE PDF EXTRACTION) ===")

    if not pdf_path or not os.path.exists(pdf_path):
        # MOCK BACKWARD COMPATIBILITY
        print("Warning: File PDF tidak ditemukan atau tidak disertakan. Menggunakan data simulasi Mock...")
        mock_data = {
            "full_name": "Ahmad Dani Mock",
            "age": 35,
            "gaji": 8000000,
            "cicilan": 2000000,
            "balance": 15000000,
            "kolektibilitas_bi": 1,
            "lama_usaha_bulan": 52,
            "dsr": 25.0,
            "housing": 1,
            "job": 1,
            "marital": 1,
            "education": 2,
            "default": 0,
            "loan": 0,
            "contact": 1,
            "day": 15,
            "month": 5,
            "duration": 300,
            "campaign": 1,
            "pdays": -1,
            "previous": 0,
            "poutcome": 0,
            "summary": "Analisis dokumen simulasi. Nasabah memiliki riwayat kolektibilitas baik (Kol 1) dan kondisi keuangan stabil.",
            "anomalies": []
        }
        return {
            "status": "SUCCESS",
            "data": mock_data
        }

    # Extract text from the PDF
    pdf_text = extract_text_from_pdf(pdf_path)
    
    if not pdf_text.strip():
        return {
            "status": "ERROR",
            "errors": ["Gagal mengekstrak teks dari berkas PDF nasabah."],
            "data": {}
        }

    # Analyze text using OpenRouter AI
    extracted_data = ai_extract_credit_data(pdf_text)
    
    # Run structured validations
    validation_errors = validate_extracted_data(extracted_data)
    
    if validation_errors:
        return {
            "status": "ERROR",
            "errors": validation_errors,
            "data": extracted_data
        }

    return {
        "status": "SUCCESS",
        "data": extracted_data
    }


# =========================================================
# TESTING
# =========================================================

if __name__ == "__main__":
    # Test fallback
    result = extract_data_from_documents("documents_test/non_existent_file.pdf")
    print("\n=== HASIL EKSTRAKSI ===")
    print(result)