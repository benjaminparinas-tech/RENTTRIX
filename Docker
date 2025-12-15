# 1. Use Python 3.11 as the base
FROM python:3.11-slim

# 2. Install the system tools needed for WeasyPrint (PDFs)
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    python3-cffi \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# 3. Set up the working folder
WORKDIR /app

# 4. Copy and install your Python libraries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your code
COPY . .

# 6. Collect static files (CSS)
# We use a dummy key here just for the build process
RUN SECRET_KEY=dummy python manage.py collectstatic --noinput --clear

# 7. Start the server
# RENTRIX NOTE: We bind to port 10000 which Render expects
CMD ["gunicorn", "rentrix.wsgi", "--bind", "0.0.0.0:10000"]
