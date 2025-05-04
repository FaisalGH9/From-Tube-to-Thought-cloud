# Use an official Python image
FROM python:3.10-slim

# Install ffmpeg and other dependencies
RUN apt-get update && apt-get install -y ffmpeg git curl && apt-get clean

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Install yt-dlp
RUN pip install yt-dlp

# Copy the rest of the code
COPY . .

# Streamlit port config (Cloud Run uses $PORT env)
ENV PORT=8080
EXPOSE 8080

# Run the app
CMD ["streamlit", "run", "main.py", "--server.port=8080", "--server.enableCORS=false"]
