import asyncio
from pyppeteer import launch
import os

async def generate_pdf_with_pyppeteer(html_content: str) -> bytes:
  # Path to Chrome executable - update this to your Chrome installation path
  chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"  # Windows default path
  
  # Launch existing Chrome installation
  browser = await launch(
    headless=True,
    executablePath=chrome_path
  )
  page = await browser.newPage()
  
  # Load the HTML content directly
  await page.setContent(html_content, waitUntil='networkidle0')  # Wait for resources to load

  # Generate PDF (here, you can pass page size, margins, etc.)
  pdf_data = await page.pdf(
    format='A4', 
    margin={'top': '0.4in', 'right': '0.4in', 'bottom': '0.4in', 'left': '0.4in'}
  )

  await browser.close()
  return pdf_data
