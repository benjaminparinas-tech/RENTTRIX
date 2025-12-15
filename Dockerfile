# Use the full Python image (not slim) to avoid missing build tools
FROM python:3.11

# Install the correct system tools for WeasyPrint
# We corrected the package names here (added dashes)
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Set up the workspace
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files
COPY . .

# Collect static files (CSS)
# We use a dummy key because the real one is only needed at runtime
RUN SECRET_KEY=dummy python manage.py collectstatic --noinput --clear

# Start the server on port 10000
CMD ["gunicorn", "rentrix.wsgi", "--bind", "0.0.0.0:10000"]
