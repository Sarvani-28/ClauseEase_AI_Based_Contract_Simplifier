import os
import json
import logging
import traceback
import io
import base64
import re
from pathlib import Path
from datetime import datetime
import pytz
from contextlib import contextmanager
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import fitz
from docx import Document as DocxDocument
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter

from flask import Flask, request, jsonify, session, make_response, render_template, redirect, url_for, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey, or_
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, scoped_session

from nltk.tokenize import sent_tokenize, word_tokenize
import syllables

# Project paths
ROOT = Path(__file__).parent.parent
USERS_FILE = ROOT / 'data' / 'users.json'
SESSIONS_FILE = ROOT / 'data' / 'sessions.json'
UPLOAD_FOLDER = ROOT / 'temp_uploads'
UPLOAD_FOLDER.mkdir(exist_ok=True)

# Add components to path
import sys
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# Import custom modules
from components.module1_document_ingestion import extract_text
from components.module2_text_preprocessing import clean_text, preprocess_contract_text
from components.module3_clause_detection import detect_clause_type, ensure_model_loaded
from components.module4_legal_terms import extract_legal_terms
from components.module5_language_simplification import simplify_text
from components.readability_metrics import calculate_all_metrics

# Database configuration
DB_PATH = ROOT / 'data' / 'clauseease.db'
DB_PATH.parent.mkdir(exist_ok=True)

engine = create_engine(f'sqlite:///{DB_PATH}', connect_args={'check_same_thread': False}, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True))
Base = declarative_base()

# User model
class User(Base, UserMixin):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(150), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Kolkata')))

    documents = relationship('Document', back_populates='user', cascade='all, delete-orphan')
    glossary_entries = relationship('Glossary', back_populates='creator', cascade='all, delete-orphan')

# Document model
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
    uploaded_at = Column(DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Kolkata')))
    report_json = Column(Text)
    stats_json = Column(Text)
    clause_count = Column(Integer, default=0)
    word_count = Column(Integer, default=0)

    user = relationship('User', back_populates='documents')

# Glossary model
class Glossary(Base):
    __tablename__ = 'glossary'

    id = Column(Integer, primary_key=True)
    term = Column(String(255), nullable=False, unique=True)
    simplified_explanation = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Kolkata')))
    created_by = Column(Integer, ForeignKey('users.id'))

    creator = relationship('User', back_populates='glossary_entries')

# Login form
class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', 
                                   validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Create Account')

# Database helper functions
@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)

def count_syllables(word):
    return syllables.estimate(word)

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

# Generate base64 charts
def generate_chart_base64(chart_type, data, title):
    """Create chart as base64"""
    plt.figure(figsize=(10, 7))
    plt.style.use('seaborn-v0_8-whitegrid')
    
    if chart_type == 'pie':
        labels = list(data.keys())
        sizes = list(data.values())
        colors = ['#3b82f6', '#f59e0b', '#10b981', '#8b5cf6', '#ef4444', '#06b6d4', '#ec4899', '#14b8a6']
        
        # Simple 2D design
        wedges, texts, autotexts = plt.pie(
            sizes, 
            labels=labels, 
            autopct='%1.1f%%', 
            colors=colors[:len(labels)],
            startangle=90,
            textprops={'fontsize': 12, 'weight': 'bold', 'color': '#1e293b'}
        )
        
        # Style percentages
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(13)
            autotext.set_weight('bold')
        
        plt.title(title, fontsize=16, fontweight='bold', color='#1e293b', pad=25)
        plt.axis('equal')
        
    elif chart_type == 'bar':
        categories = list(data.keys())
        original_values = [v[0] if isinstance(v, list) else v for v in data.values()]
        simplified_values = [v[1] if isinstance(v, list) and len(v) > 1 else v * 0.7 for v in data.values()]
        
        x = range(len(categories))
        width = 0.38
        
        fig, ax = plt.subplots(figsize=(10, 7))
        
        # Create comparison bars
        bars1 = ax.bar([i - width/2 for i in x], original_values, width, 
                       label='Original', color='#3b82f6', edgecolor='#1e40af', linewidth=2)
        bars2 = ax.bar([i + width/2 for i in x], simplified_values, width,
                       label='Simplified', color='#10b981', edgecolor='#059669', linewidth=2)
        
        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}',
                       ha='center', va='bottom', fontweight='bold', fontsize=10)
        
        ax.set_xlabel('Metrics', fontsize=13, fontweight='bold', color='#1e293b', labelpad=10)
        ax.set_ylabel('Values', fontsize=13, fontweight='bold', color='#1e293b', labelpad=10)
        ax.set_title(title, fontsize=16, fontweight='bold', color='#1e293b', pad=25)
        ax.set_xticks(x)
        ax.set_xticklabels(categories, rotation=0, ha='center', fontsize=11, fontweight='600')
        ax.legend(fontsize=11, loc='upper right', framealpha=0.95, edgecolor='#cbd5e1')
        ax.grid(True, alpha=0.2, linestyle='--', linewidth=0.5)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        plt.tight_layout()
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight', facecolor='white', edgecolor='none')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close()
    
    return f"data:image/png;base64,{image_base64}"

