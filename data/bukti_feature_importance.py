import pandas as pd
import numpy as np
import os
import joblib
import matplotlib.pyplot as plt

def main():
    # 1. Tentukan path file secara dinamis
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(current_dir)
    data_path = os.path.join(current_dir, 'bank_cleaned.csv')
    
    # Lokasi model (mencari di folder models/ atau di folder yang sama)
    model_paths_to_try = [
        os.path.join(base_dir, 'models', 'rf_model_bni.pkl'),
        os.path.join(current_dir, 'rf_model_bni.pkl')
    ]
    scaler_paths_to_try = [
        os.path.join(base_dir, 'models', 'scaler_bni.pkl'),
        os.path.join(current_dir, 'scaler_bni.pkl')
    ]
    
    model_path = None
    scaler_path = None
    
    for path in model_paths_to_try:
        if os.path.exists(path):
            model_path = path
            break
            
    for path in scaler_paths_to_try:
        if os.path.exists(path):
            scaler_path = path
            break

    print("=" * 60)
    print("    TES BUKTI KUANTITATIF FEATURE IMPORTANCE - BNI CREDIT AI")
    print("=" * 60)
    
    if not model_path or not scaler_path:
        print("[ERROR] File model pkl atau scaler pkl tidak ditemukan!")
        print("Pastikan rf_model_bni.pkl dan scaler_bni.pkl ada di folder models/ atau data/.")
        return
        
    print(f"[OK] Model loaded from  : {model_path}")
    print(f"[OK] Scaler loaded from : {scaler_path}")
    print(f"[OK] Dataset loaded from: {data_path}")

    # 2. Muat model dan scaler
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    # 3. Muat dataset bank_cleaned.csv
    if not os.path.exists(data_path):
        print(f"[ERROR] File dataset {data_path} tidak ditemukan!")
        return
        
    df = pd.read_csv(data_path)
    print(f"[OK] Jumlah Data : {df.shape[0]} baris nasabah.")
    print(f"[OK] Jumlah Kolom: {df.shape[1]} fitur.")

    # 4. PERBAIKAN: Hardcoded Mapping Dictionary (Menggantikan LabelEncoder baru)
    # Aturan ini disesuaikan dengan urutan alfabetis dataset bank marketing asli agar sinkron dengan model
    mapping_rules = {
        'default': {'no': 0, 'yes': 1},
        'housing': {'no': 0, 'yes': 1},
        'loan': {'no': 0, 'yes': 1},
        'marital': {'divorced': 0, 'married': 1, 'single': 2},
        'education': {'primary': 0, 'secondary': 1, 'tertiary': 2, 'unknown': 3},
        'contact': {'cellular': 0, 'telephone': 1, 'unknown': 2},
        'poutcome': {'failure': 0, 'other': 1, 'success': 2, 'unknown': 3},
        'month': {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 
                  'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12},
        'job': {'admin.': 0, 'blue-collar': 1, 'entrepreneur': 2, 'housemaid': 3, 
                'management': 4, 'retired': 5, 'self-employed': 6, 'services': 7, 
                'student': 8, 'technician': 9, 'unemployed': 10, 'unknown': 11}
    }

    categorical_cols = ['job', 'marital', 'education', 'default', 'housing', 'loan', 'contact', 'month', 'poutcome']
    
    # Lakukan mapping string-to-numeric yang aman
    for col in categorical_cols:
        if col in df.columns:
            df[col] = df[col].map(mapping_rules[col]).fillna(0).astype(int)

    # 16 Fitur BNI Credit Scoring asli
    feature_columns = [
        'age', 'job', 'marital', 'education', 'default', 'balance', 
        'housing', 'loan', 'contact', 'day', 'month', 'duration', 
        'campaign', 'pdays', 'previous', 'poutcome'
    ]
    
    # 5. Validasi kecocokan fitur
    X = df[feature_columns]

    # 6. Ekstrak kontribusi fitur (Feature Importance) dari Random Forest Classifier
    importances = model.feature_importances_
    
    # Buat Series & urutkan dari terkecil ke terbesar untuk plotting horizontal
    forest_importances = pd.Series(importances, index=feature_columns)
    forest_importances_sorted_plot = forest_importances.sort_values(ascending=True)

    # 7. Desain Visualisasi Chart (Putih & BNI Orange)
    plt.figure(figsize=(11, 7), dpi=300)
    
    # Set background putih bersih
    plt.gca().set_facecolor('#ffffff') 
    
    # Atur skema warna: Top 5 diberi warna BNI Orange (#f97316), sisanya Slate Gray lembut (#cbd5e1)
    colors = ['#cbd5e1'] * (len(forest_importances_sorted_plot) - 5) + ['#f97316'] * 5
    
    # Render Bar Horizontal
    bars = plt.barh(
        forest_importances_sorted_plot.index, 
        forest_importances_sorted_plot.values, 
        color=colors, 
        edgecolor='none', 
        height=0.6
    )

    # Tambahkan garis grid x tipis untuk membantu pembacaan kuantitatif
    plt.grid(axis='x', linestyle='--', alpha=0.3, color='#94a3b8')

    # Title & Label Styling
    plt.title(
        'Bukti Kuantitatif Feature Importance\nModel AI Classifier Klasifikasi Risiko Kredit BNI', 
        fontsize=13, 
        fontweight='bold', 
        pad=22, 
        color='#0f172a'
    )
    plt.xlabel('Tingkat Kontribusi Fitur (Importance Value)', fontsize=10, fontweight='bold', labelpad=12, color='#334155')
    plt.ylabel('16 Variabel Masukan Model', fontsize=10, fontweight='bold', labelpad=12, color='#334155')

    # Berikan label persentase teks di setiap ujung bar
    for bar in bars:
        width = bar.get_width()
        val_percent = f"{width * 100:.2f}%"
        
        # Cek apakah warna bar adalah BNI Orange (RGB tuple)
        # Warna #f97316 dikonversi ke skala 0-1 mendekati nilai (0.976, 0.450, 0.086)
        face_color = bar.get_facecolor()
        is_orange = face_color[0] > 0.9 and face_color[1] < 0.5
        
        text_color = '#ea580c' if is_orange else '#64748b'
        font_weight = 'bold' if is_orange else 'medium'
        
        plt.text(
            width + 0.003, 
            bar.get_y() + bar.get_height()/2, 
            val_percent, 
            va='center', 
            ha='left', 
            fontsize=8.5, 
            fontweight=font_weight, 
            color=text_color
        )

    # Atur layout agar margins tidak terpotong
    plt.tight_layout()

    # Simpan hasil grafik PNG ke folder yang aktif
    output_png = os.path.join(current_dir, 'bukti_feature_importance.png')
    plt.savefig(output_png, facecolor='white', bbox_inches='tight')
    plt.close()
    
    print("[OK] Grafik Feature Importance berhasil dibuat!")
    print(f"[PATH] DISIMPAN DI: {output_png}")

    # 8. Cetak Laporan Detail ke Console
    print("\n" + "=" * 60)
    print("      DETAIL TINGKAT KONTRIBUSI FITUR (TERURUT TERTINGGI)")
    print("=" * 60)
    sorted_importances_print = forest_importances.sort_values(ascending=False)
    for rank, (feat_name, val) in enumerate(sorted_importances_print.items(), 1):
        top_tag = "* [TOP 5 FITUR UTAMA]" if rank <= 5 else "    "
        print(f" {rank:2d}. {feat_name:<12} : {val*100:6.2f}%   {top_tag}")
    print("=" * 60)
    print("Interpretasi: Variabel dengan persentase tinggi memiliki pengaruh paling")
    print("dominan dalam menentukan apakah nasabah layak disetujui (Approved)")
    print("atau ditolak (Rejected) dalam proses scoring acak Random Forest.")
    print("=" * 60 + "\n")

if __name__ == '__main__':
    main()