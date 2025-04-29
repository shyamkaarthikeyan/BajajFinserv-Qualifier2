import pytesseract
from PIL import Image
import io
import re
from typing import List, Dict, Any
import numpy as np
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LabReportProcessor:
    def __init__(self):
        # Set the Tesseract path for Linux (Render environment)
        pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
        
        # Verify Tesseract is accessible
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            raise Exception(f"Tesseract initialization failed: {str(e)}")

    def process_report(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Process the lab report image and extract test information.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            List of dictionaries containing test information
        """
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Preprocess image
            image = self._preprocess_image(image)
            
            # Perform OCR with improved configuration
            text = pytesseract.image_to_string(image, config='--psm 6 --oem 3')
            
            # Log extracted text for debugging
            logger.info("Extracted text:\n%s", text)
            
            # Process the extracted text
            return self._extract_lab_tests(text)
        except Exception as e:
            logger.error("Error processing image: %s", str(e))
            raise Exception(f"Error processing image: {str(e)}")
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess the image to improve OCR accuracy.
        
        Args:
            image: PIL Image to preprocess
            
        Returns:
            Preprocessed PIL Image
        """
        # Convert to grayscale
        image = image.convert('L')
        
        # Increase contrast
        image = image.point(lambda x: 0 if x < 128 else 255, '1')
        
        return image
    
    def _extract_lab_tests(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract lab test information from OCR text.
        
        Args:
            text: OCR extracted text
            
        Returns:
            List of dictionaries containing test information
        """
        # Split text into lines
        lines = text.split('\n')
        
        lab_tests = []
        current_test = None
        
        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue
                
            # Log each line for debugging
            logger.debug("Processing line: %s", line)
                
            # Try to extract test name, value, and reference range
            test_info = self._parse_test_line(line)
            
            if test_info:
                logger.info("Found test: %s", test_info)
                if current_test:
                    lab_tests.append(current_test)
                current_test = test_info
            elif current_test:
                # Try to add more information to current test
                self._update_test_info(current_test, line)
        
        if current_test:
            lab_tests.append(current_test)
            
        return lab_tests
    
    def _parse_test_line(self, line: str) -> Dict[str, Any]:
        """
        Parse a line to extract test information.
        
        Args:
            line: Text line to parse
            
        Returns:
            Dictionary containing test information or None if no test found
        """
        # More flexible pattern to match test name, value, reference range, and unit
        patterns = [
            # Pattern 1: Test name, value, range, unit
            r'([A-Za-z\s\(\)]+)\s*([\d\.]+)\s*([\d\.]+)\s*-\s*([\d\.]+)\s*([A-Za-z\/%]+)',
            # Pattern 2: Test name, value, unit, range
            r'([A-Za-z\s\(\)]+)\s*([\d\.]+)\s*([A-Za-z\/%]+)\s*([\d\.]+)\s*-\s*([\d\.]+)',
            # Pattern 3: Test name, value, range
            r'([A-Za-z\s\(\)]+)\s*([\d\.]+)\s*([\d\.]+)\s*-\s*([\d\.]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                try:
                    if len(match.groups()) == 5:
                        # Pattern 1 or 2
                        test_name = match.group(1).strip()
                        value = float(match.group(2))
                        if pattern == patterns[0]:
                            ref_min = float(match.group(3))
                            ref_max = float(match.group(4))
                            unit = match.group(5).strip()
                        else:
                            unit = match.group(3).strip()
                            ref_min = float(match.group(4))
                            ref_max = float(match.group(5))
                    else:
                        # Pattern 3
                        test_name = match.group(1).strip()
                        value = float(match.group(2))
                        ref_min = float(match.group(3))
                        ref_max = float(match.group(4))
                        unit = ""  # No unit in this pattern
                    
                    return {
                        "test_name": test_name,
                        "test_value": str(value),
                        "bio_reference_range": f"{ref_min}-{ref_max}",
                        "test_unit": unit,
                        "lab_test_out_of_range": not (ref_min <= value <= ref_max)
                    }
                except (ValueError, IndexError) as e:
                    logger.warning("Error parsing line '%s': %s", line, str(e))
                    continue
        
        return None
    
    def _update_test_info(self, test: Dict[str, Any], line: str) -> None:
        """
        Update test information with additional details from the line.
        
        Args:
            test: Current test dictionary
            line: Additional line of text
        """
        # Try to extract unit if not already present
        if not test.get("test_unit"):
            unit_match = re.search(r'([A-Za-z\/%]+)$', line)
            if unit_match:
                test["test_unit"] = unit_match.group(1).strip()
