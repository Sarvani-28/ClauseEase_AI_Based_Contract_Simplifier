ClauseEase: AI-Based Contract Simplifier

ClauseEase is an innovative Python-based application designed to simplify complex legal contracts using Natural Language Processing (NLP) and machine learning techniques. The tool extracts key clauses from legal documents and presents them in plain language, making legal content more accessible to non-experts.

🚀 Features

  Clause Extraction: Identifies and extracts standard legal clauses such as indemnity, termination, confidentiality, and force majeure.
  
  Simplified Summaries: Converts complex legal jargon into easy-to-understand summaries.
  
  Template Generation: Allows users to generate contract templates with predefined clauses.
  
  Custom Clause Insertion: Enables users to add custom clauses to existing contracts.
  
  Multi-format Support: Handles various document formats including DOCX, PDF, and TXT.

🧰 Technologies Used

  Programming Language: Python
  
  Libraries:
  
  spaCy for NLP tasks
  
  PyPDF2 for PDF handling
  
  python-docx for DOCX files
  
  Flask for web application framework
  
  Machine Learning:
  
  Pre-trained NLP models for clause identification
  
  Custom models for clause simplification

📁 Project Structure
Clause_Ease_AI_Based_Contract_Language_Simplifier/
│
├── src/                                # Main application code
│   ├── app.py                          # Flask application entry point
│   └── components/                     # Core NLP processing modules
│       ├── module1_document_ingestion.py       # PDF/DOCX/TXT extraction
│       ├── module2_text_preprocessing.py       # Text cleaning
│       ├── module3_clause_detection.py         # Clause classification
│       ├── module4_legal_terms.py              # Legal term extraction
│       ├── module5_language_simplification.py  # Text simplification
│       └── readability_metrics.py              # Readability scoring
│
├── templates/                          # HTML templates (Jinja2)
│   ├── index.html                       # Base layout
│   ├── login.html                      # Login page
│   ├── register.html                   # Registration page
│   ├── landing.html                    # Main dashboard
│   ├── results.html                    # Results display page
│   └── history.html                    # Document history page
│
├── static/                             # CSS and JavaScript files
│   ├── css/                            # Stylesheets
│   │   ├── auth.css                    # Login/Register styling
│   │   ├── landing.css                 # Dashboard styling
│   │   ├── results.css                 # Results page styling
│   │   └── history.css                 # History page styling
│   └── js/                             # JavaScript files
│       ├── landing.js                  # Dashboard functionality
│       └── results.js                  # Results page functionality
│
├── scripts/                            # Utility scripts
│   ├── download_models.py              # NLP model downloader
│
├── data/                               # Database storage (auto-created)
│   └── clauseease.db                   # SQLite database
│
├── temp_uploads/                       # Temporary file storage (auto-created)
│
├── requirements.txt                    # Python dependencies
├── .env.example                        # Environment variables template
├── .gitignore                          # Git ignore rules
└── README.md                           # This file                                                                                                                                                                                      


🛠️ Installation

Clone the repository:

git clone https://github.com/Sarvani-28/ClauseEase_AI_Based_Contract_Simplifier.git
cd ClauseEase_AI_Based_Contract_Simplifier


Create a virtual environment:

python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`


Install dependencies:

pip install -r requirements.txt


Set up environment variables by copying .env.example to .env and configuring your settings.

⚙️ Usage

Run the Flask application:

  python app.py


Access the application in your web browser at http://127.0.0.1:5000.

Upload a contract document to extract and simplify clauses.

  🧪 Testing

Unit tests are located in the tests/ directory. To run the tests:

  pytest

📞 Contact

For questions or contributions, please contact me at mulukutlasarvani@gmail.com
