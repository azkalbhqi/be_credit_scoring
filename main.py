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
    print(f" Gagal memuat file pkl: {e}")

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
    if model is None or scaler is None:
        raise HTTPException(status_code=503, detail="Model Machine Learning belum siap.")

    try:
        input_dict = data.dict()
        input_df = pd.DataFrame([input_dict])
        input_scaled = scaler.transform(input_df)
        
        # 1. Hitung Skor
        probability = model.predict_proba(input_scaled)[0][1]
        credit_score = int(probability * 1000)
        
        # 2. Ambil Fitur Paling Berpengaruh
        importances = model.feature_importances_
        indices = np.argsort(importances)[-3:][::-1] # Ambil 3 teratas
        
        # 3. Logika Analisis Good/Bad
        # Kita bandingkan dengan nilai rata-rata scaler (scaler.mean_)
        detail_analisis = {}
        for i in indices:
            feature_name = feature_columns[i]
            user_value = input_dict[feature_name]
            avg_value = scaler.mean_[i] # Nilai rata-rata dataset training[cite: 1]
            
            # Logika penentuan Good/Bad tergantung jenis fitur[cite: 1]
            # Untuk fitur 'default', 'loan', 'housing', nilai kecil justru 'Good'[cite: 1]
            negative_features = ['default', 'loan', 'housing']
            
            if feature_name in negative_features:
                status = "Good" if user_value == 0 else "Bad"
            else:
                status = "Good" if user_value >= avg_value else "Bad"
            
            detail_analisis[feature_name] = status

        # 4. Penentuan Kategori[cite: 1]
        if credit_score >= 700:
            kategori, rekomendasi = "Rendah", "Layak Kredit"
        elif 400 <= credit_score < 700:
            kategori, rekomendasi = "Menengah", "Perlu Pertimbangan"
        else:
            kategori, rekomendasi = "Tinggi", "Tidak Layak Kredit"

        return {
            "credit_score": credit_score,
            "kategori_risiko": kategori,
            "rekomendasi": rekomendasi,
            "analisis": detail_analisis # Output baru sesuai keinginan Anda[cite: 1]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/metadata")
async def get_metadata():
    if scaler is None:
        raise HTTPException(status_code=503, detail="Scaler belum dimuat.")
    
    thresholds = {}
    
    # Kita iterasi setiap kolom fitur
    for i, col in enumerate(feature_columns):
        avg_value = float(scaler.mean_[i])
        
        # Logika penentuan arah Good/Bad
        negative_features = ['default', 'loan', 'housing']
        
        if col in negative_features:
            # Untuk fitur negatif, 0 adalah Good, >= 1 adalah Bad
            info = {
                "threshold_value": 0,
                "logic": f"Value 0 is Good, >= 1 is Bad",
                "average_in_dataset": avg_value
            }
        else:
            # Untuk fitur positif (seperti balance), >= rata-rata adalah Good
            info = {
                "threshold_value": round(avg_value, 2),
                "logic": f">= {round(avg_value, 2)} is Good, below is Bad",
                "average_in_dataset": avg_value
            }
            
        thresholds[col] = info
        
    return {
        "status": "success",
        "description": "Batas nilai Good/Bad berdasarkan rata-rata dataset training BNI",
        "data": thresholds
    }