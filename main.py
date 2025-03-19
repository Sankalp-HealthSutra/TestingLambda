from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
from pdf_generation import generate_pdf_with_wkhtmltopdf
from io import BytesIO
import logging
import os
from dotenv import load_dotenv
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


app = FastAPI(
    title="Patient Report Service",
    description="Service to generate patient reports in PDF format"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the data model
class ReportData(BaseModel):
    reportDetails: Dict[str, Any]
    tests: list[Dict[str, Any]]
    summary: str
    referenceLinks: Dict[str,Any]
    inRangeCategory: list[str, Any]
    originalFileLink: str
    smartReportName: str
    patientData: Dict[str, Any]
    overallMonitoringRecommendation: list[Dict[str, Any]]
    overallExerciseRecommendations: list[str, Any]
    dietSummary: Dict[str, Any]


@app.get("/")
async def root():
    return {"message": "Welcome to the Patient Report Service"}
# Update the generate_report endpoint
@app.post("/generate-report/")
async def generate_report(data: ReportData):
    try:
        aws_access_key_id = os.getenv('AWS_ACCESS')
        aws_secret_access_key = os.getenv('AWS_SECRET')
        # Generate PDF using existing function
        pdf_bytes = generate_pdf_with_wkhtmltopdf(data.dict(),aws_access_key_id,aws_secret_access_key)

        # Wrap the bytes in BytesIO
        pdf_buffer = BytesIO(pdf_bytes)

        # Return PDF as downloadable file
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=patient_report.pdf"
            }
        )
    except Exception as e:
        logger.error("Error in generate_report:", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)