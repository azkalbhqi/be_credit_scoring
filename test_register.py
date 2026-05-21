import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import init_db, SessionLocal, User, hash_password
from api.schemas import UserCreate

def test():
    try:
        print("Initializing database...")
        init_db()
        
        db = SessionLocal()
        
        # Test query
        print("Querying users...")
        users = db.query(User).all()
        print(f"Current users in DB: {len(users)}")
        
        # Test insert
        print("Attempting to insert test user...")
        new_user = User(
            username="test_user_777",
            email="test777@gmail.com",
            hashed_password=hash_password("password123"),
            role="staff"
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        print(f"Inserted user: {new_user.username}, ID: {new_user.id}")
        
        # Clean up
        db.delete(new_user)
        db.commit()
        print("Test complete: Insert and delete successful!")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()
