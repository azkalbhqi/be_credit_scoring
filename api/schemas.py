from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class CreditInput(BaseModel):
    full_name: str # Nama Lengkap Nasabah
    # Fitur-fitur Random Forest
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
    

class CreditResponse(BaseModel):
    status: str
    credit_score: Optional[int] = None
    kategori_risiko: Optional[str] = None
    analisis: Optional[Dict[str, str]] = None
    narasi_rag: Optional[str] = None
    action_plan: Optional[str] = None
    full_name: Optional[str] = None
    message: Optional[str] = None
    nama_hasil_analisis: Optional[str] = None
    file_pdf: Optional[str] = None
    ai_summary: Optional[str] = None
    detected_anomalies: Optional[List[str]] = None

class RulesTestInput(BaseModel):
    kolektibilitas_bi: int
    produk: str
    lama_usaha_bulan: int
    dsr: float
    gaji: float

class RagTestInput(BaseModel):
    credit_score: int
    kategori_risiko: str
    analisis: Dict[str, str]

class ReportTestInput(BaseModel):
    full_name: str
    credit_score: int
    kategori_risiko: str
    analisis: Dict[str, str]
    narasi_rag: str
    action_plan: str
    ai_summary: Optional[str] = None
    detected_anomalies: Optional[List[str]] = None
