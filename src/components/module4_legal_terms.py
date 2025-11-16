import re

# Legal term categories mapping
_LEXICON = {
    "indemnity": "Indemnity Clause",
    "indemnify": "Indemnity Clause",
    "security deposit": "Payment Terms",
    "termination": "Termination Clause",
    "arbitration": "Dispute Resolution",
    "dispute resolution": "Dispute Resolution",
    "force majeure": "Force Majeure",
    "governing law": "Governing Law",
    "warranty": "Warranty",
    "confidential": "Confidentiality",
    "intellectual property": "IP Rights",
    "non-compete": "Non-Compete",
    "severability": "Severability",
    "amendment": "Amendment Rights",
    "assignment": "Assignment Rights",
    "liability": "Liability",
    "damages": "Damages",
}

# Simple language definitions
_DEFINITIONS = {
    "indemnity": "A promise to protect someone from financial loss or legal liability",
    "indemnify": "To compensate or reimburse someone for loss or damage",
    "security deposit": "Money held by one party as protection in case of damage or default",
    "termination": "The act of ending or canceling a contract or agreement",
    "arbitration": "Resolving a dispute outside of court with a neutral third party making the decision",
    "dispute resolution": "Methods used to settle disagreements or conflicts",
    "force majeure": "Unforeseeable circumstances that prevent someone from fulfilling a contract (like natural disasters)",
    "governing law": "The legal system and rules that apply to a contract",
    "the governing law": "The legal system and rules that apply to this contract",
    "warranty": "A guarantee or promise about the quality or condition of something",
    "confidential": "Information that must be kept private and not shared with others",
    "intellectual property": "Creations of the mind like inventions, designs, brand names, and artistic works",
    "non-compete": "An agreement not to compete with a business in the same industry or area",
    "severability": "If one part of a contract is invalid, the rest of the contract remains valid",
    "amendment": "A formal change or addition to a contract or document",
    "assignment": "Transferring rights or responsibilities from one party to another",
    "liability": "Legal responsibility for something, especially for costs or damages",
    "damages": "Money paid as compensation for loss or injury",
    "consideration": "Something of value exchanged between parties in a contract",
    "breach": "Breaking or violating the terms of a contract",
    "covenant": "A formal promise or agreement in a contract",
    "party": "A person or organization involved in a contract or legal agreement",
    "effective date": "The date when a contract or agreement officially begins",
    "notice": "Formal communication or warning given to another party",
    "terms and conditions": "The detailed rules and requirements of an agreement",
    "agreement": "A mutual understanding or arrangement between two or more parties",
    "obligations": "Duties or responsibilities that must be fulfilled under a contract",
    "rights": "Legal entitlements or permissions granted by a contract",
    "default": "Failure to fulfill an obligation or payment as required",
    "cure period": "Time given to fix a problem or breach before penalties apply",
    "remedies": "Solutions or compensations available when a contract is broken",
    "waiver": "Voluntarily giving up a right or claim",
    "execution": "The act of signing and making a contract legally binding",
    "representations": "Statements of fact made by one party to another",
    "warranties": "Promises or guarantees about facts or conditions",
    "audit": "An official examination or review of records or accounts",
    "compliance": "Following or obeying rules, laws, or requirements",
    "confidentiality": "The state of keeping information secret or private",
    "disclosure": "Revealing or making information known",
    "exclusivity": "The right to be the only one to do something in an agreement",
    "jurisdiction": "The authority of a court or legal system to hear a case",
    "limitation of liability": "A cap or restriction on the amount of damages that can be claimed",
    "liquidated damages": "A predetermined amount of money to be paid if a contract is broken",
    "material breach": "A serious violation of a contract that affects its core purpose",
    "mutual consent": "Agreement by all parties involved",
    "non-disclosure": "An agreement to keep certain information confidential",
    "performance": "Completing the obligations required by a contract",
    "renewal": "Extending a contract for an additional period",
    "representations and warranties": "Statements and promises made about facts and conditions",
    "services": "Work or assistance provided under an agreement",
    "service": "Work or assistance provided under an agreement",
    "the service provider": "The person or company providing work or assistance under the agreement",
    "service provider": "The person or company providing work or assistance",
    "parties": "People or organizations involved in a contract or legal agreement",
    "the effective date": "The specific date when a contract or agreement officially begins",
    "sole discretion": "The complete freedom to make a decision without needing approval",
    "sublicense": "Permission granted by a licensee to allow someone else to use licensed rights",
    "subsidiary": "A company controlled by another company",
    "term": "The length or duration of a contract",
    "third party": "A person or entity not directly involved in an agreement",
    "title": "Legal ownership of property or rights",
    "venue": "The location where a legal case will be heard",
    "void": "Having no legal effect or validity",
    "voidable": "Valid but can be legally canceled under certain conditions",
    "the state of uttarakhand": "A state in northern India, mentioned as the governing jurisdiction",
    "state": "A political territory with its own government and laws",
}

