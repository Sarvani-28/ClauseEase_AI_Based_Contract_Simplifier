# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Prevent Python from writing pyc files and buffer stdio
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies if needed (e.g., for PyMuPDF)
# RUN apt-get update && apt-get install -y --no-install-recommends build-essential libmu*-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Download NLTK Data ---
RUN python -m nltk.downloader -d /usr/share/nltk_data punkt stopwords wordnet
# --- Set NLTK_DATA environment variable ---
ENV NLTK_DATA=/usr/share/nltk_data

# --- Download SpaCy Model (if used by your components) ---
RUN python -m spacy download en_core_web_sm

# Copy the rest of the application code
COPY . .

# --- Pre-load AI Models (Optional but Recommended) ---
# Ensure you have a script like src/preload_models.py if you uncomment this
# RUN python src/preload_models.py

# Make port 5000 available
EXPOSE 5000

# Run app.py using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "src.app:app"]