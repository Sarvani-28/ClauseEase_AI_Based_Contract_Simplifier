import re
import nltk
try:
    import spacy
except Exception:
    spacy = None

from nltk.tokenize import sent_tokenize

# Download NLTK data
nltk.download('punkt')
nltk.download('punkt_tab')

# Load spaCy model
nlp = None
if spacy is not None:
    try:
        nlp = spacy.load("en_core_web_sm")
        print("spaCy model 'en_core_web_sm' loaded successfully for entity extraction")
    except Exception as e:
        print(f"Could not load spaCy model: {e}")
        print("Run: python -m spacy download en_core_web_sm")
        nlp = None


# Text cleaning functions

def clean_text(text: str) -> str:
    """Clean and normalize text"""
    text = text.replace('\xa0', ' ')
    text = re.sub(r'[\r\f\v]', '', text)
    text = re.sub(r'\s+', ' ', text)  # Collapse spaces
    # Normalize smart quotes
    quote_map = {
        '"': '"',
        '"': '"',
        ''': "'",
        ''': "'",
    }
    for src, replacement in quote_map.items():
        text = text.replace(src, replacement)
    return text.strip()


def segment_clauses(text: str) -> list:
    """Split text into clauses"""
    if not text or not text.strip():
        return [text]
    
    # Normalize line breaks
    text = re.sub(r'\r\n?', '\n', text)
    text = re.sub(r'\n+', '\n', text)
    
    # Define clause markers
    markers = [
        (r'(Annexure-?\s*)', 'ANNEXURE'),
        (r'(AGREEMENT FORMAT)', 'HEADING'),
        (r'(\(ON NON-JUDICIAL)', 'SUBHEADING'),
        (r'(This\s+agreement\s+is\s+made)', 'PREAMBLE'),
        (r'(\bAND\s*\n)', 'AND_SEPARATOR'),
        (r'(Whereas\s+the\s+Employer)', 'WHEREAS'),
        (r'(NOW THIS AGREEMENT WITNESSETH)', 'WITNESSETH'),
        (r'(\n\s*\d+\.\s+[A-Z])', 'NUMBERED_CLAUSE'),
        (r'(In witness whereof)', 'IN_WITNESS'),
        (r'(The Common Seal)', 'SEAL'),
        (r'(Signed Sealed and Delivered)', 'SIGNED'),
        (r'(For & on behalf of Employer)', 'EMPLOYER_SIG'),
        (r'(For & on behalf of Contractor)', 'CONTRACTOR_SIG'),
        (r'(\bNote:)', 'NOTE'),
    ]
    
    # Find all markers
    splits = []
    for pattern, label in markers:
        for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            splits.append((match.start(), label, match.group(0)))
    
    # Sort by position
    splits.sort(key=lambda x: x[0])
    
    if not splits:
        # Fallback to paragraphs
        print("No clause markers found, using paragraph-based split...")
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n+', text) if p.strip()]
        clauses = [p for p in paragraphs if len(p) > 20]
        print(f"Raw text length: {len(text)} characters")
        print(f"Text segmented into {len(clauses)} parts (paragraph-based)")
        return clauses if clauses else [text]
    
    # Extract clauses
    clauses = []
    for i, (pos, label, matched_text) in enumerate(splits):
        if i == 0 and pos > 0:
            # Add pre-marker text
            clauses.append(text[:pos].strip())
        
        # Find end position
        end_pos = splits[i+1][0] if i+1 < len(splits) else len(text)
        clause_text = text[pos:end_pos].strip()
        
        if clause_text and len(clause_text) > 15:
            clauses.append(clause_text)
    
    # Clean up clauses
    clauses = [c.strip() for c in clauses if c.strip() and len(c.strip()) > 10]
    
    print(f"Raw text length: {len(text)} characters")
    print(f"Found {len(splits)} clause markers")
    print(f"Text segmented into {len(clauses)} parts")
    
    return clauses if clauses else [text]


def split_sentences(text: str) -> list:
    """Split text into sentences"""
    return sent_tokenize(text)


# Named entity extraction

def extract_entities(text: str) -> list:
    """Extract named entities"""
    if nlp is None:
        return []  # spaCy unavailable
    
    try:
        doc = nlp(text)
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        return entities
    except Exception as e:
        print(f"Error extracting entities: {e}")
        return []


def preprocess_clause(clause_text: str) -> dict:
    """Preprocess single clause"""
    cleaned = clean_text(clause_text)
    sentences = split_sentences(cleaned)
    entities = extract_entities(cleaned)
    
    return {
        "raw_text": clause_text,
        "cleaned_text": cleaned,
        "sentences": sentences,
        "entities": entities
    }


# Batch processing

def preprocess_contract_text(raw_text: str) -> list:
    """Preprocess entire contract"""
    cleaned_text = clean_text(raw_text)
    clauses = segment_clauses(cleaned_text)
    
    processed = []
    for clause in clauses:
        result = preprocess_clause(clause)
        processed.append(result)
    
    return processed