# Load spaCy model
try:
    import spacy
    _HAS_SPACY = True
    try:
        _SPACY_NLP = spacy.load("en_core_web_sm")
    except Exception:
        _SPACY_NLP = None
except Exception:
    _HAS_SPACY = False
    _SPACY_NLP = None


def extract_legal_terms(text: str):
    """Extract and define legal terms"""
    if not text or not text.strip():
        return []

    found = []
    seen = set()  # Prevent duplicates
    
    # Extract quoted terms
    quoted_pattern = r'["\']([A-Z][A-Za-z\s]{2,30})["\']'
    for match in re.finditer(quoted_pattern, text):
        term = match.group(1).strip()
        term_lower = term.lower()
        if term_lower not in seen:
            definition = _DEFINITIONS.get(term_lower, "Legal terminology used in contracts.")
            found.append({
                "term": term,
                "category": "Defined Term",
                "definition": definition,
                "simplified_explanation": definition
            })
            seen.add(term_lower)
    
    # Extract definition patterns
    definition_pattern = r'([A-Z][A-Za-z\s]{2,30})\s*(?:\(hereinafter|shall mean|means|refers to)'
    for match in re.finditer(definition_pattern, text):
        term = match.group(1).strip()
        term_lower = term.lower()
        if term_lower not in seen:
            definition = _DEFINITIONS.get(term_lower, "Legal terminology used in contracts.")
            found.append({
                "term": term,
                "category": "Defined Term",
                "definition": definition,
                "simplified_explanation": definition
            })
            seen.add(term_lower)
    
    # Check lexicon keywords
    t = text.lower()
    for keyword, category in _LEXICON.items():
        if keyword in t:
            if keyword not in seen:
                definition = _DEFINITIONS.get(keyword, "Legal terminology used in contracts.")
                found.append({
                    "term": keyword.title(),
                    "category": category,
                    "definition": definition,
                    "simplified_explanation": definition
                })
                seen.add(keyword)
    
    # Use spaCy NER
    if _SPACY_NLP:
        try:
            doc = _SPACY_NLP(text[:5000])  # Performance limit
            for ent in doc.ents:
                if ent.label_ in ['LAW', 'ORG', 'EVENT']:
                    ent_text = ent.text.strip()
                    
                    # Skip quotes
                    if '"' in ent_text or "'" in ent_text:
                        continue
                    
                    # Skip repeated words
                    words = ent_text.lower().split()
                    if len(words) != len(set(words)):
                        continue
                    
                    ent_text_lower = ent_text.lower()
                    if ent_text_lower not in seen:
                        definition = _DEFINITIONS.get(ent_text_lower, "Legal terminology used in contracts.")
                        found.append({
                            "term": ent_text,
                            "category": f"{ent.label_} Entity",
                            "definition": definition,
                            "simplified_explanation": definition
                        })
                        seen.add(ent_text_lower)
        except Exception:
            pass  # Silent fail

    return found
