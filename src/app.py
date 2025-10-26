import os
import json
import logging
import traceback
import io
import base64
import re
from pathlib import Path
from datetime import datetime, timedelta, date # Added date
from contextlib import contextmanager
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
from docx import Document as DocxDocument
import matplotlib
matplotlib.use('Agg')  # Non-GUI backend
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter, defaultdict # Added defaultdict
from flask import Blueprint, Flask, render_template, request, redirect, url_for, flash
from flask import Flask, request, jsonify, session, make_response, render_template, redirect, url_for, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length # Removed Email
# --- Added func.strftime ---
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey, or_, Boolean, func, desc
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, scoped_session

# NLTK and Syllables (ensure NLTK data is downloaded: python -m nltk.downloader punkt stopwords)
from nltk.tokenize import sent_tokenize, word_tokenize
# import syllables # Using a simpler fallback syllable counter

# Project paths
ROOT = Path(__file__).parent.parent
USERS_FILE = ROOT / 'data' / 'users.json' # Likely unused if using DB
SESSIONS_FILE = ROOT / 'data' / 'sessions.json' # Likely unused if using DB
UPLOAD_FOLDER = ROOT / 'temp_uploads'
UPLOAD_FOLDER.mkdir(exist_ok=True)

# Import custom components
try:
    from components.module1_document_ingestion import extract_text
    from components.module2_text_preprocessing import clean_text, preprocess_contract_text
    from components.module3_clause_detection import detect_clause_type, ensure_model_loaded
    from components.module4_legal_terms import extract_legal_terms
    from components.module5_language_simplification import simplify_text, ensure_simplifier_loaded
    from components.readability_metrics import calculate_all_metrics
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"[ERROR] Could not import components: {e}. Some features might be disabled.")
    COMPONENTS_AVAILABLE = False
    # Define dummy functions if components are missing to avoid NameErrors
    def extract_text(p): return "Error: Component missing."
    def clean_text(t): return t
    def preprocess_contract_text(t): return [{'raw_text': t, 'cleaned_text': t, 'sentences': [], 'entities': []}]
    def detect_clause_type(t): return "Unknown"
    def ensure_model_loaded(): pass
    def extract_legal_terms(t): return []
    def simplify_text(t): return t if isinstance(t, str) else [text for text in t] # Return input
    def ensure_simplifier_loaded(): pass
    def calculate_all_metrics(t): return {'flesch_reading_ease': 0}


# Database configuration
DB_PATH = ROOT / 'data' / 'clauseease.db'
DB_PATH.parent.mkdir(exist_ok=True)

engine = create_engine(f'sqlite:///{DB_PATH}', connect_args={'check_same_thread': False}, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True))
Base = declarative_base()

# --- Database Models ---
class User(Base, UserMixin):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(150), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_admin = Column(Boolean, nullable=False, default=False, index=True)
    documents = relationship('Document', back_populates='user', cascade='all, delete-orphan')
    glossary_entries = relationship('Glossary', back_populates='creator', cascade='all, delete-orphan')

class Document(Base):
    __tablename__ = 'documents'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    document_title = Column(String(255), nullable=False)
    original_text = Column(Text, nullable=False)
    simplified_text_basic = Column(Text)
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

# --- Forms ---
class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email Address', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Create Account')

# --- Database & Helper Functions ---
@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)

def count_syllables(word):
    # Simple regex-based syllable counter (fallback)
    word = word.lower().strip(".:;?!")
    if not word: return 0
    if len(word) <= 3: return 1
    word = re.sub('(?:[^laeiouy]es|ed|[^laeiouy]e)$', '', word)
    word = re.sub('^y', '', word)
    vowels = 'aeiouy'
    count = 0
    in_vowel_group = False
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not in_vowel_group:
            count += 1
            in_vowel_group = True
        elif not is_vowel:
            in_vowel_group = False
    return count if count > 0 else 1

