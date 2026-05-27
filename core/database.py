
from sqlalchemy import create_engine, Column, Integer, String, Float, JSON, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from .config import settings

# Setup SQLAlchemy
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="staff") # manager, staff

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
    screening_file = Column(String, nullable=True)  # Tambahan: path file screening doc di Supabase
    ai_summary = Column(String, nullable=True)  # Tambahan: ringkasan dossier oleh AI
    detected_anomalies = Column(JSON, nullable=True)  # Tambahan: kelemahan/kejanggalan dokumen
    approval = Column(String, default="PENDING")  # Tambahan: approval status (PENDING / APPROVED / REJECTED)
    approved_by = Column(String, nullable=True)  # Tambahan: nama manager yang melakukan approval
    created_at = Column(DateTime, default=datetime.utcnow)

# Engine & Session
# Pastikan DATABASE_URL di config.py sudah benar
engine = None
SessionLocal = None

if settings.DATABASE_URL:
    try:
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    except Exception as e:
        print(f"Database engine creation failed: {e}")

def init_db():
    """Membuat tabel jika belum ada di PostgreSQL."""
    if not engine:
        raise Exception("Database engine is not initialized. Please verify your DATABASE_URL environment variable.")

    try:
        # Check database connectivity first
        with engine.connect() as connection:
            pass
        print("Database: Connected to PostgreSQL/Supabase successfully.")
        
        Base.metadata.create_all(bind=engine)
        print("Database initialized (tables created).")
        
        # Ensure newer columns exist (automatic self-healing migration)
        from sqlalchemy import text
        with engine.connect() as conn:
            try:
                if engine.dialect.name == "postgresql":
                    # Migrate users table
                    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR UNIQUE;"))
                    
                    # Migrate credit_applications table
                    conn.execute(text("ALTER TABLE credit_applications ADD COLUMN IF NOT EXISTS nama_hasil_analisis VARCHAR;"))
                    conn.execute(text("ALTER TABLE credit_applications ADD COLUMN IF NOT EXISTS file_pdf VARCHAR;"))
                    conn.execute(text("ALTER TABLE credit_applications ADD COLUMN IF NOT EXISTS screening_file VARCHAR;"))
                    conn.execute(text("ALTER TABLE credit_applications ADD COLUMN IF NOT EXISTS ai_summary TEXT;"))
                    conn.execute(text("ALTER TABLE credit_applications ADD COLUMN IF NOT EXISTS detected_anomalies JSON;"))
                    conn.execute(text("ALTER TABLE credit_applications ADD COLUMN IF NOT EXISTS approval VARCHAR DEFAULT 'PENDING';"))
                    conn.execute(text("ALTER TABLE credit_applications ADD COLUMN IF NOT EXISTS approved_by VARCHAR;"))
                    
                    conn.commit()
                    print("Database: PostgreSQL tables checked and auto-migrated successfully.")
            except Exception as e_alter:
                print(f"Database migration warning: {e_alter}")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        raise e

def save_application_record(data: dict):
    """
    Simpan riwayat pengajuan ke database PostgreSQL secara nyata.
    """
    if not SessionLocal:
        print("Database error: SessionLocal is not initialized. Cannot save record.")
        return False
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
            screening_file=data.get("screening_file"),
            ai_summary=data.get("ai_summary"),
            detected_anomalies=data.get("detected_anomalies"),
            approval=data.get("approval", "PENDING"),
            approved_by=data.get("approved_by")
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
