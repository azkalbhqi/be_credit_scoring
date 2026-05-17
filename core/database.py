# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine, Column, Integer, String, Float, JSON, DateTime
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from .config import settings

# Setup SQLAlchemy
Base = declarative_base()

class CreditApplication(Base):
    __tablename__ = "credit_applications"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=True) # Nama Lengkap
    status = Column(String)  # APPROVE / REJECT / REVIEW
    credit_score = Column(Integer, nullable=True)
    kategori_risiko = Column(String, nullable=True)
    analisis = Column(JSON, nullable=True)  # Menyimpan detail Good/Bad
    narasi_rag = Column(String, nullable=True)
    action_plan = Column(String, nullable=True)
    message = Column(String, nullable=True)
    nama_hasil_analisis = Column(String, nullable=True)  # Tambahan: nama hasil analisis
    file_pdf = Column(String, nullable=True)  # Tambahan: nama file pdf
    ai_summary = Column(String, nullable=True)  # Tambahan: ringkasan dossier oleh AI
    detected_anomalies = Column(JSON, nullable=True)  # Tambahan: kelemahan/kejanggalan dokumen
    created_at = Column(DateTime, default=datetime.utcnow)

# Engine & Session
# Pastikan DATABASE_URL di config.py sudah benar
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Membuat tabel jika belum ada di PostgreSQL."""
    try:
        Base.metadata.create_all(bind=engine)
        print("Database initialized (tables created).")
    except Exception as e:
        print(f"Database initialization failed: {e}")

def save_application_record(data: dict):
    """
    Simpan riwayat pengajuan ke database PostgreSQL secara nyata.
    """
    db = SessionLocal()
    try:
        new_record = CreditApplication(
            full_name=data.get("full_name"),
            status=data.get("status"),
            credit_score=data.get("credit_score"),
            kategori_risiko=data.get("kategori_risiko"),
            analisis=data.get("analisis"),
            narasi_rag=data.get("narasi_rag"),
            action_plan=data.get("action_plan"),
            message=data.get("message"),
            nama_hasil_analisis=data.get("nama_hasil_analisis"),
            file_pdf=data.get("file_pdf"),
            ai_summary=data.get("ai_summary"),
            detected_anomalies=data.get("detected_anomalies")
        )
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        print(f"Data saved to DB (ID: {new_record.id})")
        return True
    except Exception as e:
        db.rollback()
        print(f"Failed to save to DB: {e}")
        return False
    finally:
        db.close()