def calculate_reading_ease(text):
    if not text or not text.strip(): return 0.0
    try:
        sentences = sent_tokenize(text)
        words = [w for w in word_tokenize(text) if w.isalpha()]
        sentence_count = len(sentences)
        word_count = len(words)
        if sentence_count == 0 or word_count == 0: return 0.0
        syllable_count = sum(count_syllables(w) for w in words)
        words_per_sentence = word_count / max(sentence_count, 1)
        syllables_per_word = syllable_count / max(word_count, 1)
        # Flesch Reading Ease formula
        score = 206.835 - (1.015 * words_per_sentence) - (84.6 * syllables_per_word)
        return round(max(0.0, min(100.0, score)), 2)
    except Exception as e:
        print(f"[WARN] Failed calculating reading ease: {e}")
        return 0.0

def generate_chart_base64(chart_type, data, title):
    # Condensed version - keep your full version if needed
    plt.figure(figsize=(10,7)); plt.style.use('seaborn-v0_8-whitegrid');
    try:
        if chart_type=='pie': labels=list(data.keys()); sizes=list(data.values()); colors=['#3b82f6','#f59e0b','#10b981','#8b5cf6','#ef4444','#06b6d4','#ec4899','#14b8a6']; wedges, texts, autotexts = plt.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors[:len(labels)], startangle=90, textprops={'fontsize':12,'weight':'bold','color':'#1e293b'}); [a.set_color('white') or a.set_fontsize(13) or a.set_weight('bold') for a in autotexts]; plt.title(title, fontsize=16, fontweight='bold', color='#1e293b', pad=25); plt.axis('equal');
        elif chart_type=='bar': categories=list(data.keys()); ov=[v[0] if isinstance(v, list) else v for v in data.values()]; sv=[v[1] if isinstance(v,list) and len(v)>1 else v*0.7 for v in data.values()]; x=range(len(categories)); w=0.38; fig,ax=plt.subplots(figsize=(10,7)); b1=ax.bar([i-w/2 for i in x],ov,w,label='Original',color='#3b82f6',edgecolor='#1e40af',linewidth=2); b2=ax.bar([i+w/2 for i in x],sv,w,label='Simplified',color='#10b981',edgecolor='#059669',linewidth=2); [[ax.text(bar.get_x()+bar.get_width()/2.,bar.get_height(),f'{int(bar.get_height())}',ha='center',va='bottom',fontweight='bold',fontsize=10) for bar in bars] for bars in [b1,b2]]; ax.set_xlabel('Metrics',fontsize=13,fontweight='bold',color='#1e293b',labelpad=10); ax.set_ylabel('Values',fontsize=13,fontweight='bold',color='#1e293b',labelpad=10); ax.set_title(title,fontsize=16,fontweight='bold',color='#1e293b',pad=25); ax.set_xticks(x); ax.set_xticklabels(categories,rotation=0,ha='center',fontsize=11,fontweight='600'); ax.legend(fontsize=11,loc='upper right',framealpha=0.95,edgecolor='#cbd5e1'); ax.grid(True,alpha=0.2,linestyle='--',linewidth=0.5); ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False); plt.tight_layout();
        buf=io.BytesIO(); plt.savefig(buf,format='png',dpi=120,bbox_inches='tight',facecolor='white',edgecolor='none'); buf.seek(0); img_b64=base64.b64encode(buf.read()).decode('utf-8');
        return f"data:image/png;base64,{img_b64}"
    except Exception as e:
        print(f"[ERROR] Failed to generate chart '{title}': {e}")
        return None # Return None on error
    finally:
        plt.close() # Ensure plot is closed


# --- Flask App Setup ---
app = Flask(__name__, template_folder=str(ROOT / 'templates'), static_folder=str(ROOT / 'static'))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'f8a3c9e7d6b5a4f3e2d1c0b9a8f4e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a0f5')
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = None
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16MB limit

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    with get_db() as db:
        user = db.query(User).get(int(user_id))
        if user:
            db.expunge(user) # Detach from session
        return user

# --- Decorators ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required for this page.', 'danger')
            return redirect(url_for('landing'))
        return f(*args, **kwargs)
    return decorated_function

# --- Main Routes ---
@app.route('/')
def intro():
    return render_template('intro.html')

@app.route('/dashboard')
@login_required
def landing():
    return render_template('landing.html')

