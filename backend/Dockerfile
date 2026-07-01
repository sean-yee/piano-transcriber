# 1. Start with a lightweight Python environment
FROM python:3.9-slim

# --- NEW: Install essential OS-level audio and ML libraries! ---
# (The slim image is missing these, which causes basic-pitch and tensorflow to crash)
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 2. Hugging Face Security Requirement: Create a non-root user
# (They don't allow apps to run with master admin privileges for security)
RUN useradd -m -u 1000 user
USER user

# 3. Set up the home directory and working folder
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# 4. Copy your requirements file FIRST and install the libraries
COPY --chown=user requirements.txt .
# --- NEW: Force downgrade NumPy to fix the TFLite Array API crash ---
RUN pip install --no-cache-dir "numpy<2" 
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy your actual code and data into the container
COPY --chown=user . .

# 6. Start the FastAPI server!
# Hugging Face explicitly requires apps to run on port 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]