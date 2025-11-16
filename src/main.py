from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import hashlib
import json
import os
import sys
from pathlib import Path
import jwt
from datetime import datetime, timedelta
from functools import wraps
from contextlib import contextmanager
from io import BytesIO

from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey, or_
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, scoped_session

from nltk.tokenize import sent_tokenize, word_tokenize

# Add components to path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from components.module1_document_ingestion import extract_text
from components.module2_text_preprocessing import preprocess_contract_text
from components.module3_clause_detection import detect_clause_type, ensure_model_loaded
from components.module5_language_simplification import simplify_text, ensure_simplifier_loaded
from components.module4_legal_terms import extract_legal_terms
from components.readability_metrics import (
    calculate_all_metrics,
    generate_clause_type_chart,
    generate_stats_chart,
    count_syllables,
)

# Flask app setup
app = Flask(__name__)
CORS(app, supports_credentials=True)
app.config['SECRET_KEY'] = 'clauseease-secret-key-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Paths
ROOT = CURRENT_DIR.parent
USERS_FILE = ROOT / 'data' / 'users.json'

DB_PATH = ROOT / 'data' / 'clauseease.db'
DB_PATH.parent.mkdir(exist_ok=True)

engine = create_engine(f'sqlite:///{DB_PATH}', connect_args={'check_same_thread': False}, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True))
Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(150), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    documents = relationship('Document', back_populates='user', cascade='all, delete-orphan')
    glossary_entries = relationship('Glossary', back_populates='creator', cascade='all, delete-orphan')


class Document(Base):
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    document_title = Column(String(255), nullable=False)
    original_text = Column(Text, nullable=False)
    simplified_text_basic = Column(Text)
    simplified_text_intermediate = Column(Text)
    simplified_text_advanced = Column(Text)
    original_readability_score = Column(Float)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    report_json = Column(Text)
    stats_json = Column(Text)
    clause_count = Column(Integer, default=0)
    word_count = Column(Integer, default=0)

    user = relationship('User', back_populates='documents')


class Glossary(Base):
    __tablename__ = 'glossary'

    id = Column(Integer, primary_key=True)
    term = Column(String(255), nullable=False, unique=True)
    simplified_explanation = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))

    creator = relationship('User', back_populates='glossary_entries')


@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_legacy_users():
    if not USERS_FILE.exists():
        return

    try:
        with USERS_FILE.open('r') as f:
            legacy_users = json.load(f)
    except Exception:
        return

    with get_db() as db:
        for email, payload in legacy_users.items():
            username = payload.get('username')
            password_hash = payload.get('password')
            created_at_raw = payload.get('created_at')

            if not email or not username or not password_hash:
                continue

            exists = db.query(User).filter(or_(User.email == email, User.username == username)).first()
            if exists:
                continue

            created_at = None
            if created_at_raw:
                try:
                    created_at = datetime.fromisoformat(created_at_raw)
                except ValueError:
                    created_at = datetime.utcnow()

            user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                created_at=created_at or datetime.utcnow()
            )
            db.add(user)
        db.commit()


def init_db():
    Base.metadata.create_all(bind=engine)
    migrate_legacy_users()


def calculate_reading_ease(text):
    if not text or not text.strip():
        return 0.0

    try:
        sentences = sent_tokenize(text)
        words = [word for word in word_tokenize(text) if word.isalpha()]

        if len(sentences) == 0 or len(words) == 0:
            return 0.0

        syllable_count = sum(count_syllables(word) for word in words)
        words_per_sentence = len(words) / max(len(sentences), 1)
        syllables_per_word = syllable_count / max(len(words), 1)
        score = 206.835 - (1.015 * words_per_sentence) - (84.6 * syllables_per_word)
        return round(max(min(score, 100.0), 0.0), 2)
    except Exception:
        return 0.0


def get_user_by_email(db, email):
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db, username):
    return db.query(User).filter(User.username == username).first()


def store_document_record(username, filename, raw_text, simplified_texts, results, original_metrics, simplified_metrics):
    combined_simplified = " ".join(simplified_texts) if simplified_texts else ''
    readability_score = calculate_reading_ease(raw_text)

    stats_payload = {
        'original_metrics': original_metrics,
        'simplified_metrics': simplified_metrics,
        'clause_type_summary': results.get('clause_type_summary', {}),
        'legal_terms_count': len(results.get('legal_terms', [])),
    }

    report_payload = dict(results)
    report_payload.pop('clause_type_chart', None)
    report_payload.pop('stats_chart', None)

    with get_db() as db:
        user = get_user_by_username(db, username)
        if not user:
            raise ValueError('User not found for document storage')

        document = Document(
            user_id=user.id,
            document_title=filename,
            original_text=raw_text,
            simplified_text_basic=combined_simplified,
            original_readability_score=readability_score,
            report_json=json.dumps(report_payload),
            stats_json=json.dumps(stats_payload),
            clause_count=results.get('clause_count', 0),
            word_count=results.get('word_count', 0)
        )

        db.add(document)
        db.commit()
        db.refresh(document)
        return document