# Flask app configuration
app = Flask(__name__, 
            template_folder=str(ROOT / 'templates'),
            static_folder=str(ROOT / 'static'))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = None  # No expiration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user:
            db.expunge(user)  # Detach from session
        return user
    finally:
        db.close()

# Routes
@app.route('/')
def index():
    """Welcome page route"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        return render_template('welcome.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard landing page"""
    return render_template('landing.html')

# Auth blueprint setup
from flask import Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    form = LoginForm()
    if form.validate_on_submit():
        with get_db() as db:
            # Find user by email
            user = db.query(User).filter(User.email == form.email.data).first()
            if user and check_password_hash(user.password_hash, form.password.data):
                login_user(user)
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
            flash('Invalid email or password')
    return render_template('login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    form = RegisterForm()
    if form.validate_on_submit():
        with get_db() as db:
            # Check existing user
            existing_user = db.query(User).filter(
                or_(User.email == form.email.data, User.username == form.username.data)
            ).first()
            
            if existing_user:
                if existing_user.email == form.email.data:
                    flash('Email already registered')
                else:
                    flash('Username already taken')
                return render_template('register.html', form=form)
            
            # Create new user
            user = User(
                username=form.username.data,
                email=form.email.data,
                password_hash=generate_password_hash(form.password.data)
            )
            db.add(user)
            db.commit()
            flash('Registration successful! Please Login to proceed.')
            return redirect(url_for('auth.login'))
    
    return render_template('register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout route"""
    logout_user()
    return redirect(url_for('auth.login'))

app.register_blueprint(auth_bp)

from admin_routes import admin_bp, configure_admin

configure_admin(get_db, User, Document)
app.register_blueprint(admin_bp)

@app.route('/process', methods=['POST'])
@login_required
def process_document():
    """Process uploaded document with multi-level simplification"""
    try:
        # Get uploaded file
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('No file selected')
            return redirect(url_for('dashboard'))

        filename = secure_filename(file.filename)
        if not filename.lower().endswith(('.pdf', '.docx', '.txt')):
            flash('Invalid file type. Please upload PDF, DOCX, or TXT files only.')
            return redirect(url_for('dashboard'))
        
        # Get simplification level
        simplification_level = request.form.get('simplification_level', 'basic')
        if simplification_level not in ['basic', 'intermediate', 'advanced']:
            simplification_level = 'basic'

        # Save temp file
        file_path = UPLOAD_FOLDER / filename
        file.save(str(file_path))

        # Extract document text
        raw_text = extract_text(str(file_path))
        if not raw_text or not raw_text.strip():
            flash('Could not extract text from the file')
            return redirect(url_for('dashboard'))

        # Clean and preprocess
        processed_text = clean_text(raw_text)
        processed_clauses = preprocess_contract_text(raw_text)
        
        # Process each clause
        clauses = []
        for idx, clause_data in enumerate(processed_clauses):
            clause_type = detect_clause_type(clause_data['cleaned_text'])
            simplified = simplify_text(clause_data['cleaned_text'], level=simplification_level)
            
            clauses.append({
                'index': idx + 1,
                'raw_text': clause_data['raw_text'],
                'cleaned_text': clause_data['cleaned_text'],
                'sentences': clause_data['sentences'],
                'entities': clause_data['entities'],
                'type': clause_type,
                'simplified': simplified
            })
        
        # Extract legal terms
        legal_terms = extract_legal_terms(processed_text)
        simplified_text = simplify_text(processed_text, level=simplification_level)
        
        # Calculate readability metrics
        original_metrics = calculate_all_metrics(raw_text)
        simplified_metrics = calculate_all_metrics(simplified_text)
        
        # Generate clause chart
        clause_types = Counter([c['type'] for c in clauses])
        clause_chart = generate_chart_base64('pie', clause_types, 'Clause Types Distribution')
        
        # Calculate text statistics
        original_words = len(raw_text.split())
        simplified_words = len(simplified_text.split()) if simplified_text and simplified_text.strip() else int(original_words * 0.7)
        
        from nltk.tokenize import sent_tokenize
        original_sentences = len(sent_tokenize(raw_text))
        simplified_sentences = len(sent_tokenize(simplified_text)) if simplified_text and simplified_text.strip() else int(original_sentences * 0.7)
        
        stats_data = {
            'Word Count': [original_words, simplified_words],
            'Sentence Count': [original_sentences, simplified_sentences],
            'Avg Words/Sentence': [round(original_words / max(original_sentences, 1), 1), 
                                   round(simplified_words / max(simplified_sentences, 1), 1)],
            'Complex Words': [sum(1 for word in raw_text.split() if len(word) > 8),
                            sum(1 for word in simplified_text.split() if len(word) > 8) if simplified_text and simplified_text.strip() else 0]
        }
        stats_chart = generate_chart_base64('bar', stats_data, 'Text Statistics Comparison')
        
        # Highlight legal terms
        highlighted_text = raw_text
        if legal_terms:
            for term in legal_terms:
                if isinstance(term, dict) and 'term' in term:
                    term_word = term['term']
                    term_definition = term.get('simplified_explanation', term.get('definition', 'Legal term'))
                    
                    # Escape HTML quotes
                    term_definition = term_definition.replace('"', '&quot;').replace("'", '&#39;')
                    
                    # Preserve original case
                    def replace_func(match):
                        return f'<span class="highlight-legal" title="{term_definition}">{match.group(0)}</span>'
                    
                    # Apply highlighting
                    pattern = re.compile(r'\b' + re.escape(term_word) + r'\b', re.IGNORECASE)
                    highlighted_text = pattern.sub(replace_func, highlighted_text)
        
        # Package results
        results = {
            'clauses': clauses,
            'legal_terms': legal_terms,
            'simplified_text': simplified_text,
            'original_metrics': original_metrics,
            'simplified_metrics': simplified_metrics,
            'clause_type_chart': clause_chart,
            'stats_chart': stats_chart,
            'highlighted_text': highlighted_text,
            'simplification_level': simplification_level,
            'original_sentences': original_sentences,
            'simplified_sentences': simplified_sentences
        }
        
        # Save to database with level-specific field
        with get_db() as db:
            # Prepare level-specific storage
            level_fields = {
                'simplified_text_basic': None,
                'simplified_text_intermediate': None,
                'simplified_text_advanced': None
            }
            level_fields[f'simplified_text_{simplification_level}'] = simplified_text
            
            document = Document(
                user_id=current_user.id,
                document_title=filename,
                original_text=raw_text,
                **level_fields,
                original_readability_score=calculate_reading_ease(raw_text),
                report_json=json.dumps(results),
                clause_count=len(clauses),
                word_count=len(raw_text.split())
            )
            db.add(document)
            db.commit()
            db.refresh(document)
            document_id = document.id
            
        # Remove temp file
        if file_path.exists():
            file_path.unlink()
        
        return redirect(url_for('view_document', document_id=document_id))

    except Exception as e:
        logging.error(f"Processing error: {str(e)}")
        flash('An error occurred during processing')
        return redirect(url_for('dashboard'))

@app.route('/document/<int:document_id>')
@login_required
def view_document(document_id):
    """Display single document results"""
    with get_db() as db:
        # Query user's document
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        
        if not document:
            flash('Document not found')
            return redirect(url_for('history'))
        
        # Load report JSON
        results = json.loads(document.report_json) if document.report_json else {}
        
        if 'original_sentences' not in results and document.original_text:
            from nltk.tokenize import sent_tokenize
            results['original_sentences'] = len(sent_tokenize(document.original_text))
        
        if 'simplified_sentences' not in results:
            simplified_text = results.get('simplified_text') or document.simplified_text_basic
            if simplified_text:
                from nltk.tokenize import sent_tokenize
                results['simplified_sentences'] = len(sent_tokenize(simplified_text))
            else:
                results['simplified_sentences'] = 0
        
        doc_data = {
            'id': document.id,
            'document_title': document.document_title,
            'original_text': document.original_text,
            'simplified_text_basic': document.simplified_text_basic,
            'original_readability_score': document.original_readability_score,
            'uploaded_at': document.uploaded_at,
            'clause_count': document.clause_count,
            'word_count': document.word_count
        }
        
    return render_template('results.html', document=doc_data, results=results)

@app.route('/history')
@login_required
def history():
    """Show user document history"""
    with get_db() as db:
        # Get all user documents
        documents = db.query(Document).filter(
            Document.user_id == current_user.id
        ).order_by(Document.uploaded_at.desc()).all()
        
        # Convert to dict
        docs_data = [{
            'id': doc.id,
            'document_title': doc.document_title,
            'uploaded_at': doc.uploaded_at,
            'clause_count': doc.clause_count,
            'word_count': doc.word_count,
            'original_readability_score': doc.original_readability_score
        } for doc in documents]
        
    return render_template('history.html', documents=docs_data)

@app.route('/download/<int:document_id>')
@login_required
def download_report(document_id):
    """Export document report JSON"""
    with get_db() as db:
        # Query user's document
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        
        if not document:
            flash('Document not found')
            return redirect(url_for('history'))
        
        # Prepare report data
        report_data = {
            'document_title': document.document_title,
            'processed_at': document.uploaded_at.isoformat(),
            'original_text': document.original_text,
            'simplified_text': document.simplified_text_basic,
            'readability_score': document.original_readability_score,
            'results': json.loads(document.report_json) if document.report_json else {}
        }
        doc_title = document.document_title
    
    # Create JSON response
    response = make_response(json.dumps(report_data, indent=2))
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = f'attachment; filename={doc_title}_report.json'
    return response

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for Docker"""
    return jsonify({'status': 'ok', 'message': 'ClauseEase is running'}), 200

if __name__ == '__main__':
    init_db()
    ensure_model_loaded()
    app.run(debug=True, host='0.0.0.0', port=5000)