# Use an official Python runtime as a parent image (slim reduces image size)
FROM python:3.11-slim

# Set environment variables
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files
# PYTHONUNBUFFERED: Ensures console output isn't buffered (better for Docker logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:$PATH"

# Create a non-root user and group for security
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Set the working directory inside the container
WORKDIR /app

# Copy requirements and set ownership
COPY --chown=appuser:appgroup requirements.txt .

# Switch to non-root user before installing packages
USER 10001

# Install dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy application source code
COPY --chown=appuser:appgroup . .

# Document the port the container will use
EXPOSE 5001

# Run the application securely using Gunicorn (if added) or default python
CMD ["python", "app.py"]
