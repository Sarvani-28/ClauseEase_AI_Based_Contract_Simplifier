import os
from pathlib import Path
import traceback

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


# In components/module5_language_simplification.py
# Replace the simplify_text function with this:

def simplify_text(text_input, max_length=60, min_length=10):
    """
    Simplify legal text. Accepts a single string or a list of strings.
    If a single string is passed, it processes sentence by sentence but batches the AI calls.
    If a list is passed, it processes the list directly as a batch.
    """
    global _simplifier, _load_attempted
    
    # Auto-load model if needed
    if _HAS_HF and _simplifier is None and not _load_attempted:
        print("Auto-loading AI simplification model (facebook/bart-large-cnn)...")
        ensure_simplifier_loaded("facebook/bart-large-cnn")
        
    if not _simplifier:
        print("[WARN] Simplifier model not loaded. Skipping simplification.")
        return text_input # Return original input if model failed to load

    # --- BATCH PROCESSING LOGIC ---
    is_batch = isinstance(text_input, list)
    
    if is_batch:
        # Input is already a list of texts
        texts_to_process = text_input
        print(f"--- [DEBUG] simplify_text received a batch of {len(texts_to_process)} items. ---")
    else:
        # Input is a single string, process sentence by sentence
        if not text_input or not text_input.strip() or len(text_input.split()) <= 10:
            return text_input # Return short texts as is

        try:
            from nltk.tokenize import sent_tokenize
            sentences = sent_tokenize(text_input)
            print(f"--- [DEBUG] simplify_text processing {len(sentences)} sentences from single string. ---")
        except Exception as e:
            print(f"[WARN] NLTK sentence tokenization failed: {e}. Processing full text.")
            sentences = [text_input] # Fallback to processing the whole text

        texts_to_process = sentences # For consistency, we'll process this list
        
    # --- Run the AI model (only once if possible) ---
    simplified_outputs = []
    try:
        # Filter out very short sentences/texts before sending to model
        valid_texts_to_process = []
        original_indices = [] # Keep track of original position
        placeholder_results = {} # Store short sentences to merge back later
        
        for i, text in enumerate(texts_to_process):
            if len(text.strip()) < 20:
                 placeholder_results[i] = text # Keep short sentence as is
            else:
                valid_texts_to_process.append(text)
                original_indices.append(i)

        if not valid_texts_to_process:
             # If all sentences were short, just reconstruct
             simplified_outputs = [placeholder_results.get(i, "") for i in range(len(texts_to_process))]
             print("--- [DEBUG] No valid sentences long enough for simplification. ---")
        else:
            print(f"--- [DEBUG] Sending batch of {len(valid_texts_to_process)} texts to AI model... ---")
            # Use dynamic max_length based on average? Or fixed? Let's try fixed first.
            # Using the function's default max_length
            
            results = _simplifier(
                valid_texts_to_process, 
                max_length=max_length, 
                min_length=min_length,
                do_sample=False,
                truncation=True
            )
            print("--- [DEBUG] AI model batch processing finished. ---")

            # Merge results back with placeholders
            simplified_batch_map = {original_indices[i]: result['summary_text'].strip() for i, result in enumerate(results)}
            
            simplified_outputs = []
            for i in range(len(texts_to_process)):
                if i in placeholder_results:
                    simplified_outputs.append(placeholder_results[i])
                elif i in simplified_batch_map:
                    # Basic check to ensure simplification didn't fail badly or expand too much
                    ai_output = simplified_batch_map[i]
                    original_sent = texts_to_process[i]
                    if len(ai_output) > 5 and len(ai_output) <= len(original_sent) * 1.5:
                         simplified_outputs.append(ai_output)
                    else:
                         simplified_outputs.append(original_sent) # Revert if output is bad
                else:
                    simplified_outputs.append(texts_to_process[i]) # Fallback

    except Exception as e:
        print(f"[ERROR] AI simplification failed during batch processing: {e}")
        traceback.print_exc()
        # Return original input(s) on error
        return text_input 

    # --- Return in the original format ---
    if is_batch:
        return simplified_outputs
    else:
        # Join sentences back if input was a single string
        return ' '.join(simplified_outputs)