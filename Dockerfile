# Base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install OS dependencies
RUN apt-get update && apt-get install -y ffmpeg git && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Expose Streamlit port
EXPOSE 7860

# Launch Streamlit
CMD ["streamlit", "run", "main.py", "--server.port=7860", "--server.address=0.0.0.0"]
