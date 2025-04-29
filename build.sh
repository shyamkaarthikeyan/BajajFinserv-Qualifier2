#!/bin/bash
# Update package lists
apt-get update

# Install Tesseract OCR
apt-get install -y tesseract-ocr
# Install dependencies from requirements.txt
pip install --no-cache-dir -r requirements.txt
# Print Tesseract version for verification
tesseract --version
