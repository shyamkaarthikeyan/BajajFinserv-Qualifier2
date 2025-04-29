#!/bin/bash
# Install Tesseract for OCR
apt-get update && apt-get install -y tesseract-ocr
pip install -r requirements.txt
