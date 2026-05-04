import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from imblearn.over_sampling import SMOTE
import joblib

# Load Dataset
df = pd.read_csv('data/bank_cleaned.csv')

# Encoding Kolom Kategorikal
# Mengubah teks menjadi angka agar bisa diproses model
le = LabelEncoder()
categorical_cols = ['job', 'marital', 'education', 'default', 'housing', 'loan', 'contact', 'month', 'poutcome']

for col in categorical_cols:
    df[col] = le.fit_transform(df[col])

# Mengubah menjadi biner (1: Layak, 0: Tidak Layak)
df['y'] = df['y'].map({'yes': 1, 'no': 0})

# Pemisahan Fitur dan Target
X = df.drop('y', axis=1)
y = df['y']

# Handling Imbalanced Data dengan SMOTE
# Menyeimbangkan jumlah data nasabah lancar dan macet
smote = SMOTE(random_state=42)
X_resampled, y_resampled = smote.fit_resample(X, y)

# Split Data & Scaling
X_train, X_test, y_train, y_test = train_test_split(X_resampled, y_resampled, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Training Random Forest
# Menggunakan Random Forest karena akurasinya tinggi dan robust terhadap overfitting
rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
rf_model.fit(X_train_scaled, y_train)

# Konversi ke Credit Score (0-1000)
def generate_credit_score(model, input_data_scaled):
    
    prob = model.predict_proba(input_data_scaled)[:, 1]
    # Konversi ke skala 0-1000[cite: 1]
    return (prob * 1000).astype(int)

# 8. Simpan Model untuk FastAPI[cite: 1]
joblib.dump(rf_model, 'data/rf_model_bni.pkl')
joblib.dump(scaler, 'data/scaler_bni.pkl')

print("Model Random Forest berhasil dilatih dan disimpan!")