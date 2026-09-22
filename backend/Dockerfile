# ================================================================
# Backend Dockerfile — FastAPI + Whisper + BLIP
# ================================================================
# Uses Python 3.11 slim base.
# FFmpeg is installed from the Debian package manager.
# Whisper + BLIP models are downloaded on first run (or restored
# from the huggingface_cache volume on subsequent runs).
# ================================================================

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies:
# - ffmpeg: required by Whisper, MoviePy, and our video renderer
# - libsm6, libxext6, libgl1: required by OpenCV
# - git: required by some HuggingFace installers
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer caching — only re-installs if requirements change)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for file storage
RUN mkdir -p uploads outputs temp

# Expose the FastAPI port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
