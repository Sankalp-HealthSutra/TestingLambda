import pdfkit
from jinja2 import Template
from io import BytesIO
import json
import os
import requests
import boto3
from urllib.parse import urlparse, unquote
from PyPDF2 import PdfReader, PdfWriter
from dotenv import load_dotenv
import base64
from datetime import datetime

load_dotenv()
with open('new2.json', 'r', encoding="utf-8") as file:
    data2 = json.load(file)

def download_pdf(url, output_path, aws_access_key_id, aws_secret_access_key):
    try:
        parsed_url = urlparse(url)
        
        if parsed_url.netloc.endswith('amazonaws.com'):  # Handle S3 URLs
            # Extract bucket and key from the URL
            path_parts = parsed_url.path.lstrip('/').split('/')
            bucket = parsed_url.netloc.split('.')[0]  # Get bucket name from subdomain
            key = unquote('/'.join(path_parts)).replace('+', ' ')
            print(f"Downloading PDF from S3 bucket '{bucket}' with key '{key}'")
            s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
            
            try:
                s3_client.download_file(bucket, key, output_path)
                
                # Verify the downloaded file
                if os.path.getsize(output_path) == 0:
                    raise ValueError("Downloaded PDF file is empty")
                
                # Try to open it as PDF to verify integrity
                try:
                    with open(output_path, 'rb') as test_file:
                        PdfReader(test_file)
                except Exception as pdf_error:
                    raise ValueError(f"Downloaded file is not a valid PDF: {str(pdf_error)}")
                    
            except s3_client.exceptions.ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                error_message = e.response.get('Error', {}).get('Message', 'Unknown error')
                raise Exception(f"S3 error ({error_code}): {error_message}")
                
        else:  # Handle HTTP URLs
            response = requests.get(url)
            response.raise_for_status()
            
            with open(output_path, 'wb') as file:
                file.write(response.content)
            
            # Verify file size
            if os.path.getsize(output_path) == 0:
                raise ValueError("Downloaded PDF file is empty")
                
            # Verify PDF integrity
            try:
                with open(output_path, 'rb') as test_file:
                    PdfReader(test_file)
            except Exception as pdf_error:
                raise ValueError(f"Downloaded file is not a valid PDF: {str(pdf_error)}")
                
    except Exception as e:
        if os.path.exists(output_path):
            os.remove(output_path)  # Clean up partial downloads
        print(f"Error downloading PDF from {url}: {str(e)}")
        raise

def append_pdf(original_pdf_path, generated_pdf_path):
    try:
        # Verify files exist
        if not os.path.exists(original_pdf_path):
            raise FileNotFoundError(f"Original PDF not found at {original_pdf_path}")
        if not os.path.exists(generated_pdf_path):
            raise FileNotFoundError(f"Generated PDF not found at {generated_pdf_path}")
            
        # Create a PDF writer object
        pdf_writer = PdfWriter()

        # Try reading the generated PDF first
        try:
            with open(generated_pdf_path, 'rb') as generated_pdf_file:
                generated_pdf = PdfReader(generated_pdf_file)
                for page_num in range(len(generated_pdf.pages)):
                    pdf_writer.add_page(generated_pdf.pages[page_num])
        except Exception as e:
            raise ValueError(f"Error reading generated PDF: {str(e)}")

        # Then try reading the original PDF
        try:
            with open(original_pdf_path, 'rb') as original_pdf_file:
                original_pdf = PdfReader(original_pdf_file)
                for page_num in range(len(original_pdf.pages)):
                    pdf_writer.add_page(original_pdf.pages[page_num])
        except Exception as e:
            raise ValueError(f"Error reading original PDF: {str(e)}")

        # Write the combined PDF to a bytes buffer
        output_pdf_buffer = BytesIO()
        pdf_writer.write(output_pdf_buffer)
        output_pdf_buffer.seek(0)
        return output_pdf_buffer
        
    except Exception as e:
        # Clean up any temporary files if there's an error
        if os.path.exists(original_pdf_path):
            os.remove(original_pdf_path)
        if os.path.exists(generated_pdf_path):
            os.remove(generated_pdf_path)
        raise

