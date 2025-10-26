"""
Migration script to import users from JSON to SQLite database
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from werkzeug.security import generate_password_hash

# Add parent directory to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'src'))

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

# Define User model here to avoid importing from app.py
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(150), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Database setup
DB_PATH = ROOT / 'data' / 'clauseease.db'
engine = create_engine(f'sqlite:///{DB_PATH}', connect_args={'check_same_thread': False})
Session = sessionmaker(bind=engine)

def migrate_users():
    """Migrate users from users.json to SQLite database"""
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Read JSON file
    users_file = ROOT / 'data' / 'users.json'
    with open(users_file, 'r') as f:
        users_data = json.load(f)
    
    session = Session()
    
    try:
        migrated_count = 0
        skipped_count = 0
        
        for email, user_info in users_data.items():
            # Check if user already exists
            existing_user = session.query(User).filter(User.email == email).first()
            
            if existing_user:
                print(f"⏭️  Skipping {email} - already exists in database")
                skipped_count += 1
                continue
            
            # Create new user with password "123456" (since we can't reverse old hashes)
            # Users can change their password later or we set a known default
            new_user = User(
                username=user_info['username'],
                email=email,
                password_hash=generate_password_hash('123456'),  # Default password
                created_at=datetime.fromisoformat(user_info['created_at'].replace('Z', '+00:00')) if 'created_at' in user_info else datetime.utcnow()
            )
            
            session.add(new_user)
            print(f"✅ Migrated {email} (username: {user_info['username']}) - password set to: 123456")
            migrated_count += 1
        
        session.commit()
        
        print(f"\n🎉 Migration Complete!")
        print(f"   ✅ Migrated: {migrated_count} users")
        print(f"   ⏭️  Skipped: {skipped_count} users (already existed)")
        print(f"\n📝 Note: All migrated users have password set to '123456'")
        print(f"   Users can login with their email and password '123456'")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error during migration: {e}")
        raise
    finally:
        session.close()

if __name__ == '__main__':
    print("🔄 Starting user migration from JSON to SQLite...\n")
    migrate_users()
