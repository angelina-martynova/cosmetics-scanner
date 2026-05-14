# Cosmetics Scanner

A web application for analyzing cosmetic product ingredients. Upload a photo of a product label — get a detailed report about each ingredient and its safety level.

## What it does

The user uploads a photo of a cosmetic product label. The app reads the text from the image, finds each ingredient in the database, and shows a report: what the substance is, what category it belongs to, how risky it is, and whether it is allowed by EU regulations and EWG standards.

## How it works

**Text recognition (OCR)** — the app extracts text from the label photo using Tesseract OCR. Before recognition, the image goes through preprocessing: contrast adjustment, noise reduction, and skew correction. EasyOCR and TrOCR can also be connected as alternative OCR engines.

**Ingredient analysis (NLP)** — the recognized text is parsed into separate ingredients. Each one is searched in the database using exact match, fuzzy search (RapidFuzz), and keyword-based classification. Unknown substances are automatically checked through external APIs (Open Food Facts, PubChem, CIR).

**Safety assessment** — each ingredient gets a risk level (safe / moderate / hazardous) based on EWG rating, GHS classification, and EU regulations. The overall product safety status is calculated automatically.

## Tech stack

- **Backend:** Flask, PostgreSQL, SQLAlchemy
- **OCR:** Tesseract (main), EasyOCR, TrOCR (optional)
- **Image processing:** PIL/Pillow, OpenCV
- **NLP:** regex parsing, RapidFuzz, keyword classification, ML filter
- **External APIs:** Open Food Facts, PubChem, CIR (Cosmetic Ingredient Review)
- **Export:** PDF reports (ReportLab)
- **Authentication:** Flask-Login

## Key features

- Upload a label photo or enter ingredient text manually
- Multi-engine OCR with image preprocessing
- Automatic ingredient recognition and classification
- Risk assessment based on EU regulations and EWG ratings
- Scan history with PDF export
- User system with admin panel for ingredient verification
