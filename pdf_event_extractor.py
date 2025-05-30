import re
import pdfplumber
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import pandas as pd
import os

class PDFEventExtractor:
    """
    A class to extract event schedules from PDF documents.
    Supports both text-based and image-based PDFs using OCR.
    """
    
    def __init__(self, use_ocr: bool = False):
        """Initialize the PDF Event Extractor.
        
        Args:
            use_ocr: Whether to use OCR for image-based PDFs
        """
        self.use_ocr = use_ocr
        self.events = []
        self.date_patterns = [
            r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,\s*\d{4})?\b',  # Month Day, Year
            r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',  # MM/DD/YYYY or DD-MM-YYYY
            r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b',  # YYYY-MM-DD
            r'\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)(?:day)?\b',  # Day of week
            r'\b(?:Day\s*\d+)\b',  # Day 1, Day 2, etc.
        ]
        self.time_patterns = [
            r'\b(?:1[0-2]|0?[1-9]):[0-5][0-9]\s*(?:[AaPp][mM]|[Aa]\.?[mM]\.?|[Pp]\.?[mM]\.?)\b',  # 12-hour format
            r'\b(?:[01]?[0-9]|2[0-3]):[0-5][0-9]\b',  # 24-hour format
            r'\b(?:1[0-2]|0?[1-9])(?::[0-5][0-9])?\s*(?:[AaPp][mM]|[Aa]\.?[mM]\.?|[Pp]\.?[mM]\.?)\b',  # 12-hour without minutes
        ]
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text as a string
        """
        if self.use_ocr:
            return self._extract_text_with_ocr(pdf_path)
        else:
            return self._extract_text_direct(pdf_path)
    
    def _extract_text_direct(self, pdf_path: str) -> str:
        """Extract text directly from text-based PDFs."""
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n\n"
        return text
    
    def _extract_text_with_ocr(self, pdf_path: str) -> str:
        """Extract text from image-based PDFs using OCR with improved preprocessing."""
        text = ""
        try:
            # Convert PDF to images with higher DPI for better OCR
            images = convert_from_path(pdf_path, dpi=300)
            
            # Extract text from each image using OCR with custom configuration
            for i, image in enumerate(images):
                # Preprocess the image for better OCR results
                # 1. Convert to grayscale
                image = image.convert('L')
                
                # 2. Increase contrast
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(2.0)  # Increase contrast
                
                # 3. Perform OCR with basic configuration
                config = '--psm 6 --oem 3 -c preserve_interword_spaces=1'
                
                page_text = pytesseract.image_to_string(image, config=config)
                
                # Clean up the extracted text
                page_text = '\n'.join(line.strip() for line in page_text.split('\n') if line.strip())
                text += f"\n\n--- Page {i+1} ---\n{page_text}"
                
        except Exception as e:
            print(f"Error during OCR processing: {e}")
            raise
            
        return text
    
    def parse_events(self, text: str) -> List[Dict]:
        """Parse events from extracted text with improved pattern matching.
        
        Args:
            text: Text extracted from PDF
            
        Returns:
            List of event dictionaries
        """
        # Split text into lines and clean
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        current_date = None
        events = []
        current_event = {}
        
        # Patterns for different components
        date_pattern = re.compile(r'([A-Za-z]+\s+\d+\s*\([^)]+\))', re.IGNORECASE)
        time_pattern = re.compile(r'(\d{1,2}:\d{2}\s*[ap]m)\s*-\s*(\d{1,2}:\d{2}\s*[ap]m)', re.IGNORECASE)
        speaker_pattern = re.compile(r'(?i)(?:dr\.?|prof\.?|professor|presented by|speaker:?|by:?)\s*(.*)')
        location_pattern = re.compile(r'(?i)(?:room|location|venue|hall|theater|lab|place)[: ]*(.*)')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for date patterns (e.g., "May 10 (Day 1)")
            date_match = date_pattern.search(line)
            if date_match:
                current_date = date_match.group(1).strip()
                continue
                
            # Check for time patterns (e.g., "8:00 am - 9:00 am")
            time_match = time_pattern.search(line.lower())
            if time_match:
                # Save current event if exists
                if current_event and any(current_event.values()):
                    events.append(current_event)
                
                # Extract time range
                start_time = time_match.group(1).strip()
                end_time = time_match.group(2).strip()
                time_range = f"{start_time} - {end_time}"
                
                # Extract session name (text after time range)
                session_name = line[time_match.end():].strip()
                
                # Clean up session name
                session_name = re.sub(r'\s+', ' ', session_name)  # Normalize spaces
                session_name = re.sub(r'^[\s\-:]+|[\s\-:]+$', '', session_name)  # Trim dashes/colons
                
                current_event = {
                    'date': current_date or 'N/A',
                    'time_slots': time_range,
                    'session_name': session_name or 'N/A',
                    'speaker_organizer': 'N/A',
                    'location_venue': 'N/A'
                }
                continue
                
            # Process current event if exists
            if not current_event:
                continue
                
            # Check for speaker information
            speaker_match = speaker_pattern.search(line)
            if speaker_match:
                speaker = speaker_match.group(1).strip()
                if speaker and speaker != 'N/A':
                    current_event['speaker_organizer'] = speaker
                continue
                
            # Check for location information
            location_match = location_pattern.search(line)
            if location_match:
                location = location_match.group(1).strip()
                if location and location != 'N/A':
                    current_event['location_venue'] = location
                continue
                
            # If line doesn't match any pattern, it might be a continuation of session name or speaker
            if current_event['session_name'] == 'N/A':
                current_event['session_name'] = line
            elif current_event['speaker_organizer'] == 'N/A' and not any(keyword in line.lower() for keyword in ['room', 'location', 'venue']):
                current_event['speaker_organizer'] = line
        
        # Add the last event if it exists
        if current_event and any(current_event.values()):
            events.append(current_event)
        
        # Post-process the extracted events
        for event in events:
            # Clean up session names
            if event['session_name'] != 'N/A':
                event['session_name'] = re.sub(r'\s+', ' ', event['session_name']).strip()
                event['session_name'] = re.sub(r'^[\s\-:]+|[\s\-:]+$', '', event['session_name'])
                
            # Clean up speaker/organizer
            if event['speaker_organizer'] != 'N/A':
                event['speaker_organizer'] = re.sub(r'\s+', ' ', event['speaker_organizer']).strip()
                event['speaker_organizer'] = re.sub(r'^[,\-\.\s]+|[,\-\.\s]+$', '', event['speaker_organizer'])
            
            # Clean up location
            if event['location_venue'] != 'N/A':
                event['location_venue'] = re.sub(r'\s+', ' ', event['location_venue']).strip()
        
        return events
    
    def process_pdf(self, pdf_path: str) -> pd.DataFrame:
        """Process a PDF file and return events as a DataFrame.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            DataFrame containing extracted events
        """
        print(f"Processing {pdf_path}...")
        
        # First try direct text extraction
        try:
            text = self._extract_text_direct(pdf_path)
            events = self.parse_events(text)
            
            # If no events found, try with OCR
            if not events and not self.use_ocr:
                print("No events found with direct text extraction. Trying OCR...")
                self.use_ocr = True
                text = self._extract_text_with_ocr(pdf_path)
                events = self.parse_events(text)
                
        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
            if not self.use_ocr:
                print("Trying with OCR...")
                self.use_ocr = True
                try:
                    text = self._extract_text_with_ocr(pdf_path)
                    events = self.parse_events(text)
                except Exception as ocr_error:
                    print(f"OCR processing failed: {ocr_error}")
                    events = []
            else:
                events = []
        
        return pd.DataFrame(events)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract event schedules from PDF files.')
    parser.add_argument('pdf_files', nargs='+', help='PDF files to process')
    parser.add_argument('--output', '-o', default='schedule.csv', 
                       help='Output CSV file (default: schedule.csv)')
    parser.add_argument('--ocr', action='store_true', 
                       help='Use OCR for image-based PDFs')
    
    args = parser.parse_args()
    
    extractor = PDFEventExtractor(use_ocr=args.ocr)
    
    all_events = []
    for pdf_file in args.pdf_files:
        if not os.path.exists(pdf_file):
            print(f"Error: File not found: {pdf_file}")
            continue
            
        df = extractor.process_pdf(pdf_file)
        if not df.empty:
            all_events.append(df)
    
    if all_events:
        result_df = pd.concat(all_events, ignore_index=True)
        result_df.to_csv(args.output, index=False)
        print(f"Schedule saved to {args.output}")
        print("\nExtracted Schedule:")
        print(result_df.to_string(index=False))
    else:
        print("No events were extracted from the provided PDFs.")


if __name__ == "__main__":
    main()
