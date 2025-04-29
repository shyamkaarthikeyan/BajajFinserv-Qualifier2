#!/bin/bash
# Update package list and install Tesseract OCR
apt-get update
apt-get install -y tesseract-ocr

# Install Python dependencies
pip install -r requirements.txt
