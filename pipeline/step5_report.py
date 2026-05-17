from fpdf import FPDF
import os
from datetime import datetime

class CreditReport(FPDF):
    def header(self):
        # Header Laporan BNI
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'LAPORAN CREDIT SCORING BNI', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, f'Dibuat pada: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Halaman {self.page_no()}', 0, 0, 'C')

def generate_pdf_report(data: dict) -> str:
    """
    Langkah 5: Generate PDF Report (Laporan Bahasa Indonesia)
    Mengembalikan path ke file PDF yang berhasil dibuat.
    """
    pdf = CreditReport()
    pdf.add_page()
    
    # 1. Informasi Pribadi
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, '1. Informasi Pribadi', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(50, 10, 'Nama Lengkap:', 0, 0)
    pdf.cell(0, 10, str(data.get('full_name', 'Tidak Tersedia')), 0, 1)
    pdf.ln(5)

    # 2. Analisis Credit Scoring
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, '2. Analisis Credit Scoring', 0, 1)
    pdf.set_font('Arial', '', 10)
    
    score = data.get('credit_score', 0)
    category = data.get('kategori_risiko', 'Tidak Tersedia')
    
    # Penerjemahan kategori risiko agar seragam dalam Bahasa Indonesia
    category_translations = {
        "LOW RISK": "RISIKO RENDAH",
        "MEDIUM RISK": "RISIKO MENENGAH",
        "HIGH RISK": "RISIKO TINGGI",
        "LOW": "RENDAH",
        "MEDIUM": "MENENGAH",
        "HIGH": "TINGGI",
        "RENDAH": "RENDAH",
        "MENENGAH": "MENENGAH",
        "TINGGI": "TINGGI"
    }
    category_upper = category.upper()
    display_category = category_translations.get(category_upper, category_upper)
    
    # Pewarnaan teks berdasarkan tingkat risiko
    if "RENDAH" in display_category or "LOW" in category_upper:
        pdf.set_text_color(0, 128, 0)      # Hijau untuk risiko rendah
    elif "MENENGAH" in display_category or "MEDIUM" in category_upper:
        pdf.set_text_color(255, 165, 0)    # Oranye untuk risiko menengah
    else:
        pdf.set_text_color(255, 0, 0)      # Merah untuk risiko tinggi
        
    pdf.cell(50, 10, 'Skor Kredit:', 0, 0)
    pdf.cell(0, 10, f'{score} / 1000', 0, 1)
    pdf.cell(50, 10, 'Kategori Risiko:', 0, 0)
    pdf.cell(0, 10, display_category, 0, 1)
    
    pdf.set_text_color(0, 0, 0) # Reset kembali ke hitam
    pdf.ln(5)

    # 3. Indikator Kunci (Baik / Buruk)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, '3. Indikator Kunci (Baik / Buruk)', 0, 1)
    pdf.set_font('Arial', '', 10)
    
    # Kamus penerjemahan nama fitur ke Bahasa Indonesia
    feature_translations = {
        "age": "Umur",
        "gaji": "Gaji Bulanan",
        "cicilan": "Cicilan Bulanan",
        "balance": "Rata-rata Saldo Rekening",
        "kolektibilitas_bi": "Kolektibilitas BI",
        "lama_usaha_bulan": "Lama Usaha (Bulan)",
        "dsr": "Debt Service Ratio (DSR)",
        "housing": "Kepemilikan Rumah",
        "job": "Jenis Pekerjaan",
        "marital": "Status Pernikahan",
        "education": "Tingkat Pendidikan",
        "default": "Tunggakan Kredit (Default)",
        "loan": "Pinjaman Pribadi Aktif",
        "contact": "Metode Kontak",
        "day": "Hari Terakhir Dihubungi",
        "month": "Bulan Terakhir Dihubungi",
        "duration": "Durasi Kontak (Detik)",
        "campaign": "Jumlah Kontak Kampanye",
        "pdays": "Hari Sejak Kontak Sebelumnya",
        "previous": "Jumlah Kontak Sebelumnya",
        "poutcome": "Hasil Kampanye Sebelumnya"
    }

    analisis = data.get('analisis', {})
    for feature, status in analisis.items():
        translated_feature = feature_translations.get(feature.lower(), feature.capitalize())
        pdf.cell(60, 8, f'{translated_feature}:', 0, 0)
        
        # Penerjemahan status Good / Bad -> Baik / Buruk
        if status.lower() == "good":
            pdf.set_text_color(0, 128, 0) # Hijau
            display_status = "Baik"
        else:
            pdf.set_text_color(255, 0, 0) # Merah
            display_status = "Buruk"
            
        pdf.cell(0, 8, display_status, 0, 1)
        pdf.set_text_color(0, 0, 0) # Reset ke hitam
    pdf.ln(5)

    # 4. Penalaran Kontekstual & Rekomendasi AI
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, '4. Penalaran Kontekstual & Rekomendasi AI (RAG)', 0, 1)
    pdf.set_font('Arial', '', 10)
    
    # Ringkasan Analisis (RAG)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 8, 'Ringkasan Analisis:', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 8, str(data.get('narasi_rag', 'Narasi AI tidak tersedia.')), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    
    # Rencana Tindakan untuk Analis
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 8, 'Rencana Tindakan (Action Plan) untuk Analis:', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 8, str(data.get('action_plan', 'Rencana tindakan tidak tersedia.')), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # 5. Ringkasan Dossier AI & Deteksi Anomali
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, '5. Ringkasan Dossier AI & Deteksi Anomali', 0, 1)
    pdf.set_font('Arial', '', 10)
    
    # Analisis Dossier
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 8, 'Ringkasan Analisis Dossier Nasabah:', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 8, str(data.get('summary', 'Ringkasan dossier tidak tersedia.')), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    
    # Deteksi Anomali / Bendera Merah
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 8, 'Deteksi Anomali / Temuan Kejanggalan (Red Flags):', 0, 1)
    pdf.set_font('Arial', '', 10)
    
    anomalies = data.get('anomalies', [])
    if anomalies:
        pdf.set_text_color(255, 0, 0) # Merah untuk anomali
        for anomaly in anomalies:
            pdf.multi_cell(0, 8, f'- {anomaly}', new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0) # Reset ke hitam
    else:
        pdf.set_text_color(0, 128, 0) # Hijau untuk indikator bersih
        pdf.cell(0, 8, 'Tidak ada anomali atau kontradiksi dokumen yang terdeteksi. Verifikasi dokumen lolos.', 0, 1)
        pdf.set_text_color(0, 0, 0) # Reset ke hitam
    
    # Menyimpan file PDF laporan
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
        
    filename = f"Report_{data.get('full_name', 'Nasabah').replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    filepath = os.path.join(reports_dir, filename)
    pdf.output(filepath)
    
    return filepath
