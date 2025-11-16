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
ClauseEase/
│
├── data/               # Sample contract datasets                                                                                                                                                                     
├── scripts/            # Python scripts for processing and analysis                                                                                                                                                  
├── src/                # Core application logic                                                                                                                                                                        
│   ├── extractor.py    # Clause extraction logic                                                                                                                                                                    
│   ├── summarizer.py   # Clause simplification logic                                                                                                                                                                          
│   └── generator.py    # Template generation logic                                                                                                                                                                            
├── static/             # Static files for web interface                                                                                                                                                              
├── templates/          # HTML templates for web interface                                                                                                                                                            
├── .env.example        # Environment variable example                                                                                                                                                                  
├── .gitignore          # Git ignore rules                                                                                                                                                                              
├── requirements.txt    # Python dependencies                                                                                                                                                                                          
└── app.py              # Flask application entry point                                                                                                                                                                                        


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
