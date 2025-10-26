// Landing page JavaScript for Flask templates
document.addEventListener('DOMContentLoaded', () => {
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                const navbarHeight = 80;
                const elementPosition = targetElement.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - navbarHeight;
                
                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // Handle file selection
    const fileInput = document.getElementById('file-input');
    if (fileInput) {
        fileInput.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file) {
                document.getElementById('filename').textContent = file.name;
                document.getElementById('file-selected').style.display = 'block';
            }
        });
    }
});

function openFileUpload() {
    const uploadSection = document.getElementById('demo');
    const navbarHeight = 80;
    const elementPosition = uploadSection.getBoundingClientRect().top;
    const offsetPosition = elementPosition + window.pageYOffset - navbarHeight - 40;
    
    window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
    });
}

function openFileUpload() {
    const uploadSection = document.getElementById('demo');
    const navbarHeight = 80;
    const elementPosition = uploadSection.getBoundingClientRect().top;
    const offsetPosition = elementPosition + window.pageYOffset - navbarHeight - 40;
    
    window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
    });
}

function triggerFileInput() {
    document.getElementById('file-input').click();
}

// Handle form submission with progress indication
const uploadForm = document.getElementById('upload-form');
if (uploadForm) {
    uploadForm.addEventListener('submit', function(e) {
        const fileInput = document.getElementById('file-input');
        if (!fileInput.files.length) {
            e.preventDefault();
            alert('Please select a file first');
            return;
        }
        
        // Show progress section
        document.querySelector('.btn-process').style.display = 'none';
        document.getElementById('progress-section').style.display = 'block';
        
        // Animate progress bar
        const progressFill = document.getElementById('progress-fill');
        const progressPercentage = document.getElementById('progress-percentage');
        
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += 1;
            if (progress <= 98) {
                progressFill.style.width = progress + '%';
                progressPercentage.textContent = progress + '%';
            } else {
                // Keep at 98% until actual redirect happens
                clearInterval(progressInterval);
                progressFill.style.width = '98%';
                progressPercentage.textContent = '98%';
            }
        }, 200);
        
        // Form will redirect automatically when server responds
        // No need to manually redirect - let the form submission handle it
    });
}

