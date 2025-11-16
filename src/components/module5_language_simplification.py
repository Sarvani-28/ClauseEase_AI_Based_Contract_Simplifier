import os
from pathlib import Path

try:
    from transformers import pipeline
    _HAS_HF = True
except Exception:
    _HAS_HF = False

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[OK] Loaded environment from {env_path}")
except ImportError:
    print("[WARN] python-dotenv not installed, skipping .env loading")
    pass

# Get HF token
HF_TOKEN = os.environ.get("HUGGINGFACE_HUB_TOKEN")

_simplifier = None
_load_attempted = False


def ensure_simplifier_loaded(model_name="facebook/bart-large-cnn"):
    """Load simplification model"""
    global _simplifier, _load_attempted
    
    if _load_attempted:
        return _simplifier is not None
    
    _load_attempted = True
    
    if not _HAS_HF:
        return False
    try:
        kwargs = {"use_fast": False}
        if HF_TOKEN:
            kwargs["token"] = HF_TOKEN
        print("Using Hugging Face token from environment")
        
        _simplifier = pipeline("summarization", model=model_name, **kwargs)
        print(f"Loaded simplification model: {model_name}")
        return True
    except Exception as e:
        print(f"Failed to load simplifier: {e}")
        _simplifier = None
        return False


def simplify_text(text: str, max_length=60, level="basic"):
    """
    Multi-level text simplification
    
    Args:
        text: Input text
        max_length: Maximum output length
        level: Simplification intensity ('basic', 'intermediate', 'advanced')
    
    Returns:
        Simplified text string
    """
    global _simplifier, _load_attempted
    
    if not text or not text.strip():
        return text
    
    # Auto-load model
    if _HAS_HF and _simplifier is None and not _load_attempted:
        print("Auto-loading AI simplification model (facebook/bart-large-cnn)...")
        ensure_simplifier_loaded("facebook/bart-large-cnn")
    
    if _simplifier and len(text.split()) > 10:
        try:
            from nltk.tokenize import sent_tokenize
            sentences = sent_tokenize(text)
            
            # Level-specific parameters
            if level == "basic":
                temperature = 0.5
                length_ratio = 0.85
                max_sentence_length = 30
            elif level == "intermediate":
                temperature = 0.7
                length_ratio = 0.70
                max_sentence_length = 25
            else:  # advanced
                temperature = 1.0
                length_ratio = 0.55
                max_sentence_length = 20
            
            simplified_sentences = []
            for sent in sentences:
                if len(sent.strip()) < 20:
                    simplified_sentences.append(sent)
                    continue
                
                try:
                    sent_words = len(sent.split())
                    dynamic_max_length = max(15, min(int(sent_words * length_ratio), 50))
                    
                    result = _simplifier(
                        sent, 
                        max_length=dynamic_max_length, 
                        min_length=10,
                        do_sample=True,
                        temperature=temperature,
                        top_p=0.95,
                        truncation=True
                    )
                    
                    if result and len(result) > 0 and 'summary_text' in result[0]:
                        ai_output = result[0]['summary_text'].strip()
                        
                        if level == "advanced":
                            ai_output = _aggressive_simplification(ai_output, max_sentence_length)
                        elif level == "intermediate":
                            ai_output = _moderate_simplification(ai_output, max_sentence_length)
                        
                        if len(ai_output) > 5 and len(ai_output) <= len(sent) * 1.5:
                            simplified_sentences.append(ai_output)
                        else:
                            simplified_sentences.append(sent)
                    else:
                        simplified_sentences.append(sent)
                        
                except Exception as e:
                    simplified_sentences.append(sent)
            
            return ' '.join(simplified_sentences)
            
        except Exception as e:
            print(f"[WARN] AI simplification failed: {e}")
            return text
    
    return text


def _aggressive_simplification(text: str, max_length: int) -> str:
    words = text.split()
    if len(words) > max_length:
        text = ' '.join(words[:max_length])
        if text and text[-1].isalnum():
            text += '.'

    replacements = {
        'aforementioned': 'mentioned',
        'herein': 'here',
        'thereof': 'of it',
        'whereby': 'by which',
        'hereunder': 'under this',
        'thereto': 'to it',
        'pursuant to': 'according to',
        'notwithstanding': 'despite'
    }

    for old, new in replacements.items():
        text = text.replace(old, new)
        text = text.replace(old.capitalize(), new.capitalize())

    return text


def _moderate_simplification(text: str, max_length: int) -> str:
    """Intermediate post-processing"""
    # Basic term replacement
    replacements = {
        'aforementioned': 'mentioned',
        'herein': 'here',
        'pursuant to': 'according to'
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
        text = text.replace(old.capitalize(), new.capitalize())
    
    return text