# --- Auth Blueprint ---
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
# In src/app.py, inside the auth_bp blueprint

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # If already logged in, go straight to dashboard
        return redirect(url_for('landing'))

    form = LoginForm()
    if form.validate_on_submit(): # This runs when you POST (click Sign In)
        # Get data from the form
        email_attempt = form.email.data
        password_attempt = form.password.data
        print(f"--- [DEBUG] Login attempt for email: {email_attempt} ---") # Debug print

        with get_db() as db:
            # Find the user by the email they entered
            user = db.query(User).filter(User.email == email_attempt).first()

        # Check if user exists AND if the password hash matches
        if user and check_password_hash(user.password_hash, password_attempt):
            # Password is correct!
            print(f"--- [DEBUG] Password correct for user {user.username}. Logging in... ---") # Debug print
            login_user(user) # This sets the session cookie
            next_page = request.args.get('next') # For redirecting after login if needed
            flash('Login successful!', 'success')
            return redirect(next_page or url_for('landing')) # Redirect to dashboard
        else:
            # User not found OR password incorrect
            print(f"--- [DEBUG] Login failed for email: {email_attempt}. User found: {user is not None} ---") # Debug print
            flash('Invalid email or password.', 'danger')
            # No redirect here, just re-render the login page with the flash message

    # This runs for GET requests or if form validation fails
    return render_template('login.html', form=form)

