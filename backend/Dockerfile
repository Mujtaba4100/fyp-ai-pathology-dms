# Use official Python 3.10 slim image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=7860

# Install system dependencies (Tesseract OCR & Poppler for PDF-to-image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user (Required by Hugging Face Spaces: user 1000)
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Set working directory and grant full ownership to user 1000
WORKDIR /app
RUN mkdir -p /app/uploads && chown -R user:user /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend code with user ownership
COPY --chown=user:user . /app

# Switch to non-root user
USER user

# Expose Hugging Face default port
EXPOSE 7860

# Run FastAPI server on port 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
