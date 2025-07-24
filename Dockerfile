FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including pipenv
RUN apt-get update && \
    apt-get install -y build-essential libpq-dev postgresql-client curl git && \
    pip install --upgrade pip pipenv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy Pipfile and Pipfile.lock first (for better Docker layer caching)
COPY Pipfile Pipfile.lock ./

# Install Python dependencies using pipenv
# --system installs packages to system python (not in virtual env)
# --deploy ensures Pipfile.lock is up to date with Pipfile
RUN pipenv install --system --deploy

# Copy application code
COPY . .

# Make entrypoint executable
RUN chmod +x /app/django-entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run the entrypoint script and then start the server
CMD ["/app/django-entrypoint.sh"]