// Technology Details Data
const techDetails = {
    python: {
        icon: '🐍',
        title: 'Python',
        version: '3.11.0',
        description: 'Python is a high-level, interpreted programming language known for its simplicity and readability. It\'s widely used in AI, machine learning, web development, and scientific computing.',
        features: [
            'Easy-to-learn syntax and readability',
            'Extensive standard library and third-party packages',
            'Strong support for AI/ML frameworks',
            'Cross-platform compatibility',
            'Dynamic typing and memory management'
        ],
        usecase: 'We use Python 3.11 as our primary backend language for its excellent AI/ML library ecosystem, making it perfect for natural language processing and document analysis tasks.'
    },
    transformers: {
        icon: '🤖',
        title: 'Transformers (Hugging Face)',
        version: '4.56.2',
        description: 'Transformers is a state-of-the-art library by Hugging Face providing pre-trained models for natural language understanding and generation tasks using transformer architectures.',
        features: [
            'Access to 100,000+ pre-trained models',
            'Support for BERT, GPT, T5, BART, and more',
            'Easy fine-tuning and inference',
            'Multi-language and multi-task support',
            'Seamless PyTorch/TensorFlow integration'
        ],
        usecase: 'We leverage legal-bert-base-uncased for clause classification and facebook/bart-large-cnn for text simplification, providing accurate legal document analysis.'
    },
    pytorch: {
        icon: '🔥',
        title: 'PyTorch',
        version: '2.8.0',
        description: 'PyTorch is an open-source machine learning framework developed by Facebook\'s AI Research lab. It provides tensor computation with GPU acceleration and automatic differentiation for building neural networks.',
        features: [
            'Dynamic computational graphs',
            'GPU acceleration with CUDA support',
            'Intuitive Python-first design',
            'Strong ecosystem for research and production',
            'TorchScript for model optimization'
        ],
        usecase: 'PyTorch powers our deep learning models, enabling efficient training and inference of transformer models on both CPU and GPU for fast document processing.'
    },
    spacy: {
        icon: '⚡',
        title: 'spaCy',
        version: '3.7.2',
        description: 'spaCy is an industrial-strength natural language processing library designed for production use. It excels at large-scale information extraction and text preprocessing tasks.',
        features: [
            'Fast and efficient NLP pipeline',
            'Named Entity Recognition (NER)',
            'Part-of-speech tagging',
            'Dependency parsing',
            'Pre-trained models for 70+ languages'
        ],
        usecase: 'We use spaCy\'s en_core_web_sm model for entity extraction, identifying parties, dates, amounts, and other key information in legal contracts.'
    },
    flask: {
        icon: '🌐',
        title: 'Flask',
        version: '3.0.0',
        description: 'Flask is a lightweight WSGI web application framework in Python. It\'s designed to make getting started quick and easy, with the ability to scale up to complex applications.',
        features: [
            'Lightweight and flexible microframework',
            'Built-in development server and debugger',
            'RESTful request dispatching',
            'Jinja2 templating engine',
            'Extensive extension ecosystem'
        ],
        usecase: 'Flask serves as our web framework, handling HTTP requests, rendering templates, managing user sessions, and connecting frontend to our AI processing backend.'
    },
    pymupdf: {
        icon: '📄',
        title: 'PyMuPDF',
        version: '1.23.8',
        description: 'PyMuPDF (also known as fitz) is a Python binding for MuPDF, a lightweight PDF, XPS, and eBook viewer. It provides fast and accurate PDF text extraction and manipulation.',
        features: [
            'Lightning-fast PDF text extraction',
            'Support for images and metadata',
            'PDF creation and modification',
            'Text search and highlighting',
            'Conversion to other formats'
        ],
        usecase: 'PyMuPDF extracts text from PDF contracts with high accuracy, preserving document structure and handling complex layouts for our analysis pipeline.'
    },
    'python-docx': {
        icon: '📋',
        title: 'python-docx',
        version: '1.1.0',
        description: 'python-docx is a Python library for creating, reading, and updating Microsoft Word (.docx) files. It provides a simple API for working with Word documents programmatically.',
        features: [
            'Read and write .docx files',
            'Extract paragraphs and text',
            'Access document structure',
            'Handle tables and lists',
            'Preserve formatting information'
        ],
        usecase: 'We use python-docx to extract text from Word documents, enabling users to upload contracts in DOCX format for analysis and simplification.'
    },
    sqlalchemy: {
        icon: '💾',
        title: 'SQLAlchemy',
        version: '2.0.36',
        description: 'SQLAlchemy is the Python SQL toolkit and Object-Relational Mapping (ORM) library. It provides a full suite of enterprise-level persistence patterns for database interactions.',
        features: [
            'Powerful ORM with lazy loading',
            'Database-agnostic query generation',
            'Connection pooling and transactions',
            'Migration support with Alembic',
            'Support for SQLite, PostgreSQL, MySQL, etc.'
        ],
        usecase: 'SQLAlchemy manages our SQLite database, storing user accounts, document history, and processing results with efficient queries and data integrity.'
    }
};

// Show Technology Details Modal
function showTechDetails(tech) {
    const modal = document.getElementById('tech-modal');
    const data = techDetails[tech];
    
    if (!data) return;
    
    document.getElementById('modal-icon').textContent = data.icon;
    document.getElementById('modal-title').textContent = data.title;
    document.getElementById('modal-version').textContent = data.version;
    document.getElementById('modal-description').textContent = data.description;
    document.getElementById('modal-usecase').textContent = data.usecase;
    
    // Populate features list
    const featuresList = document.getElementById('modal-features');
    featuresList.innerHTML = '';
    data.features.forEach(feature => {
        const li = document.createElement('li');
        li.textContent = feature;
        featuresList.appendChild(li);
    });
    
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

// Close Technology Modal
function closeTechModal() {
    const modal = document.getElementById('tech-modal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('tech-modal');
    if (event.target === modal) {
        closeTechModal();
    }
}
