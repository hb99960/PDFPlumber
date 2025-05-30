import os
import re
import torch
import pandas as pd
from transformers import pipeline
from typing import List, Dict, Optional
import pdfplumber
from tqdm import tqdm

class AIEventExtractor:
    def __init__(self, model_name="deepset/roberta-base-squad2"):
        """
        Initialize the AI Event Extractor with a question-answering model.
        
        Args:
            model_name: Name of the pre-trained model to use for question answering
        """
        self.device = 0 if torch.cuda.is_available() else -1  # Use GPU if available
        self.nlp = pipeline(
            "question-answering",
            model=model_name,
            device=self.device
        )
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from a PDF file using OCR for better accuracy."""
        from pdf2image import convert_from_path
        from PIL import Image
        import pytesseract
        
        text_parts = []
        
        try:
            # Convert PDF to images with higher DPI for better OCR
            images = convert_from_path(pdf_path, dpi=300)
            
            for i, image in enumerate(tqdm(images, desc="Processing PDF pages")):
                try:
                    # Preprocess image for better OCR
                    # 1. Convert to grayscale
                    image = image.convert('L')
                    
                    # 2. Enhance contrast
                    from PIL import ImageEnhance
                    enhancer = ImageEnhance.Contrast(image)
                    image = enhancer.enhance(2.0)
                    
                    # 3. Perform OCR with custom configuration
                    config = '--psm 6 --oem 3 -c preserve_interword_spaces=1'
                    page_text = pytesseract.image_to_string(image, config=config)
                    
                    if page_text.strip():
                        text_parts.append(page_text.strip())
                        
                except Exception as e:
                    print(f"\nError processing page {i+1}: {str(e)}")
                    continue
                    
            return "\n\n".join(text_parts)
            
        except Exception as e:
            print(f"\nError in PDF to image conversion: {str(e)}")
            # Fall back to pdfplumber if pdf2image fails
            print("Falling back to direct text extraction...")
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
            return "\n\n".join(text_parts)
    
    def extract_events(self, text: str) -> List[Dict]:
        """
        Extract events from text using pattern matching and AI-powered question answering.
        
        Args:
            text: Raw text extracted from the PDF
            
        Returns:
            List of dictionaries containing event information
        """
        # First, try to split by day headers
        day_sections = re.split(r'(May 1[01] \(Day [12]\)\s*\n)', text)
        
        # If no day sections found, try a different approach
        if len(day_sections) <= 1:
            day_sections = re.split(r'(DAY [12]\s*\n)', text)
        
        # If still no luck, try to split by time patterns
        if len(day_sections) <= 1:
            return self._extract_events_by_time_patterns(text)
        
        # Process each day section
        all_events = []
        current_date = ""
        
        for i in range(1, len(day_sections), 2):
            if i < len(day_sections):
                # The day header is in the previous element
                day_header = day_sections[i-1].strip()
                day_content = day_sections[i]
                
                # Extract date from day header
                date_match = re.search(r'(May 1[01])', day_header)
                if date_match:
                    current_date = date_match.group(1) + " (" + day_header.split('(')[-1].strip()
                
                # Extract events from day content
                day_events = self._extract_events_from_day(day_content, current_date)
                all_events.extend(day_events)
        
        return all_events
    
    def _extract_events_from_day(self, day_content: str, current_date: str) -> List[Dict]:
        """Extract events from a single day's content."""
        # Clean up the day content
        day_content = '\n'.join(line.strip() for line in day_content.split('\n') if line.strip())
        
        # Split into time slots using a more robust pattern
        time_pattern = r'(\d{1,2}:\d{2}\s*(?:am|pm|a\.m\.|p\.m\.)?\s*-\s*\d{1,2}:\d{2}\s*(?:am|pm|a\.m\.|p\.m\.)?)'
        parts = re.split(f'({time_pattern})', day_content)
        
        events = []
        
        for i in range(1, len(parts), 2):
            if i + 1 >= len(parts):
                continue
                
            time_slot = parts[i].strip()
            event_text = parts[i+1].strip()
            
            # Skip if time slot is not in the expected format
            if not re.match(r'\d{1,2}:\d{2}\s*(?:am|pm|a\.m\.|p\.m\.)?\s*-\s*\d{1,2}:\d{2}\s*(?:am|pm|a\.m\.|p\.m\.)?', time_slot, re.IGNORECASE):
                continue
                
            # Clean up the event text
            event_text = ' '.join(line.strip() for line in event_text.split('\n') if line.strip())
            
            # Try to extract session name and speaker
            session_name = self._extract_session_name(event_text)
            speaker = self._extract_speaker(event_text)
            location = self._extract_location(event_text)
            
            event = {
                'date': current_date,
                'time': time_slot,
                'session_name': session_name or "N/A",
                'speaker': speaker or "N/A",
                'location': location or "N/A",
                'raw_text': event_text
            }
            events.append(event)
        
        return events
    
    def _extract_session_name(self, text: str) -> str:
        """Extract session name from event text."""
        # Look for patterns like "Session X:" or lines in all caps
        session_match = re.search(r'Session\s+[A-Z0-9]+[\s:]+(.+?)(?=\n|$)', text, re.IGNORECASE)
        if session_match:
            return session_match.group(1).strip()
            
        # Look for lines that might be session names
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if lines and len(lines[0].split()) < 10:  # Assume first line with few words is the title
            return lines[0]
            
        return ""
    
    def _extract_speaker(self, text: str) -> str:
        """Extract speaker/organizer from event text."""
        # Look for patterns like "Dr. Name" or "Name, Title"
        speaker_match = re.search(r'(?:Dr\.?|Prof\.?)\s+[A-Z][a-z]+(?:\s+[A-Z]\.?)?(?:\s+[A-Z][a-z]+)+', text)
        if speaker_match:
            return speaker_match.group(0).strip()
            
        return ""
    
    def _extract_location(self, text: str) -> str:
        """Extract location from event text."""
        # Look for location patterns like "Venue: Location" or "at Location"
        location_match = re.search(r'(?:Venue|at|venue)[: ]+([^\n]+)', text, re.IGNORECASE)
        if location_match:
            return location_match.group(1).strip()
            
        return ""
    
    def _extract_events_by_time_patterns(self, text: str) -> List[Dict]:
        """Fallback method to extract events using time patterns."""
        # First, try to find day sections
        day_sections = re.split(r'(May 1[01]\s*\(Day [12]\)|DAY [12]\b)', text, flags=re.IGNORECASE)
        
        if len(day_sections) <= 1:
            # If no day sections found, try to process as a single day
            return self._process_single_day_events(text, "May 10 (Day 1)")
        
        # Process each day section
        events = []
        current_date = ""
        
        for i in range(1, len(day_sections), 2):
            if i < len(day_sections):
                # The day header is in the previous element
                day_header = day_sections[i-1].strip()
                day_content = day_sections[i]
                
                # Extract date from day header
                date_match = re.search(r'(May 1[01]\s*\(Day [12]\)|DAY [12]\b)', day_header, re.IGNORECASE)
                if date_match:
                    date_str = date_match.group(1)
                    # Standardize the date format
                    if 'day' in date_str.lower():
                        day_num = '1' if '1' in date_str else '2'
                        current_date = f"May {10 + int(day_num) - 1} (Day {day_num})"
                    else:
                        current_date = date_str
                
                # Process events for this day
                day_events = self._process_single_day_events(day_content, current_date)
                events.extend(day_events)
        
        return events
    
    def _process_single_day_events(self, text: str, current_date: str) -> List[Dict]:
        """Process events for a single day's content."""
        # Split by time patterns
        time_pattern = r'(\d{1,2}:\d{2}\s*(?:am|pm|a\.m\.|p\.m\.)?\s*-\s*\d{1,2}:\d{2}\s*(?:am|pm|a\.m\.|p\.m\.)?)'
        parts = re.split(f'({time_pattern})', text)
        
        events = []
        
        for i in range(1, len(parts), 2):
            if i + 1 >= len(parts):
                continue
                
            time_slot = parts[i].strip()
            event_text = parts[i+1].strip()
            
            # Skip if time slot is not in the expected format
            if not re.match(r'\d{1,2}:\d{2}\s*(?:am|pm|a\.m\.|p\.m\.)?\s*-\s*\d{1,2}:\d{2}\s*(?:am|pm|a\.m\.|p\.m\.)?', time_slot, re.IGNORECASE):
                continue
            
            # Clean up the event text
            event_text = ' '.join(line.strip() for line in event_text.split('\n') if line.strip())
            
            # Extract session info
            session_name = self._extract_session_name(event_text)
            speaker = self._extract_speaker(event_text)
            location = self._extract_location(event_text)
            
            event = {
                'date': current_date,
                'time': time_slot,
                'session_name': session_name or "N/A",
                'speaker': speaker or "N/A",
                'location': location or "N/A",
                'raw_text': event_text
            }
            events.append(event)
        
        return events
        
        return events
    
    def _extract_info(self, context: str, question: str) -> str:
        """Extract information using the QA model."""
        try:
            result = self.nlp(question=question, context=context)
            return result['answer'].strip()
        except:
            return "N/A"
    
    def _split_into_sections(self, text: str) -> List[str]:
        """
        Split text into sections that likely contain individual events.
        Improved to handle schedule tables and multi-line entries.
        """
        # First, try to split by time patterns (e.g., "10:45 am - 11:00 am")
        time_pattern = r'\b(?:1[0-2]|0?[1-9]):[0-5][0-9]\s*(?:am|pm)\s*-\s*(?:1[0-2]|0?[1-9]):[0-5][0-9]\s*(?:am|pm)\b'
        
        # Split by time patterns but keep the delimiter
        parts = re.split(f'({time_pattern})', text)
        
        # Group time with its corresponding content
        sections = []
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                section = parts[i] + ' ' + parts[i+1]
                sections.append(section.strip())
        
        # If no time-based splits, fall back to double newline
        if not sections:
            sections = re.split(r'\n\s*\n', text)
        
        # Filter out very short sections and clean up
        return [s.strip() for s in sections if len(s.strip()) > 20]
    
    def process_pdf(self, pdf_path: str, output_csv: str = "ai_events_output.csv"):
        """
        Process a PDF file and save extracted events to a CSV.
        
        Args:
            pdf_path: Path to the input PDF file
            output_csv: Path to save the output CSV file
        """
        print(f"Processing {pdf_path}...")
        
        try:
            # Extract text from PDF
            text = self.extract_text_from_pdf(pdf_path)
            
            # Save extracted text for debugging
            with open('extracted_text.txt', 'w', encoding='utf-8') as f:
                f.write(text)
            
            # Extract events using AI
            events = self.extract_events(text)
            
            # Convert to DataFrame and save
            if events:
                df = pd.DataFrame(events)
                
                # Clean up the data
                df = df.replace({'N/A': '', '': 'N/A'})
                df = df[['date', 'time', 'session_name', 'speaker', 'location', 'raw_text']]
                
                # Save to CSV
                df.to_csv(output_csv, index=False)
                
                # Print summary
                print(f"\nExtracted {len(events)} events to {output_csv}")
                print("\nSample of extracted events:")
                print(df.head().to_string())
            else:
                print("No events were extracted from the PDF.")
                print("\nExtracted text has been saved to 'extracted_text.txt' for debugging.")
                
        except Exception as e:
            print(f"\nError processing PDF: {str(e)}")
            if 'text' in locals():
                with open('error_extracted_text.txt', 'w', encoding='utf-8') as f:
                    f.write(text)
                print("Extracted text has been saved to 'error_extracted_text.txt' for debugging.")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract events from PDF using AI')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('-o', '--output', default='ai_events_output.csv',
                      help='Output CSV file path (default: ai_events_output.csv)')
    
    args = parser.parse_args()
    
    extractor = AIEventExtractor()
    extractor.process_pdf(args.pdf_path, args.output)
