FROM python:3.10-slim

WORKDIR /app

# Install dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Debug: Print directory contents and Python path
RUN ls -la && python -c "import sys; print('Python path:', sys.path)"

# Start the app with error logging
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload 2>&1 | tee /dev/stderr"]