# In src/app.py

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('landing')) # Already logged in, go to dashboard

    form = RegisterForm()
    if form.validate_on_submit():
        with get_db() as db:
            existing_user = db.query(User).filter(
                or_(User.email == form.email.data, User.username == form.username.data)
            ).first()

            if existing_user:
                flash('Email already registered.' if existing_user.email == form.email.data else 'Username already taken.', 'warning')
                return render_template('register.html', form=form)

            # Create new user
            user = User(
                username=form.username.data,
                email=form.email.data,
                password_hash=generate_password_hash(form.password.data)
            )
            db.add(user)
            db.commit()

            # --- CHANGES ARE HERE ---
            # login_user(user) # REMOVED: Do not automatically log in

            flash('Registration successful! Please log in.', 'success') # Updated flash message
            return redirect(url_for('auth.login')) # MODIFIED: Redirect to login page
            # --- END OF CHANGES ---

    # Handle GET request or invalid form submission
    return render_template('register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('intro'))

app.register_blueprint(auth_bp)

# --- Document Processing Route ---
# In src/app.py, replace the process_document function:

@app.route('/process', methods=['POST'])
@login_required
def process_document():
    """Process uploaded document using batch simplification"""
    file_path = None # Define file_path outside try for finally block
    try:
        # --- File Upload Handling ---
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('No file selected.', 'warning')
            return redirect(url_for('landing'))

        filename = secure_filename(file.filename)
        if not filename.lower().endswith(('.pdf', '.docx', '.txt')):
            flash('Invalid file type. Please upload PDF, DOCX, or TXT.', 'warning')
            return redirect(url_for('landing'))

        file_path = UPLOAD_FOLDER / filename
        file.save(str(file_path))
        print(f"--- [DEBUG] File saved: {filename} ---")

        # --- Text Extraction ---
        raw_text = extract_text(str(file_path))
        if not raw_text or not raw_text.strip():
            flash('Could not extract text from the file.', 'danger')
            raise ValueError("Empty text extracted")
        print(f"--- [DEBUG] Text extracted successfully ({len(raw_text)} chars). ---")

        # --- Preprocessing Steps (ADDED MORE LOGGING) ---
        print("--- [DEBUG] Calling clean_text... ---")
        processed_text = clean_text(raw_text)
        print(f"--- [DEBUG] clean_text finished. Result length: {len(processed_text)} chars. ---") # Log result length

        print("--- [DEBUG] Calling preprocess_contract_text... ---")
        processed_clauses = preprocess_contract_text(raw_text)
        print(f"--- [DEBUG] preprocess_contract_text finished. Found {len(processed_clauses)} potential clauses. ---") # Log number of clauses found

        # Check if preprocessing returned meaningful results
        if not processed_clauses:
             print("[WARN] preprocess_contract_text returned an empty list. Check the function's logic.")
             # Decide how to handle: maybe flash a warning and skip clause processing?
             # For now, continue to see if other parts work

        # --- Clause Type Detection & Batch Prep ---
        print(f"--- [DEBUG] Detecting types for {len(processed_clauses)} clauses...")
        clauses = []
        all_clause_texts_to_simplify = []
        for idx, clause_data in enumerate(processed_clauses):
            # print(f"  > Clause {idx + 1} type...") # Optional: verbose log
            clause_cleaned_text = clause_data.get('cleaned_text', '') # Safely get text
            clause_type = detect_clause_type(clause_cleaned_text)
            clauses.append({
                'index': idx + 1, 'raw_text': clause_data.get('raw_text', ''),
                'cleaned_text': clause_cleaned_text,
                'sentences': clause_data.get('sentences', []),
                'entities': clause_data.get('entities', []),
                'type': clause_type, 'simplified': "Processing..."
            })
            all_clause_texts_to_simplify.append(clause_cleaned_text)

        # --- Legal Term Extraction ---
        legal_terms = extract_legal_terms(processed_text)
        print(f"--- [DEBUG] Found {len(legal_terms)} legal terms. Batch simplifying...")

        # --- Batch Simplification ---
        texts_to_simplify_batch = [processed_text] + all_clause_texts_to_simplify
        simplified_results_batch = simplify_text(texts_to_simplify_batch)
        print("--- [DEBUG] Batch simplification done. Assigning...")

        simplified_text = processed_text # Default fallback
        if isinstance(simplified_results_batch, list) and len(simplified_results_batch) == len(texts_to_simplify_batch):
            simplified_text = simplified_results_batch[0]
            simplified_clauses_list = simplified_results_batch[1:]
            for i, clause in enumerate(clauses):
                if i < len(simplified_clauses_list): clause['simplified'] = simplified_clauses_list[i]
                else: clause['simplified'] = clause.get('cleaned_text', '') # Fallback
        else:
            print("[ERROR] Batch simplification failed. Using original/cleaned text.")
            for clause in clauses: clause['simplified'] = clause.get('cleaned_text', '')

        # --- Metrics, Charts, Highlighting ---
        print("--- [DEBUG] Calculating metrics & charts...")
        # ... (keep the rest of the code for metrics, charts, highlighting, results dict, db save) ...
        original_metrics = calculate_all_metrics(raw_text)
        simplified_metrics = calculate_all_metrics(simplified_text)
        clause_types = Counter(c.get('type', 'Unknown') for c in clauses)
        clause_chart = generate_chart_base64('pie', dict(clause_types), 'Clause Types Distribution')

        original_words = len(word_tokenize(raw_text))
        simplified_words = len(word_tokenize(simplified_text)) if simplified_text else original_words
        original_sentences = len(sent_tokenize(raw_text))
        simplified_sentences = len(sent_tokenize(simplified_text)) if simplified_text else original_sentences
        stats_data = {
            'Word Count': [original_words, simplified_words],
            'Sentence Count': [original_sentences, simplified_sentences],
            'Avg Words/Sentence': [round(original_words / max(original_sentences, 1), 1), round(simplified_words / max(simplified_sentences, 1), 1)],
            'Complex Words': [sum(1 for w in word_tokenize(raw_text) if w.isalpha() and count_syllables(w) > 2),
                              sum(1 for w in word_tokenize(simplified_text) if w.isalpha() and count_syllables(w) > 2) if simplified_text else 0]
        }
        stats_chart = generate_chart_base64('bar', stats_data, 'Text Statistics Comparison')

        print("--- [DEBUG] Highlighting terms...")
        highlighted_text = raw_text
        if legal_terms:
            unique_terms = sorted(list(set(term.get('term', term) for term in legal_terms if (isinstance(term, dict) and term.get('term')) or isinstance(term, str))), key=len, reverse=True)
            temp_highlighted_text = highlighted_text
            term_map = { (term.get('term', term) if isinstance(term, dict) else term).lower(): term for term in legal_terms if (isinstance(term, dict) and term.get('term')) or isinstance(term, str) }

            for term_word in unique_terms:
                term_data = term_map.get(term_word.lower())
                term_definition = "Legal Term"
                if isinstance(term_data, dict): term_definition = term_data.get('simplified_explanation', term_data.get('definition', 'Legal term'))
                term_definition = term_definition.replace('"', '&quot;').replace("'", '&#39;')
                pattern = re.compile(r'(\b' + re.escape(term_word) + r'\b)', re.IGNORECASE)
                temp_highlighted_text = pattern.sub(lambda m: f'<span class="highlight-legal" title="{term_definition}">{m.group(0)}</span>', temp_highlighted_text)
            highlighted_text = temp_highlighted_text

        results = {
            'clauses': clauses, 'legal_terms': legal_terms, 'simplified_text': simplified_text,
            'original_metrics': original_metrics, 'simplified_metrics': simplified_metrics,
            'clause_type_chart': clause_chart, 'stats_chart': stats_chart,
            'highlighted_text': highlighted_text
        }

        print("--- [DEBUG] Saving to DB...")
        with get_db() as db:
            document = Document(
                user_id=current_user.id, document_title=filename, original_text=raw_text,
                simplified_text_basic=simplified_text,
                original_readability_score=calculate_reading_ease(raw_text),
                report_json=json.dumps(results, default=str), # Use default=str for safety
                clause_count=len(clauses), word_count=original_words
            )
            db.add(document)
            db.commit()
            document_id = document.id

        print("--- [DEBUG] Redirecting to results. ---")
        return redirect(url_for('view_document', document_id=document_id))

    except Exception as e:
        print(f"--- [ERROR] Exception during process: {str(e)} ---")
        traceback.print_exc()
        logging.exception("Processing error occurred")
        flash(f'An error occurred during processing: {e}', 'danger')
        # Ensure cleanup happens even if error before file_path defined
        if 'file_path' in locals() and file_path and file_path.exists():
             try: file_path.unlink()
             except OSError as unlink_error: print(f"Error removing temp file on error: {unlink_error}")
        return redirect(url_for('landing'))
    finally:
        # Final cleanup attempt
         if 'file_path' in locals() and file_path and file_path.exists():
            try: file_path.unlink()
            except OSError as unlink_error: print(f"Error removing temp file in finally: {unlink_error}")

# --- Other Routes (View Document, History, Download) ---
@app.route('/document/<int:document_id>')
@login_required
def view_document(document_id):
    with get_db() as db:
        document = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not document:
        flash('Document not found or access denied.', 'warning')
        return redirect(url_for('history'))
    try:
        results = json.loads(document.report_json) if document.report_json else {}
    except json.JSONDecodeError:
        results = {}
        flash('Error loading document analysis results.', 'danger')
    # Prepare doc_data safely
    doc_data = {
        'id': document.id, 'document_title': document.document_title,
        'original_text': document.original_text,
        'simplified_text_basic': document.simplified_text_basic,
        'original_readability_score': document.original_readability_score,
        'uploaded_at': document.uploaded_at, # Pass datetime object
        'clause_count': document.clause_count, 'word_count': document.word_count
    }
    return render_template('results.html', document=doc_data, results=results)

@app.route('/history')
@login_required
def history():
    with get_db() as db:
        documents = db.query(Document).filter(Document.user_id == current_user.id).order_by(desc(Document.uploaded_at)).all()
    # Pass datetime objects directly to template for formatting
    docs_data = [{'id': doc.id, 'document_title': doc.document_title, 'uploaded_at': doc.uploaded_at, 'clause_count': doc.clause_count, 'word_count': doc.word_count, 'original_readability_score': doc.original_readability_score} for doc in documents]
    return render_template('history.html', documents=docs_data)

@app.route('/download/<int:document_id>')
@login_required
def download_report(document_id):
    with get_db() as db:
        document = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not document:
        flash('Document not found.', 'warning')
        return redirect(url_for('history'))
    try:
        report_data = {
            'document_title': document.document_title,
            'processed_at': document.uploaded_at.isoformat(),
            'original_text': document.original_text,
            'simplified_text': document.simplified_text_basic,
            'readability_score': document.original_readability_score,
            'results': json.loads(document.report_json) if document.report_json else {}
        }
        doc_title_safe = secure_filename(document.document_title).replace('.', '_') # Sanitize title
        response = make_response(json.dumps(report_data, indent=2, default=str)) # Added default=str
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = f'attachment; filename={doc_title_safe}_report.json'
        return response
    except Exception as e:
        print(f"[ERROR] Failed to generate download for doc {document_id}: {e}")
        flash('Error generating report for download.', 'danger')
        return redirect(url_for('history'))


# --- Admin Dashboard Route ---
@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    try:
        with get_db() as db:
            # 1. Stat Cards
            total_users = db.query(User).count()
            total_documents = db.query(Document).count()
            today_date = datetime.utcnow().date()
            active_today = db.query(func.count(func.distinct(Document.user_id))).filter(func.date(Document.uploaded_at) == today_date).scalar() or 0

            # 2. Registration Chart (Last 7 Days) - Daily
            registration_data = []
            seven_days_ago = today_date - timedelta(days=6)
            registrations = db.query(
                func.strftime('%Y-%m-%d', User.created_at).label('date'),
                func.count(User.id).label('count')
            ).filter(
                func.date(User.created_at) >= seven_days_ago
            ).group_by('date').order_by('date').all() # Use alias 'date'

            reg_dict = {reg.date: reg.count for reg in registrations}

            for i in range(7):
                date_obj = seven_days_ago + timedelta(days=i)
                date_str = date_obj.isoformat()
                registration_data.append({'date': date_str, 'count': reg_dict.get(date_str, 0)})

            # 3. Documents Processed Weekly Chart (Last 4 Weeks)
            processed_docs_weekly_data = []
            # Go back almost 4 full weeks from start of *this* week to ensure we capture relevant data
            today_weekday = today_date.weekday() # Monday is 0, Sunday is 6
            start_of_current_week = today_date - timedelta(days=today_weekday)
            four_weeks_ago_start = start_of_current_week - timedelta(weeks=4)

            docs_processed_weekly = db.query(
                func.strftime('%Y-%W', Document.uploaded_at).label('year_week'), # YYYY-WW (Week starts Sunday by default in SQLite %W)
                func.count(Document.id).label('count')
            ).filter(
                func.date(Document.uploaded_at) >= four_weeks_ago_start
                # Ensure we don't go past today if needed (usually not necessary for past weeks)
                # and func.date(Document.uploaded_at) <= today_date
            ).group_by('year_week').order_by('year_week').all()

            docs_weekly_dict = {doc.year_week: doc.count for doc in docs_processed_weekly}

            # Generate labels for the last 4 weeks (ending with the current week)
            for i in range(4):
                # Calculate week label (e.g., "Week 43")
                target_week_start = start_of_current_week - timedelta(weeks=3 - i)
                # Use ISO calendar for week number that starts on Monday, more standard
                year, week_num, _ = target_week_start.isocalendar()
                
                # Format key for SQLite lookup (may need adjustment if %W starts Sunday)
                # Let's try ISO week format for lookup too if strftime supports %V or %G
                # If using %W (starts Sunday), need careful mapping or adjustment
                sqlite_week_key = target_week_start.strftime('%Y-%W') # Example if %W used

                processed_docs_weekly_data.append({
                    'week': f"W{week_num}", # Label like W43
                    'year_week_iso': f"{year}-{week_num:02d}",
                    'count': docs_weekly_dict.get(sqlite_week_key, 0) # Lookup using SQLite week format
                })


            # 4. Active Users Table
            active_users = db.query(
                User.username,
                func.count(Document.id).label('doc_count')
            ).join(
                Document, User.id == Document.user_id, isouter=True
            ).group_by(User.id).order_by(desc('doc_count')).limit(5).all()

        return render_template(
            'admin_dashboard.html',
            total_users=total_users,
            total_documents=total_documents,
            active_today=active_today,
            registration_data=registration_data,
            processed_docs_weekly_data=processed_docs_weekly_data,
            active_users=active_users
        )
    except Exception as e:
        print(f"--- [ERROR] Failed to load admin dashboard: {e} ---")
        traceback.print_exc()
        flash("Error loading admin dashboard data.", "danger")
        # Redirect to a safe page, maybe user dashboard?
        return redirect(url_for('landing'))


# --- App Runner ---
if __name__ == '__main__':
    init_db()
    # Load models on startup if components are available
    if COMPONENTS_AVAILABLE:
        print("Loading AI models...")
        try:
            ensure_model_loaded()      # For clause detection
            ensure_simplifier_loaded() # For simplification
            print("AI models loaded.")
        except Exception as model_error:
            print(f"[ERROR] Failed to load AI models on startup: {model_error}")
    else:
        print("[WARN] Components missing, skipping AI model loading.")

    print("Starting Flask app...")
    # Consider removing debug=True for production
    app.run(debug=True, port=5000)