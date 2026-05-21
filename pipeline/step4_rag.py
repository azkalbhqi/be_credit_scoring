import os
import requests
import json
from pypdf import PdfReader
from core.config import settings

def get_bni_policy_context(produk: str) -> str:
    """
    Mengambil kebijakan resmi dari folder pipeline/rag_knowledge berdasarkan nama produk (KUR / KTA).
    Mendukung file .txt dan .pdf secara dinamis.
    """
    knowledge_dir = os.path.join("pipeline", "rag_knowledge")
    if not os.path.exists(knowledge_dir):
        return "Ketentuan BNI: KUR membutuhkan survei lapangan (On-The-Spot) & DSR max 40%. KTA membutuhkan konfirmasi kepegawaian HRD & DSR max 35%."
        
    context = ""
    produk_lower = produk.lower()
    
    try:
        for filename in os.listdir(knowledge_dir):
            filepath = os.path.join(knowledge_dir, filename)
            if filename.endswith(".txt"):
                with open(filepath, "r", encoding="utf-8") as f:
                    text = f.read()
                    # filter
                    sections = text.split("------------------------------------------------------------------------")
                    for section in sections:
                        if produk_lower in section.lower() or "prosedur deteksi" in section.lower():
                            context += section + "\n"
            elif filename.endswith(".pdf"):
                reader = PdfReader(filepath)
                for page in reader.pages:
                    text = page.extract_text()
                    if produk_lower in text.lower() or "deteksi" in text.lower():
                        context += text + "\n"
    except Exception as e:
        print(f"Peringatan: Gagal membaca pengetahuan RAG: {e}")
        
    if not context.strip():
        return "Gunakan ketentuan standar kredit BNI: Lakukan verifikasi identitas, verifikasi pendapatan (DSR), dan survei lapangan jika risiko menengah/tinggi."
        
    return context.strip()[:3500] # Batasi panjang teks agar optimal untuk LLM

def generate_action_plan(credit_score: int, kategori: str, analisis: dict, produk: str = "KUR") -> tuple[str, str]:
    """
    Langkah 4: Eksekusi Lapisan 3 (Contextual Reasoning - RAG)
    Mengambil dokumen kebijakan perbankan yang relevan dan menyisipkannya ke prompt Gemini API.
    """
    print(f"Mengambil dokumen kebijakan BNI untuk produk {produk.upper()}...")
    policy_context = get_bni_policy_context(produk)
    
    print("Mengirim data nasabah + regulasi RAG ke Gemini API...")
    
    prompt = f"""
    Anda adalah seorang analis kredit senior di Bank Negara Indonesia (BNI).
    Tugas Anda adalah mengevaluasi pengajuan kredit nasabah dengan mematuhi Dokumen Kebijakan Resmi BNI di bawah ini secara ketat.
    
    === DOKUMEN KEBIJAKAN RESMI BNI (RAG CONTEXT) ===
    {policy_context}
    ================================================
    
    Hasil Evaluasi Nasabah Saat Ini:
    - Nama Produk Kredit: BNI {produk.upper()}
    - Credit Score: {credit_score}
    - Kategori Risiko: {kategori}
    - Analisis Fitur (Good/Bad): {json.dumps(analisis)}
    
    Tugas Anda:
    1. Buatkan narasi singkat (maksimal 3 kalimat) dalam Bahasa Indonesia yang menjelaskan alasan utama nasabah mendapatkan skor tersebut berdasarkan Analisis Fitur dan kecocokannya dengan Kebijakan BNI.
    2. Berikan "Action Plan" yang konkret (maksimal 3 kalimat) dalam Bahasa Indonesia untuk tim analis kredit di lapangan mengenai apa yang harus diperiksa atau dilakukan selanjutnya sesuai dengan tindakan wajib yang tertulis di Kebijakan BNI (seperti wajib survei lapangan OTS, wawancara tetangga, konfirmasi telepon HRD, atau penanganan Red Flags jika terdeteksi).
    
    Format balasan Anda HARUS HANYA JSON dengan struktur seperti ini (tanpa markdown atau teks tambahan apapun):
    {{
        "narasi": "isi narasi 1 paragraf",
        "action_plan": "isi action plan 1 paragraf"
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
        content = result['candidates'][0]['content']['parts'][0]['text']
        
        # Bersihkan markdown backticks dari output string (jika LLM menambahkannya)
        content_cleaned = content.strip()
        if content_cleaned.startswith("```json"):
            content_cleaned = content_cleaned[7:]
        elif content_cleaned.startswith("```"):
            content_cleaned = content_cleaned[3:]
        if content_cleaned.endswith("```"):
            content_cleaned = content_cleaned[:-3]
            
        try:
            parsed_content = json.loads(content_cleaned)
            narasi = parsed_content.get("narasi", "Gagal parsing narasi dari LLM.")
            action_plan = parsed_content.get("action_plan", "Gagal parsing action plan dari LLM.")
        except json.JSONDecodeError:
            print(f"Warning: Output dari LLM bukan JSON murni. Raw output: {content}")
            narasi = f"Nasabah mendapatkan skor {credit_score} (Risiko {kategori})."
            action_plan = content 
            
        return narasi, action_plan
        
    except Exception as e:
        print(f"Error calling Gemini RAG API: {e}")
        # fallback
        narasi = f"Nasabah mendapatkan skor {credit_score} (Risiko {kategori}). Analisis menunjukkan fitur utama yang berpengaruh: {analisis}."
        kategori_lower = kategori.lower()
        if "rendah" in kategori_lower or "low" in kategori_lower:
            if "kta" in produk.lower():
                action_plan = "Setujui kredit Fleksi. Lakukan konfirmasi telepon ke HRD perusahaan tempat bekerja untuk memverifikasi status kepegawaian aktif."
            elif "komersial" in produk.lower():
                action_plan = "Setujui kredit Komersial. Lakukan verifikasi fisik dokumen legalitas bisnis (SIUP/NIB, NPWP) dan keaslian agunan."
            else:
                action_plan = "Setujui kredit KUR. Lakukan verifikasi standar (SLIK dan KTP). Pastikan dokumen asli sesuai dengan yang diunggah."
        elif "menengah" in kategori_lower or "medium" in kategori_lower:
            if "kta" in produk.lower():
                action_plan = "Lakukan verifikasi fisik ke kantor tempat bekerja dan BPJS Ketenagakerjaan nasabah untuk memvalidasi lama bekerja."
            elif "komersial" in produk.lower():
                action_plan = "Tunda keputusan. Wajib kunjungan lapangan On-The-Spot (OTS) ke tempat usaha, cek stok barang, dan wawancara distributor utama."
            else:
                action_plan = "Tunda keputusan. Wajib survei lapangan On-The-Spot ke tempat usaha dan lakukan wawancara dengan minimal 2 tetangga sekitar lokasi usaha."
        else:
            action_plan = "Tolak kredit. Risiko terlalu tinggi berdasarkan profil historis. Minta nasabah memperbaiki kolektibilitas atau memperbesar agunan."
            
        return narasi, action_plan
