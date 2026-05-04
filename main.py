from fastapi import FastAPI, HTTPException
import joblib
import pandas as pd
import numpy as np
from pydantic import BaseModel

app = FastAPI(title="BNI Credit Scoring System")

# Inisialisasi variabel 
model = None
scaler = None
feature_columns = [
    'age', 'job', 'marital', 'education', 'default', 'balance', 
    'housing', 'loan', 'contact', 'day', 'month', 'duration', 
    'campaign', 'pdays', 'previous', 'poutcome'
]

# Muat model dan scaler saat startup
try:
    model = joblib.load('rf_model_bni.pkl')
    scaler = joblib.load('scaler_bni.pkl')
    print("✅ Model dan Scaler berhasil dimuat.")
except Exception as e:
    print(f"❌ FATAL ERROR: Gagal memuat file pkl: {e}")

class CreditInput(BaseModel):
    age: int
    job: int
    marital: int
    education: int
    default: int
    balance: int
    housing: int
    loan: int
    contact: int
    day: int
    month: int
    duration: int
    campaign: int
    pdays: int
    previous: int
    poutcome: int

@app.post("/predict")
async def predict_credit(data: CreditInput):
    # Cek apakah model/scaler tersedia sebelum memproses
    if model is None or scaler is None:
        raise HTTPException(status_code=503, detail="Model Machine Learning belum siap di server.")

    try:
        input_df = pd.DataFrame([data.dict()])
        
        # Scaling data sesuai standar saat training
        input_scaled = scaler.transform(input_df)
        
        # Prediksi Probabilitas & Hitung Score 0-1000
        probability = model.predict_proba(input_scaled)[0][1]
        credit_score = int(probability * 1000)
        
        # Penentuan Kategori Risiko BNI
        if credit_score >= 700:
            kategori, rekomendasi = "Rendah", "Layak Kredit"
        elif 400 <= credit_score < 700:
            kategori, rekomendasi = "Menengah", "Perlu Pertimbangan"
        else:
            kategori, rekomendasi = "Tinggi", "Tidak Layak Kredit"
            
        # Logika Alasan (Feature Importance)
        importances = model.feature_importances_
        indices = np.argsort(importances)[-3:][::-1]
        top_features = [feature_columns[i] for i in indices]
        
        return {
            "credit_score": credit_score,
            "kategori_risiko": kategori,
            "rekomendasi": rekomendasi,
            "analisis_fitur": f"Skor dipengaruhi oleh: {', '.join(top_features)}."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Terjadi kesalahan saat pemrosesan: {str(e)}")