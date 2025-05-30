from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def create_pdf(text_file, pdf_file):
    # Create a PDF document
    c = canvas.Canvas(pdf_file, pagesize=letter)
    width, height = letter
    
    # Set font and size
    c.setFont("Helvetica", 12)
    
    # Read the text file and write to PDF
    with open(text_file, 'r') as file:
        y = 750  # Start near the top of the page
        for line in file:
            if y < 50:  # Check if we need a new page
                c.showPage()
                y = 750
                c.setFont("Helvetica", 12)
            c.drawString(50, y, line.strip())
            y -= 15  # Move down for the next line
    
    # Save the PDF
    c.save()
    print(f"PDF created: {pdf_file}")

if __name__ == "__main__":
    create_pdf("test_event_brochure.txt", "test_event_brochure.pdf")