def load_document_history(user_id):
    with get_db() as db:
        docs = (
            db.query(Document)
            .filter(Document.user_id == user_id)
            .order_by(Document.uploaded_at.desc())
            .all()
        )

        history = []
        for doc in docs:
            stats_payload = json.loads(doc.stats_json) if doc.stats_json else {}
            history.append({
                'id': doc.id,
                'document_title': doc.document_title,
                'uploaded_at': doc.uploaded_at.isoformat(),
                'original_readability_score': doc.original_readability_score,
                'clause_count': doc.clause_count,
                'word_count': doc.word_count,
                'simplified_word_count': stats_payload.get('simplified_metrics', {}).get('word_count', 0),
            })

        return history


def build_document_report(document):
    report_payload = json.loads(document.report_json) if document.report_json else {}
    stats_payload = json.loads(document.stats_json) if document.stats_json else {}

    if not report_payload:
        report_payload = {
            'filename': document.document_title,
            'raw_text': document.original_text or '',
            'clauses': [],
            'legal_terms': [],
            'clause_count': document.clause_count or 0,
            'word_count': document.word_count or 0,
            'original_readability': stats_payload.get('original_metrics', {}),
            'simplified_readability': stats_payload.get('simplified_metrics', {}),
            'clause_type_summary': stats_payload.get('clause_type_summary', {}),
        }

    if 'filename' not in report_payload:
        report_payload['filename'] = document.document_title

    if 'original_readability' not in report_payload:
        report_payload['original_readability'] = stats_payload.get('original_metrics', {})

    if 'simplified_readability' not in report_payload:
        report_payload['simplified_readability'] = stats_payload.get('simplified_metrics', {})

    if 'clause_type_summary' not in report_payload:
        report_payload['clause_type_summary'] = stats_payload.get('clause_type_summary', {})

    if 'clause_type_chart' not in report_payload:
        report_payload['clause_type_chart'] = generate_clause_type_chart(report_payload.get('clause_type_summary', {}))

    if 'stats_chart' not in report_payload:
        report_payload['stats_chart'] = generate_stats_chart(
            report_payload.get('original_readability', {}),
            report_payload.get('simplified_readability', {})
        )

    report_payload['document_id'] = document.id
    return report_payload


init_db()


@app.teardown_appcontext
def remove_session(exception=None):
    SessionLocal.remove()

# Helper functions
def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def _extract_token_from_request():
    """Pull JWT from headers, cookies, query params, or payload."""
    auth_header = request.headers.get('Authorization', '').strip()
    if auth_header:
        if auth_header.lower().startswith('bearer '):
            return auth_header[7:].strip()
        return auth_header

    for header_name in ('X-Access-Token', 'x-access-token'):
        candidate = request.headers.get(header_name)
        if candidate:
            return candidate.strip()

    for cookie_name in ('token', 'Authorization', 'authorization'):
        candidate = request.cookies.get(cookie_name)
        if candidate:
            return candidate.strip().removeprefix('Bearer ').strip()

    candidate = request.args.get('token')
    if candidate:
        return candidate.strip()

    candidate = request.form.get('token') if request.form else None
    if candidate:
        return candidate.strip()

    json_payload = request.get_json(silent=True) or {}
    candidate = json_payload.get('token') if isinstance(json_payload, dict) else None
    if candidate:
        return str(candidate).strip()

    return None


def token_required(f):
    """Decorator to protect routes with JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'OPTIONS':
            return '', 204
        token = _extract_token_from_request()

        print(f"\n🔐 TOKEN CHECK")
        print(f"Token present: {bool(token)}")

        if not token:
            print("❌ Token missing")
            return jsonify({'message': 'Token is missing'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = {
                'username': data.get('username'),
                'email': data.get('email'),
                'user_id': data.get('user_id')
            }
            print(f"✅ Token valid for user: {current_user['username']}\n")
        except Exception as e:
            print(f"❌ Token invalid: {str(e)}\n")
            return jsonify({'message': 'Token is invalid'}), 401

        return f(current_user, *args, **kwargs)

    return decorated

# Flask API Routes
@app.route('/api/register', methods=['POST', 'OPTIONS'])
def register():
    """Register a new user"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        print(f"[REGISTER] Received data: {data}")  # Debug logging
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not username or not email or not password:
            return jsonify({'message': 'All fields are required'}), 400
        
        if len(username) < 3:
            return jsonify({'message': 'Username must be at least 3 characters'}), 400
        
        if len(password) < 6:
            return jsonify({'message': 'Password must be at least 6 characters'}), 400
        
        with get_db() as db:
            existing_user = db.query(User).filter(or_(User.email == email, User.username == username)).first()
            if existing_user:
                if existing_user.email == email:
                    return jsonify({'message': 'Email already registered'}), 400
                return jsonify({'message': 'Username already taken'}), 400

            user = User(
                username=username,
                email=email,
                password_hash=hash_password(password)
            )
            db.add(user)
            db.commit()

        print(f"[REGISTER] User {username} registered successfully")  # Debug logging
        return jsonify({
            'message': 'Registration successful',
            'username': username
        }), 201
        
    except Exception as e:
        print(f"[REGISTER ERROR] {str(e)}")  # Debug logging
        return jsonify({'message': f'Server error: {str(e)}'}), 500

