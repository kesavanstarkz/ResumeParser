
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import io

# Windows only (uncomment if PATH not set)
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\Kesavan.munusamy\AppData\Local\Programs\Tesseract-OCR"

def extract_and_parse_resume(file_bytes, content_type):
    if content_type == "application/pdf":
        doc = fitz.open(stream=file_bytes)
        raw_text = "".join(page.get_text() for page in doc)

        if len(raw_text.strip()) < 100:
            print("📄 Scanned / secured PDF detected → Using OCR")
            images = convert_from_bytes(file_bytes, dpi=300)
            final_text = ""
            for i, img in enumerate(images):
                text = pytesseract.image_to_string(
                    img,
                    lang="eng",
                    config="--oem 3 --psm 6"
                )
                final_text += f"\n\n--- Page {i+1} ---\n\n{text}"
            return final_text
        else:
            print("📄 Text-based PDF detected → Using PyMuPDF")
            return raw_text
    else:  # image
        img = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(
            img,
            lang="eng",
            config="--oem 3 --psm 6"
        )
        return text