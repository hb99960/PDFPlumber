from fpdf import FPDF

def create_pdf(input_file, output_file):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Read the text file
    with open(input_file, 'r') as file:
        for line in file:
            # Add each line to the PDF
            pdf.cell(0, 10, line.strip(), 0, 1)
    
    # Save the PDF
    pdf.output(output_file)

if __name__ == "__main__":
    create_pdf("test_event_brochure.txt", "test_event_brochure.pdf")
    print("Test PDF created: test_event_brochure.pdf")
