
import pandas as pd
import os
import joblib
import numpy as np

model = None
scaler = None
# 16 Fitur asli yang diharapkan oleh model BNI
feature_columns = [
    'age', 'job', 'marital', 'education', 'default', 'balance', 
    'housing', 'loan', 'contact', 'day', 'month', 'duration', 
    'campaign', 'pdays', 'previous', 'poutcome'
]

def load_models():
    """Memuat model dari folder models/."""
    global model, scaler
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(base_dir, 'models', 'rf_model_bni.pkl')
        scaler_path = os.path.join(base_dir, 'models', 'scaler_bni.pkl')
        
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        print(" Model dan Scaler berhasil dimuat di step3_scoring.py")
    except Exception as e:
        print(f" Gagal memuat file pkl di step3_scoring.py: {e}")

def run_ml_scoring(input_dict: dict) -> tuple[int, str, dict]:
    """
    Langkah 3: Eksekusi Lapisan 2 (Refinement Scoring)
    """
    if model is None or scaler is None:
        load_models() # Coba muat jika belum ada
        if model is None:
            raise Exception("Model Machine Learning belum siap.")
        
    
    model_input_list = []
    for col in feature_columns:
        model_input_list.append(input_dict.get(col, 0))
    
    input_df = pd.DataFrame([model_input_list], columns=feature_columns)
    input_scaled = scaler.transform(input_df)
    
    # Hitung Skor
    probability = model.predict_proba(input_scaled)[0][1]
    credit_score = int(probability * 1000)
    
    # feature importance 
    importances = model.feature_importances_
    indices = np.argsort(importances)[-5:][::-1] 
    
    detail_analisis = {}
    for i in indices:
        feature_name = feature_columns[i]
        user_value = model_input_list[i]
        avg_value = scaler.mean_[i] 
        
        negative_features = ['default', 'loan', 'housing']
        if feature_name in negative_features:
            status = "Good" if user_value == 0 else "Bad"
        else:
            status = "Good" if user_value >= avg_value else "Bad"
        
        detail_analisis[feature_name] = status

    if credit_score >= 700:
        kategori = "LOW RISK"
    elif 400 <= credit_score < 700:
        kategori = "MEDIUM RISK"
    else:
        kategori = "HIGH RISK"

    return credit_score, kategori, detail_analisis
