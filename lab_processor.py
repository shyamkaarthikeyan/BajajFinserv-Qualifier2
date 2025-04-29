import pytesseract
from PIL import Image
import io
import re
from typing import List, Dict, Any
import numpy as np
import os
import logging
import shutil

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler('lab_report_processor.log')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.addHandler(file_handler)

class LabReportProcessor:
    def __init__(self):
        # Check if Tesseract is in the PATH
        tesseract_path = shutil.which("tesseract")
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        else:
            raise Exception("Tesseract not found in PATH. Please install Tesseract.")
        
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
        
        # Thresholding for better contrast
        image = image.point(lambda x: 0 if x < 200 else 255, '1')
        
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
        # Flexible pattern to match test name, value, reference range, and unit
        patterns = [
            # Pattern 1: Test name, value, range, unit
            r'([A-Za-z\s\(\)]+)\s*([\d\.]+)\s*([\d\.\-]+)\s*-\s*([\d\.\-]+)\s*([A-Za-z\/%]+)?',
            # Pattern 2: Test name, value, unit, range
            r'([A-Za-z\s\(\)]+)\s*([\d\.]+)\s*([A-Za-z\/%]+)\s*([\d\.\-]+)\s*-\s*([\d\.\-]+)',
            # Pattern 3: Test name, value, range
            r'([A-Za-z\s\(\)]+)\s*([\d\.]+)\s*([\d\.\-]+)\s*-\s*([\d\.\-]+)'
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

    def process_batch(self, image_bytes_list: List[bytes]) -> List[List[Dict[str, Any]]]:
        """
        Process a batch of lab report images and extract test information.
        
        Args:
            image_bytes_list: List of raw image bytes
            
        Returns:
            List of lists containing test information for each image
        """
        results = []
        for image_bytes in image_bytes_list:
            results.append(self.process_report(image_bytes))
        return results

    def validate_report_data(self, test_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate extracted test data to ensure proper formatting.
        
        Args:
            test_data: List of test data to validate
            
        Returns:
            List of validated test data
        """
        validated_data = []
        for test in test_data:
            # Check for required fields
            if 'test_name' in test and 'test_value' in test:
                validated_data.append(test)
            else:
                logger.warning("Missing required fields in test data: %s", test)
        return validated_data

    def export_to_csv(self, test_data: List[Dict[str, Any]], output_filepath: str) -> None:
        """
        Export extracted lab test data to a CSV file.
        
        Args:
            test_data: List of test data to export
            output_filepath: Path to the output CSV file
        """
        import csv
        with open(output_filepath, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=["test_name", "test_value", "bio_reference_range", "test_unit", "lab_test_out_of_range"])
            writer.writeheader()
            writer.writerows(test_data)
        logger.info(f"Exported test data to {output_filepath}")

    def filter_out_of_range_tests(self, test_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out lab tests that are out of range.
        
        Args:
            test_data: List of lab test data
            
        Returns:
            List of lab tests that are out of range
        """
        return [test for test in test_data if test.get('lab_test_out_of_range')]

    def process_image_for_preview(self, image_bytes: bytes) -> Image.Image:
        """
        Process an image for a preview before full extraction.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            PIL Image object for preview
        """
        image = Image.open(io.BytesIO(image_bytes))
        image = self._preprocess_image(image)
        return image
