#!/usr/bin/env bash
# Build script for Render deployment

# Install system dependencies for WeasyPrint
apt-get update
apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info

# Install Python dependencies
pip install -r requirements.txt
