# Use Ubuntu 22.04 (Jammy) as base image
FROM ubuntu:22.04

# Prevent timezone prompt during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install Python 3.11 and other dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3.11 \
        python3-pip \
        python3.11-venv \
        wget \
        xvfb \
        xfonts-75dpi \
        xfonts-base \
        libfontconfig1 \
        libxrender1 \
        libxext6 \
        libssl3 \
        libffi-dev \
        fontconfig \
        libjpeg-turbo8 \
        ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Download and install wkhtmltopdf
RUN wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_amd64.deb && \
    apt-get update && \
    apt-get install -y ./wkhtmltox_0.12.6.1-2.jammy_amd64.deb && \
    rm wkhtmltox_0.12.6.1-2.jammy_amd64.deb && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create symlink to maintain compatibility with existing code
RUN ln -sf /usr/local/bin/wkhtmltopdf /usr/bin/wkhtmltopdf

# Verify wkhtmltopdf installation
RUN wkhtmltopdf --version

# Set the working directory
WORKDIR /app

# Create and activate virtual environment
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Copy the .env file
COPY .env .env

# Expose the port the app runs on
EXPOSE 8080

# Set environment variable to enable EC2 metadata access
ENV AWS_EC2_METADATA_DISABLED=false

# Define the default command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]