@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    """Login user and return JWT token"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        print(f"[LOGIN] Email: {email}, Password entered: {password}")  # Debug
        
        if not email or not password:
            return jsonify({'message': 'Email and password required'}), 400
        
        with get_db() as db:
            user = get_user_by_email(db, email)

            if not user:
                print(f"[LOGIN ERROR] Email {email} not found in database")  # Debug
                return jsonify({'message': 'Invalid credentials'}), 401

            input_hash = hash_password(password)
            stored_hash = user.password_hash

            print(f"[LOGIN DEBUG] Input hash: {input_hash}")  # Debug
            print(f"[LOGIN DEBUG] Stored hash: {stored_hash}")  # Debug
            print(f"[LOGIN DEBUG] Match: {input_hash == stored_hash}")  # Debug

            if stored_hash != input_hash:
                print(f"[LOGIN ERROR] Password mismatch for {email}")  # Debug
                return jsonify({'message': 'Invalid credentials'}), 401

            user_id = user.id
            username = user.username

        token = jwt.encode({
            'user_id': user_id,
            'username': username,
            'email': email,
            'exp': datetime.utcnow() + timedelta(days=1)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        print(f"[LOGIN] User {username} logged in successfully")  # Debug
        response = jsonify({
            'message': 'Login successful',
            'token': token,
            'username': username
        })
        max_age_seconds = 24 * 60 * 60
        response.set_cookie(
            'token',
            token,
            max_age=max_age_seconds,
            httponly=True,
            secure=False,
            samesite='Lax'
        )
        response.set_cookie(
            'Authorization',
            f'Bearer {token}',
            max_age=max_age_seconds,
            httponly=True,
            secure=False,
            samesite='Lax'
        )
        return response, 200
        
    except Exception as e:
        print(f"[LOGIN ERROR] {str(e)}")  # Debug
        return jsonify({'message': f'Server error: {str(e)}'}), 500

@app.route('/api/process', methods=['POST', 'OPTIONS'])
@token_required
def process_document(current_user):
    """Process uploaded document through all 5 modules"""
    if request.method == 'OPTIONS':
        return '', 204
    print(f"\n{'='*60}")
    print(f"📥 PROCESSING REQUEST RECEIVED")
    user_name = current_user.get('username') if isinstance(current_user, dict) else str(current_user)
    print(f"User: {user_name}")
    print(f"Files in request: {list(request.files.keys())}")
    print(f"{'='*60}\n")
    step = 'initial'
    if 'file' not in request.files:
        print("❌ ERROR: No file in request.files")
        return jsonify({'message': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        print("❌ ERROR: Empty filename")
        return jsonify({'message': 'No file selected'}), 400
    
    print(f"✅ File received: {file.filename}")
    
    temp_dir = ROOT / 'temp_uploads'
    temp_dir.mkdir(exist_ok=True)
    
    temp_path = temp_dir / file.filename
    file.save(str(temp_path))
    
    try:
        step = 'save_upload'
        # Module 1: Document Ingestion
        step = 'extract_text'
        raw_text = extract_text(str(temp_path))
        
        if raw_text.startswith('[ERROR]'):
            return jsonify({'message': raw_text}), 400
        
        # Module 2: Text Preprocessing
        step = 'preprocess_contract_text'
        clauses = preprocess_contract_text(raw_text)
        
        # Calculate readability metrics for original text
        step = 'calculate_original_metrics'
        original_metrics = calculate_all_metrics(raw_text)
        
        # Module 3: Clause Detection
        step = 'detect_clause_type'
        clause_types = []
        for clause in clauses:
            clause_type = detect_clause_type(clause['cleaned_text'])
            clause_types.append(clause_type)
        
        # Module 4: Legal Terms Extraction
        step = 'extract_legal_terms'
        legal_terms = extract_legal_terms(raw_text)
        
        # Module 5: Language Simplification
        step = 'simplify_text'
        simplified_texts = []
        for clause in clauses:
            simplified = simplify_text(clause['cleaned_text'])
            simplified_texts.append(simplified)
        
        # Combine all simplified text
        step = 'simplified_metrics'
        combined_simplified = " ".join(simplified_texts)
        simplified_metrics = calculate_all_metrics(combined_simplified)
        
        # Save session
        step = 'save_session'
        # Prepare results
        step = 'prepare_response'
        results = {
            'filename': file.filename,
            'raw_text': raw_text,
            'word_count': len(raw_text.split()),
            'clause_count': len(clauses),
            'original_readability': original_metrics,
            'simplified_readability': simplified_metrics,
            'clauses': [
                {
                    'index': i + 1,
                    'raw_text': c['raw_text'],
                    'cleaned_text': c['cleaned_text'],
                    'sentences': c['sentences'],
                    'entities': c['entities'],
                    'type': clause_types[i],
                    'simplified': simplified_texts[i]
                }
                for i, c in enumerate(clauses)
            ],
            'legal_terms': [
                {
                    'term': t['term'] if isinstance(t, dict) else t[0],
                    'category': t.get('category') if isinstance(t, dict) else (t[1] if len(t) > 1 else ''),
                    'definition': t.get('definition') if isinstance(t, dict) else (t[2] if len(t) > 2 else None)
                }
                for t in legal_terms
            ],
            'clause_type_summary': {}
        }
        
        from collections import Counter
        type_counts = Counter(clause_types)
        results['clause_type_summary'] = dict(type_counts)
        
        document_record = store_document_record(user_name, file.filename, raw_text, simplified_texts, results, original_metrics, simplified_metrics)
        results['document_id'] = document_record.id
        
        # Generate charts using matplotlib/seaborn
        step = 'generate_charts'
        results['clause_type_chart'] = generate_clause_type_chart(results['clause_type_summary'])
        results['stats_chart'] = generate_stats_chart(original_metrics, simplified_metrics)
        
        return jsonify(results), 200
        
    except Exception as e:
        import traceback
        error_message = f"Processing error at {step}: {str(e)}"
        print(error_message)
        print(traceback.format_exc())
        return jsonify({'message': error_message}), 500
    
    finally:
        if temp_path.exists():
            temp_path.unlink()

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'ClauseEase API is running'}), 200


@app.route('/api/history', methods=['GET'])
@token_required
def get_history(current_user):
    username = current_user.get('username') if isinstance(current_user, dict) else None
    if not username:
        return jsonify({'history': []}), 200

    with get_db() as db:
        user = get_user_by_username(db, username)
        if not user:
            return jsonify({'history': []}), 200
        user_id = user.id

    history = load_document_history(user_id)
    return jsonify({'history': history}), 200


@app.route('/api/history/<int:document_id>', methods=['GET'])
@token_required
def get_document(current_user, document_id):
    username = current_user.get('username') if isinstance(current_user, dict) else None
    if not username:
        return jsonify({'message': 'Unauthorized'}), 401

    with get_db() as db:
        user = get_user_by_username(db, username)
        if not user:
            return jsonify({'message': 'Unauthorized'}), 401

        document = db.query(Document).filter(Document.id == document_id, Document.user_id == user.id).first()
        if not document:
            return jsonify({'message': 'Document not found'}), 404

    report_payload = build_document_report(document)
    return jsonify({'document': report_payload}), 200


@app.route('/api/history/<int:document_id>/download', methods=['GET'])
@token_required
def download_document(current_user, document_id):
    username = current_user.get('username') if isinstance(current_user, dict) else None
    if not username:
        return jsonify({'message': 'Unauthorized'}), 401

    with get_db() as db:
        user = get_user_by_username(db, username)
        if not user:
            return jsonify({'message': 'Unauthorized'}), 401

        document = db.query(Document).filter(Document.id == document_id, Document.user_id == user.id).first()
        if not document:
            return jsonify({'message': 'Document not found'}), 404

    report_payload = build_document_report(document)
    buffer = BytesIO()
    buffer.write(json.dumps(report_payload, indent=2).encode('utf-8'))
    buffer.seek(0)
    safe_filename = document.document_title or f'document-{document.id}.txt'
    if not safe_filename.lower().endswith('.json'):
        safe_filename = f"{Path(safe_filename).stem or 'contract'}-report.json"

    return send_file(
        buffer,
        mimetype='application/json',
        as_attachment=True,
        download_name=safe_filename
    )

if __name__ == '__main__':
    print("\n" + "="*80)
    print("CLAUSEEASE AI - CONTRACT LANGUAGE SIMPLIFIER")
    print("="*80)
    print("Starting Flask API Server...")
    print("API available at: http://localhost:5000")
    print("Frontend should connect to: http://localhost:5000/api")
    print("="*80 + "\n")
    
    # Load models on startup
    ensure_model_loaded()
    ensure_simplifier_loaded()
    
    app.run(debug=False, port=5000, host='0.0.0.0', use_reloader=False)