def generate_pdf_with_wkhtmltopdf(data, aws_access_key_id, aws_secret_access_key):
    # Load the HTML template for the body
    with open("template_patient.html", "r", encoding="utf-8") as html_file:
        html_template = html_file.read()
    
    # Load the header HTML template
    with open("header.html", "r", encoding="utf-8") as header_file:
        header_template = header_file.read()
    
    # Load the footer HTML template
    with open("footer.html", "r", encoding="utf-8") as footer_file:
        footer_template = footer_file.read()
    
    # Load the first page HTML template
    with open("firstPage.html", "r", encoding="utf-8") as first_page_file:
        first_page_template = first_page_file.read()
    
    # Load the external CSS file
    css_path = os.path.join(os.path.dirname(__file__), "template.css")
    with open(css_path, "r", encoding="utf-8") as css_file:
        css_content = css_file.read()

    # Inject CSS into the HTML template
    styled_header = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href='https://fonts.googleapis.com/css?family=Poppins' rel='stylesheet'>
        <title>Report</title>
        <style>
        {css_content}
        </style>
    </head>
    """
    html_template = html_template.replace("<head>", styled_header)  # Replace <head> with styled header
    
    # Render the first page HTML using Jinja2
    first_page_template_obj = Template(first_page_template)

    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Construct full paths for the images
    logo_file = os.path.join(current_dir, "Footer1.png")
    background_file = os.path.join(current_dir, "backgroundfron.png")

    # Convert these images to Base64 strings
    logo_base64 = image_to_base64(logo_file)
    background_base64 = image_to_base64(background_file)

    # Create data URLs for embedding in HTML
    logo_data_url = f"data:image/png;base64,{logo_base64}"
    background_data_url = f"data:image/png;base64,{background_base64}"

    # Render firstPage.html template with these variables.
    current_date = datetime.now().strftime("%d/%m/%Y")
    
    first_page_content = first_page_template_obj.render(
        author="HealthSutra",
        date=current_date,
        patient_name=data["reportDetails"].get("patientName", "Patient"),
        website="healthsutra.ai",
        email="contact@healthsutra.ai",
        logo_data_url=logo_data_url,
        background_data_url=background_data_url
    )
    
    # Render the header HTML using Jinja2
    header_template_obj = Template(header_template)
    header_content = header_template_obj.render(
        reportDetails=data["reportDetails"], 
        reportMetadata=data["reportDetails"]["reportMetadata"]
    )
    
    # Render the main HTML body
    template = Template(html_template)
    html_content = template.render(
        reportDetails=data["reportDetails"], 
        tests=data["tests"],
        summary=data["summary"],
        refLinks=data["referenceLinks"],
        inRangeCategory=data["inRangeCategory"],
        originalFileLink=data["originalFileLink"],
        smartReportName=data["smartReportName"],
        patientData=data["patientData"],
        dietSummary = data["dietSummary"],
        overallMonitoring = data["overallMonitoringRecommendation"],
        overallExerciseRecommendations = data["overallExerciseRecommendations"]
    )
    
    # Render the footer using the footer template and pass the JSON data
    footer_template_obj = Template(footer_template)
    footer_content = footer_template_obj.render(
        reportDetails=data["reportDetails"],
        reportMetadata=data["reportDetails"]["reportMetadata"],
        tests=data["tests"],
        summary=data["summary"],
        refLinks=data["referenceLinks"]
    )
    
    # Save the rendered header HTML to a temporary file
    header_temp_path = "temp_header.html"
    with open(header_temp_path, "w", encoding="utf-8") as temp_header_file:
        temp_header_file.write(header_content)
    
    footer_temp_path = "temp_footer.html"
    with open(footer_temp_path, "w", encoding="utf-8") as temp_footer_file:
        temp_footer_file.write(footer_content)
    
    first_page_pdf_path = "first_page.html"
    with open(first_page_pdf_path, "w", encoding="utf-8") as first_page_file:
        first_page_file.write(first_page_content)
    
    # Configure wkhtmltopdf path

    config = pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf')

    
    # Options for wkhtmltopdf, including the header and footer
    options = {
        "enable-local-file-access": "",
        "print-media-type": "",
        "header-html": header_temp_path,
        "footer-html": footer_temp_path,
        "header-spacing": "0",
        "enable-javascript": "",
        "javascript-delay": "3000",
        "margin-top": "26",
        "header-spacing": "5",
        "margin-right": "0",
        "margin-bottom": "20",
        "margin-left": "0"
    }
    
    # Save the main content to a temporary file for debugging
    with open("intermediate_report.html", "w", encoding="utf-8") as debug_file:
        debug_file.write(html_content)
    
    # Generate first page PDF (without header/footer)
    first_page_options = {
        "enable-local-file-access": "",
        "print-media-type": "",
        "header-spacing": "0",
        "enable-javascript": "",
        "javascript-delay": "1000",
        "margin-top": "0",
        "header-spacing": "0",
        "margin-right": "0",
        "margin-bottom": "0",
        "margin-left": "0",
        "page-size": "A4"
    }
    first_page_pdf = pdfkit.from_string(first_page_content, False, configuration=config, options=first_page_options)
    first_page_pdf_path = "first_page.pdf"
    with open(first_page_pdf_path, "wb") as first_page_pdf_file:
        first_page_pdf_file.write(first_page_pdf)
        
    
    # Generate main report PDF with JavaScript enabled (1 second delay)
    options["javascript-delay"] = "1000"
    main_pdf = pdfkit.from_string(html_content, False, configuration=config, options=options)
    main_pdf_path = "generated_report.pdf"
    with open(main_pdf_path, "wb") as main_pdf_file:
        main_pdf_file.write(main_pdf)
    
    # Clean up temporary header and footer files
    os.remove(header_temp_path)
    os.remove(footer_temp_path)

    # Download the original PDF from S3
    original_pdf_path = "original_report.pdf"
    download_pdf(data["originalFileLink"], original_pdf_path, aws_access_key_id, aws_secret_access_key)
    
    # Combine all three PDFs: first page + main report + original report
    combined_pdf = combine_pdfs([first_page_pdf_path, main_pdf_path, original_pdf_path])

    # Clean up temporary files
    for temp_file in [first_page_pdf_path, main_pdf_path, original_pdf_path]:
        if os.path.exists(temp_file):
            os.remove(temp_file)

    return combined_pdf.getvalue()

def combine_pdfs(pdf_paths):
    """Combine multiple PDFs in the order they appear in the list."""
    try:
        # Create a PDF writer object
        pdf_writer = PdfWriter()

        # Add each PDF's pages to the writer
        for pdf_path in pdf_paths:
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found at {pdf_path}")
                
            try:
                with open(pdf_path, 'rb') as pdf_file:
                    pdf = PdfReader(pdf_file)
                    for page_num in range(len(pdf.pages)):
                        pdf_writer.add_page(pdf.pages[page_num])
            except Exception as e:
                raise ValueError(f"Error reading PDF {pdf_path}: {str(e)}")

        # Write the combined PDF to a bytes buffer
        output_pdf_buffer = BytesIO()
        pdf_writer.write(output_pdf_buffer)
        output_pdf_buffer.seek(0)
        return output_pdf_buffer
        
    except Exception as e:
        # Clean up any temporary files if there's an error
        for pdf_path in pdf_paths:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        raise Exception(f"Error combining PDFs: {str(e)}")

def image_to_base64(image_path):
    with open(image_path, "rb") as img:
        return base64.b64encode(img.read()).decode('utf-8')

def main():
    try:
        input_file = "new2.json"
        with open(input_file, 'r', encoding="utf-8") as file:
            data = json.load(file)
        
        # Read JSON file
        output_file = data["smartReportName"] + ".pdf"

        with open(input_file, 'r', encoding="utf-8") as file:
            data = json.load(file)

        # AWS credentials
        aws_access_key_id = os.getenv('AWS_ACCESS')
        aws_secret_access_key = os.getenv('AWS_SECRET')

        # Generate PDF
        pdf_bytes = generate_pdf_with_wkhtmltopdf(data, aws_access_key_id, aws_secret_access_key)

        # Save PDF to output file
        with open(output_file, 'wb') as f:
            f.write(pdf_bytes)

        print(f"PDF generated successfully: {output_file}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
