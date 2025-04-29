#!/bin/bash

# Update the package list
apt-get update

# Install Tesseract OCR (and dependencies)
apt-get install -y tesseract-ocr

# Install other dependencies from requirements.txt
pip install --no-cache-dir -r requirements.txt
# Verify the Tesseract installation
tesseract --version
