import re
import csv
from typing import List, Dict

def clean_text(text: str) -> str:
    """Clean up text by normalizing whitespace and removing extra characters."""
    # Remove special characters and normalize whitespace
    text = re.sub(r'[^\w\s.,:;!?\-()]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def is_schedule_section(line: str) -> bool:
    """Check if the line is part of the schedule section."""
    schedule_keywords = [
        'session', 'program', 'schedule', 'agenda', 'time', 
        'speaker', 'presentation', 'break', 'lunch', 'dinner',
        'registration', 'welcome', 'inauguration', 'keynote'
    ]
    line_lower = line.lower()
    return any(keyword in line_lower for keyword in schedule_keywords)

def extract_events(text: str) -> List[Dict]:
    """Extract events from the schedule text."""
    events = []
    current_date = ""
    in_schedule_section = False
    
    # Split the text into lines and clean them
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if we're in the schedule section
        if not in_schedule_section and is_schedule_section(line):
            in_schedule_section = True
        
        # Skip if not in schedule section
        if not in_schedule_section:
            i += 1
            continue
            
        # Check for date headers (e.g., "May 10 (Day 1)" or "DAY 1")
        date_match = re.search(r'(?:May\s+1[01]\s*\(Day\s+[12]\)|DAY\s+[12])', line, re.IGNORECASE)
        if date_match:
            date_str = date_match.group(0)
            if 'day 1' in date_str.lower() or 'may 10' in date_str.lower():
                current_date = "May 10, 2025 (Day 1)"
            else:
                current_date = "May 11, 2025 (Day 2)"
            i += 1
            continue
        
        # Check for time slots (e.g., "8:00 am - 9:00 am")
        time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:am|pm|a\.m\.|p\.m\.)?\s*-\s*\d{1,2}:\d{2}\s*(?:am|pm|a\.m\.|p\.m\.)?)', line, re.IGNORECASE)
        if time_match and current_date:
            time_slot = time_match.group(1).strip()
            
            # Get the event text (next few lines until next time slot or empty line)
            event_lines = []
            i += 1
            while i < len(lines) and not re.match(r'\d{1,2}:\d{2}\s*(?:am|pm|a\.m\.|p\.m\.)?\s*-\s*\d{1,2}:\d{2}\s*(?:am|pm|a\.m\.|p\.m\.)?', lines[i], re.IGNORECASE):
                if lines[i].strip() and not re.match(r'^\s*$', lines[i]):
                    event_lines.append(lines[i].strip())
                i += 1
            
            # Skip if no event text found
            if not event_lines:
                i += 1
                continue
                
            event_text = ' '.join(event_lines)
            
            # Try to extract session and speaker
            session_name = ""
            speaker = ""
            location = ""
            
            # Look for session pattern (e.g., "Session 1:" or "Session A:")
            session_match = re.search(r'(?:Session|Sess|Sess\.|Sess\s*[A-Z0-9]+)[\s:]+(.+?)(?:\.|$|\n)', event_text, re.IGNORECASE)
            if session_match:
                session_name = session_match.group(1).strip()
            
            # Look for speaker pattern (Dr. Name or Name, Title)
            speaker_match = re.search(r'(?:(?:Dr|Prof|Professor|Dr\.|Prof\.)\s+[A-Z][a-z]+(?:\s+[A-Z]\.?)?(?:\s+[A-Z][a-z]+)+)', event_text)
            if speaker_match:
                speaker = speaker_match.group(0).strip()
            
            # If no session name found, use first line as session name
            if not session_name and event_lines:
                session_name = event_lines[0].strip()
                # Clean up session name
                session_name = re.sub(r'^[^a-zA-Z0-9]+', '', session_name)
                session_name = re.sub(r'[^\w\s]', ' ', session_name)
                session_name = ' '.join(session_name.split())
            
            # Look for location (if any)
            location_match = re.search(r'(?:Venue|at|venue|Location|location)[: ]+([^\n,]+(?:,[^\n,]+)*)', event_text, re.IGNORECASE)
            if location_match:
                location = location_match.group(1).strip()
            
            # Clean up the data
            session_name = clean_text(session_name)[:200]  # Limit length
            speaker = clean_text(speaker)[:100]  # Limit length
            location = clean_text(location)[:100]  # Limit length
            
            # Skip if it's just a break or similar
            if any(x in session_name.lower() for x in ['break', 'lunch', 'dinner', 'tea', 'coffee', 'registration']):
                session_name = f"{session_name} ({time_slot})"
            
            events.append({
                'date': current_date,
                'time': time_slot,
                'session_name': session_name or "N/A",
                'speaker': speaker or "N/A",
                'location': location or "N/A",
                'raw_text': clean_text(event_text)[:500]  # Limit raw text length
            })
        else:
            i += 1
    
    return events

def main():
    input_file = "extracted_text.txt"
    output_file = "schedule_events.csv"
    
    try:
        print("Reading extracted text...")
        # Read the extracted text
        with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
        
        print("Extracting events...")
        # Extract events
        events = extract_events(text)
        
        # Write to CSV
        if events:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['date', 'time', 'session_name', 'speaker', 'location', 'raw_text'])
                writer.writeheader()
                writer.writerows(events)
            
            print(f"\nSuccessfully extracted {len(events)} events to {output_file}")
            print("\nSample of extracted events:")
            for i, event in enumerate(events[:5], 1):
                print(f"\nEvent {i}:")
                print(f"Date: {event['date']}")
                print(f"Time: {event['time']}")
                print(f"Session: {event['session_name']}")
                print(f"Speaker: {event['speaker']}")
                print(f"Location: {event['location']}")
                print(f"Details: {event['raw_text'][:150]}...")
                
            print(f"\nFull schedule has been saved to: {output_file}")
        else:
            print("No events were extracted from the text.")
    
    except Exception as e:
        import traceback
        print(f"An error occurred: {str(e)}")
        print("\nStack trace:")
        traceback.print_exc()

if __name__ == "__main__":
    main()
