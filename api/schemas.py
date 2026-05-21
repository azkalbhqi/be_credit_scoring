from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str = "staff" # staff, manager

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

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
    id: Optional[int] = None
    created_at: Optional[datetime] = None
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
    screening_file: Optional[str] = None
    ai_summary: Optional[str] = None
    detected_anomalies: Optional[List[str]] = None
    approval: Optional[str] = "PENDING"
    approved_by: Optional[str] = None

    class Config:
        from_attributes = True

class RulesTestInput(BaseModel):
    kolektibilitas_bi: int
    produk: str
    lama_usaha_bulan: int
    dsr: float
    gaji: float
    balance: Optional[float] = 0.0

class RagTestInput(BaseModel):
    credit_score: int
    kategori_risiko: str
    analisis: Dict[str, str]
    produk: Optional[str] = "KUR"

class ReportTestInput(BaseModel):
    full_name: str
    credit_score: int
    kategori_risiko: str
    analisis: Dict[str, str]
    narasi_rag: str
    action_plan: str
    ai_summary: Optional[str] = None
    detected_anomalies: Optional[List[str]] = None
