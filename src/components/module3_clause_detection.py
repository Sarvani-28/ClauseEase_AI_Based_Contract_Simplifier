# Clause type labels
CLAUSE_LABELS = {
    0: "Confidentiality",
    1: "Termination",
    2: "Indemnity",
    3: "Dispute Resolution",
    4: "Governing Law",
    5: "Payment Terms",
    6: "Intellectual Property",
    7: "Warranties",
    8: "Limitation of Liability",
    9: "Force Majeure",
    10: "Assignment",
    11: "Non-Compete",
    12: "Severability",
    13: "Amendment",
    14: "Notice"
}

try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
    _HAS_TRANSFORMERS = True
except Exception:
    _HAS_TRANSFORMERS = False

_model = None
_tokenizer = None


def _load_model(model_name="nlpaueb/legal-bert-base-uncased", num_labels=15):
    """Load BERT model"""
    global _model, _tokenizer
    if not _HAS_TRANSFORMERS:
        return False
    try:
        _tokenizer = AutoTokenizer.from_pretrained(model_name)
        _model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=num_labels)
        return True
    except Exception:
        _model = None
        _tokenizer = None
        return False


def _rule_based_classify(text: str) -> str:
    """Classify using keyword rules"""
    t = text.lower()
    if any(w in t for w in ["confidential", "confidentiality", "non-disclosure", "nda", "proprietary information"]):
        return "Confidentiality"
    if any(w in t for w in ["terminate", "termination", "expire", "end of contract", "breach", "cancel"]):
        return "Termination"
    if any(w in t for w in ["indemnify", "indemnity", "hold harmless", "defend against"]):
        return "Indemnity"
    if any(w in t for w in ["arbitration", "dispute", "mediation", "court", "sole arbitrator", "litigation"]):
        return "Dispute Resolution"
    if any(w in t for w in ["governing law", "laws in force", "law of ", "applicable law"]):
        return "Governing Law"
    if any(w in t for w in ["payment", "fee", "invoice", "compensation", "price", "remuneration", "salary"]):
        return "Payment Terms"
    if any(w in t for w in ["intellectual property", "copyright", "trademark", "patent", "ip rights", "ownership"]):
        return "Intellectual Property"
    if any(w in t for w in ["warranty", "warranties", "represent", "guarantee", "assurance"]):
        return "Warranties"
    if any(w in t for w in ["limitation of liability", "limited to", "aggregate liability", "consequential damages"]):
        return "Limitation of Liability"
    if any(w in t for w in ["force majeure", "act of god", "natural disaster", "unforeseen circumstances"]):
        return "Force Majeure"
    if any(w in t for w in ["assignment", "transfer", "assign rights", "delegate"]):
        return "Assignment"
    if any(w in t for w in ["non-compete", "non compete", "competitive", "solicitation", "restrictive covenant"]):
        return "Non-Compete"
    if any(w in t for w in ["severability", "severable", "invalid provision", "unenforceable"]):
        return "Severability"
    if any(w in t for w in ["amendment", "modify", "modification", "change", "variation"]):
        return "Amendment"
    if any(w in t for w in ["notice", "notification", "inform", "written notice", "email to"]):
        return "Notice"
    return "Other"


def detect_clause_type(text: str) -> str:
    """Detect clause type"""
    if not text or not text.strip():
        return "Other"

    # Try model-based prediction
    if _model and _tokenizer:
        try:
            inputs = _tokenizer(text, return_tensors="pt", truncation=True, padding=True)
            with torch.no_grad():
                outputs = _model(**inputs)
            logits = outputs.logits
            predicted = int(torch.argmax(logits, dim=1).item())
            return CLAUSE_LABELS.get(predicted, "Other")
        except Exception:
            return _rule_based_classify(text)

    # Fallback to rules
    return _rule_based_classify(text)


def detect_clause_types_batch(texts):
    """Batch clause detection"""
    return [detect_clause_type(t) for t in texts]


def ensure_model_loaded(model_name="nlpaueb/legal-bert-base-uncased", num_labels=15):
    """Ensure model is loaded"""
    return _load_model(model_name=model_name, num_labels=num_labels)
