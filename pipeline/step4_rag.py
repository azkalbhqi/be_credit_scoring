import requests
import json
from core.config import settings

def generate_action_plan(credit_score: int, kategori: str, analisis: dict) -> tuple[str, str]:
    """
    Langkah 4: Eksekusi Lapisan 3 (Contextual Reasoning - RAG)
    Menggunakan Gemini API (gemini-3.1-flash-lite).
    """
    print("Mengirim data ke Gemini API untuk mendapatkan rekomendasi RAG...")
    
    prompt = f"""
    Anda adalah seorang analis kredit senior di BNI. 
    Seorang nasabah baru saja dievaluasi dengan hasil berikut:
    - Credit Score: {credit_score}
    - Kategori Risiko: {kategori}
    - Analisis Fitur (Good/Bad): {json.dumps(analisis)}
    
    Tugas Anda:
    1. Buatkan narasi singkat (maksimal 3 kalimat) yang menjelaskan alasan utama nasabah mendapatkan skor tersebut berdasarkan Analisis Fitur.
    2. Berikan "Action Plan" yang konkret (maksimal 3 kalimat) untuk tim analis kredit di lapangan mengenai apa yang harus diperiksa atau dilakukan selanjutnya (misalnya: verifikasi dokumen, cek lapangan, dsb).
    
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
            action_plan = content # Jadikan seluruh respons sebagai action plan
            
        return narasi, action_plan
        
    except Exception as e:
        print(f"Error calling OpenRouter API: {e}")
        # Fallback manual jika API error
        narasi = f"Nasabah mendapatkan skor {credit_score} (Risiko {kategori}). Analisis menunjukkan fitur utama yang berpengaruh: {analisis}."
        kategori_lower = kategori.lower()
        if "rendah" in kategori_lower or "low" in kategori_lower:
            action_plan = "Setujui kredit. Lakukan verifikasi standar (SLIK dan KTP). Pastikan dokumen asli sesuai dengan yang diunggah."
        elif "menengah" in kategori_lower or "medium" in kategori_lower:
            action_plan = "Tunda keputusan. Lakukan verifikasi pola transaksi via PACE dan audit karakter 5C secara mendalam melalui kunjungan lapangan."
        else:
            action_plan = "Tolak kredit. Risiko terlalu tinggi berdasarkan profil historis. Minta nasabah memperbaiki kolektibilitas atau memperbesar agunan."
            
        return narasi, action_plan
