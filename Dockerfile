# Base Python image
FROM python:3.10-slim

# Prevent Python from writing pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory for Master Dashboard project
WORKDIR /app

# ---------------------------------------------------------
# Install required system packages
# (kept from your existing Dockerfile)
# ---------------------------------------------------------
RUN apt-get update && \
    apt-get install -y \
    python3 \
    python3-venv \
    python3-pip \
    mesa-utils \
    libasound2-dev \
    gdal-bin \
    libgdal-dev \
    supervisor && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip && \
    rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------
# Create and activate a virtual environment
# ---------------------------------------------------------
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# ---------------------------------------------------------
# Copy and install dependencies for Master Dashboard backend
# (path is relative to build context: /home/vertoxlabs)
# ---------------------------------------------------------
COPY Master_Dashboard/requirements.txt /app/requirements.txt

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# ---------------------------------------------------------
# Copy Master Dashboard source code
# ---------------------------------------------------------
COPY Master_Dashboard/ /app/

# ---------------------------------------------------------
# Copy Common Login backend source code
# (second Django backend, no Dockerfile needed there)
# ---------------------------------------------------------
COPY Commonlogin_new_version_2026/ /commonlogin/

# ---------------------------------------------------------
# Install dependencies for Common Login backend
# ---------------------------------------------------------
RUN pip install --no-cache-dir -r /commonlogin/requirements.txt

# ---------------------------------------------------------
# Make startup script executable
# ---------------------------------------------------------
RUN chmod +x /app/all_commands.sh

# ---------------------------------------------------------
# Expose both backend ports
#   8000 -> Master Dashboard backend
#   8001 -> Common Login backend
# ---------------------------------------------------------
EXPOSE 8000 8001

# ---------------------------------------------------------
# Start all backend services using your shell script
# ---------------------------------------------------------
CMD ["/app/all_commands.sh"]
