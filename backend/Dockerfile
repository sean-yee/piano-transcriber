# 1. Use a lightweight Python base image
FROM python:3.11-slim

RUN apt-get update && apt-get install -y wget

# 2. Install FFmpeg (CRITICAL for librosa to process mp3/wav files)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 3. Set the working directory inside the container
WORKDIR /app

# 4. Copy the requirements file and install the Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your backend code and the ML model into the container
COPY main.py .
COPY hand_classifier.pkl .

# 6. Expose the port FastAPI runs on
EXPOSE 8000

# 7. The command to spin up the server when the container starts
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]