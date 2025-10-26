"""
Script to reset a user's password in the database
"""
import sys
from pathlib import Path
from werkzeug.security import generate_password_hash

# Add parent directory to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'src'))

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

# Define User model
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

def reset_password(email, new_password):
    """Reset password for a specific user"""
    session = Session()
    
    try:
        user = session.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"❌ User with email '{email}' not found")
            return False
        
        # Update password
        user.password_hash = generate_password_hash(new_password)
        session.commit()
        
        print(f"✅ Password updated successfully for {email}")
        print(f"   Username: {user.username}")
        print(f"   New Password: {new_password}")
        return True
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error updating password: {e}")
        return False
    finally:
        session.close()

def reset_all_passwords(password='123456'):
    """Reset all user passwords to a default password"""
    session = Session()
    
    try:
        users = session.query(User).all()
        count = 0
        
        for user in users:
            user.password_hash = generate_password_hash(password)
            print(f"✅ Updated password for {user.email} (username: {user.username})")
            count += 1
        
        session.commit()
        print(f"\n🎉 Successfully updated passwords for {count} users")
        print(f"   All users can now login with password: {password}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
    finally:
        session.close()

if __name__ == '__main__':
    print("🔄 Resetting all user passwords to '123456'...\n")
    reset_all_passwords('123456')
