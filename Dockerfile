# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install Python and other dependencies
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
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Create and activate a virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy the requirements file into the container at /app
COPY requirements.txt /app/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code into the container at /app
COPY . /app/

# Add configuration for Google Earth Engine JSON key
COPY ee-tapaskumarsahoo9090-6245e11643e0.json /app/ee-tapaskumarsahoo9090-6245e11643e0.json
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/ee-tapaskumarsahoo9090-6245e11643e0.json

# Copy the supervisord script file
COPY all_commands.sh /app/all_commands.sh
RUN chmod +x /app/all_commands.sh

# Expose the port the app runs on
EXPOSE 8000

# Run all_commands
CMD ["/app/all_commands.sh"]
