import re
import csv
from typing import List, Dict, Optional, Tuple
from datetime import datetime

def clean_text(text: str) -> str:
    """Clean up text by normalizing whitespace and removing special characters."""
    # Remove special characters but keep letters, numbers, and basic punctuation
    text = re.sub(r'[^\w\s\-\.,:;!?()&]', ' ', text)
    # Normalize whitespace and trim
    text = ' '.join(text.split())
    return text.strip()

def extract_date(line: str) -> Optional[str]:
    """Extract date from a line if it contains a date pattern."""
    date_patterns = [
        r'(?:May|June|July|August|September|October|November|December)\s+\d{1,2}\s*\(Day\s+[12]\)',
        r'DAY\s+[12]',
        r'May\s+1[01](?:st|nd|rd|th)?\s*,\s*2025',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            date_str = match.group(0)
            # Standardize date format
            if 'day 1' in date_str.lower() or 'may 10' in date_str.lower():
                return "May 10, 2025 (Day 1)"
            else:
                return "May 11, 2025 (Day 2)"
    return None

def extract_time_slot(line: str) -> Optional[str]:
    """Extract time slot from a line if it contains a time pattern."""
    time_pattern = r'(\d{1,2}:\d{2}\s*(?:am|pm|a\.m\.|p\.m\.|)\s*-\s*\d{1,2}:\d{2}\s*(?:am|pm|a\.m\.|p\.m\.|))'
    match = re.search(time_pattern, line, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

def extract_session_info(text: str) -> Tuple[str, str, str]:
    """Extract session name, speaker, and location from event text."""
    # Initialize with default values
    session_name = ""
    speaker = "N/A"
    location = "N/A"
    
    # Try to extract session name (look for patterns like "Session X:" or "Session X -")
    session_match = re.search(r'(?:Session|Sess\.?\s*[A-Z0-9]*)[:\s-]+(.+?)(?=\s*(?:Dr\.?|Prof\.?|$))', text, re.IGNORECASE)
    if session_match:
        session_name = session_match.group(1).strip()
    
    # Try to extract speaker (look for Dr./Prof. followed by name)
    speaker_match = re.search(r'(?:(?:Dr|Prof|Professor|Dr\.|Prof\.)\s+[A-Z][a-z]+(?:\s+[A-Z](?:\.|\s|$))?(?:\s+[A-Z][a-z]+)*)', text)
    if speaker_match:
        speaker = speaker_match.group(0).strip()
    
    # Try to extract location (look for keywords like "Venue:", "at", "Location:")
    location_match = re.search(r'(?:Venue|at|venue|Location|location)[: ]+([^\n,]+(?:,[^\n,]+)*)', text, re.IGNORECASE)
    if location_match:
        location = location_match.group(1).strip()
    
    # If no session name was found, use the first 50 chars of the text
    if not session_name:
        session_name = text[:50] + ('...' if len(text) > 50 else '')
    
    return session_name, speaker, location

def process_schedule(input_file: str, output_file: str):
    """Process the schedule from input file and write to output file."""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Split into lines and clean
        lines = [clean_text(line) for line in text.split('\n') if line.strip()]
        
        events = []
        current_date = None
        current_time = None
        current_event = {}
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check for date
            date = extract_date(line)
            if date:
                current_date = date
                i += 1
                continue
                
            # Check for time slot
            time_slot = extract_time_slot(line)
            if time_slot and current_date:
                # Save previous event if exists
                if current_event.get('date') and current_event.get('time'):
                    events.append(current_event)
                
                # Start new event
                current_event = {
                    'date': current_date,
                    'time': time_slot,
                    'session': '',
                    'speaker': 'N/A',
                    'location': 'N/A',
                    'raw_text': ''
                }
                
                # Get event text (next few lines until next time slot or empty line)
                event_lines = []
                i += 1
                while i < len(lines) and not extract_time_slot(lines[i]) and lines[i].strip():
                    event_lines.append(lines[i])
                    i += 1
                
                # Process event text
                if event_lines:
                    event_text = ' '.join(event_lines)
                    session, speaker, location = extract_session_info(event_text)
                    current_event.update({
                        'session': session,
                        'speaker': speaker,
                        'location': location,
                        'raw_text': event_text[:200]  # Store first 200 chars of raw text
                    })
                continue
                
            i += 1
        
        # Add the last event if exists
        if current_event.get('date') and current_event.get('time'):
            events.append(current_event)
        
        # Write to CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['date', 'time', 'session', 'speaker', 'location', 'raw_text']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(events)
            
        print(f"Successfully processed {len(events)} events to {output_file}")
        
        # Print sample output
        print("\nSample of extracted events:")
        for i, event in enumerate(events[:3], 1):
            print(f"\nEvent {i}:")
            print(f"Date: {event['date']}")
            print(f"Time: {event['time']}")
            print(f"Session: {event['session'][:100]}")
            print(f"Speaker: {event['speaker']}")
            print(f"Location: {event['location']}")
            
    except Exception as e:
        print(f"Error processing schedule: {str(e)}")
        raise

if __name__ == "__main__":
    input_file = "extracted_text.txt"
    output_file = "improved_schedule_events.csv"
    
    print("Starting schedule processing...")
    process_schedule(input_file, output_file)
