# PDF Event Schedule Extractor

A Python tool to extract event schedules from PDF documents, including both text-based and image-based PDFs using OCR.

## Features

- Extracts event schedules from PDF documents
- Supports both text-based and image-based PDFs (using OCR)
- Identifies dates, times, session names, speakers, and locations
- Outputs results in a clean, tabular format (CSV)
- Handles multi-page schedules and compiles them chronologically

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/pdf-event-extractor.git
   cd pdf-event-extractor
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Tesseract OCR (required for image-based PDFs):
   - **macOS**: `brew install tesseract`
   - **Linux**: `sudo apt-get install tesseract-ocr`
   - **Windows**: Download installer from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)

## Usage

### Basic Usage

```bash
python pdf_event_extractor.py your_event_brochure.pdf -o output.csv
```

### Options

- `-o, --output`: Output CSV file (default: `schedule.csv`)
- `--ocr`: Force OCR processing for all PDFs (useful for image-based PDFs)

### Example

```bash
# Process a single PDF
python pdf_event_extractor.py conference_brochure.pdf -o conference_schedule.csv

# Process multiple PDFs
python pdf_event_extractor.py day1.pdf day2.pdf -o combined_schedule.csv

# Force OCR processing
python pdf_event_extractor.py scanned_brochure.pdf --ocr -o schedule.csv
```

## Output Format

The tool generates a CSV file with the following columns:

- `date`: Date of the event/session
- `time_slots`: Start and end time of the session
- `session_name`: Name of the session, talk, or activity
- `speaker_organizer`: Name of the speaker or organizer
- `location_venue`: Location or venue of the session

## How It Works

1. The tool first attempts to extract text directly from the PDF.
2. If no text is found or the results are insufficient, it falls back to OCR (if enabled).
3. The extracted text is parsed using pattern matching to identify event details.
4. Events are compiled into a structured format and saved as a CSV file.

## Limitations

- The accuracy depends on the quality and layout of the input PDF.
- Complex layouts may require manual post-processing.
- OCR processing is slower than direct text extraction.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
