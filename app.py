
# import os
# import re
# import sqlite3
# from datetime import datetime
# from pathlib import Path

# import pytesseract
# from PIL import Image, ImageOps, ImageEnhance
# from flask import Flask, render_template, request, redirect, url_for, flash

# app = Flask(__name__)
# app.secret_key = "lmmp-local-development-key"

# BASE_DIR = Path(__file__).resolve().parent
# UPLOAD_FOLDER = BASE_DIR / "uploads"
# DATABASE = BASE_DIR / "history.db"

# UPLOAD_FOLDER.mkdir(exist_ok=True)

# app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
# app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

# # Update this path if Tesseract is installed elsewhere.
# TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# if os.path.exists(TESSERACT_PATH):
#     pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


# def init_db():
#     with sqlite3.connect(DATABASE) as con:
#         con.execute("""
#             CREATE TABLE IF NOT EXISTS scans (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 filename TEXT NOT NULL,
#                 extracted_text TEXT,
#                 scan_date TEXT NOT NULL
#             )
#         """)


# def extract_text(image_path):
#     """Extract printed text from the uploaded product label."""
#     try:
#         with Image.open(image_path) as original:
#             image = ImageOps.exif_transpose(original).convert("RGB")
#             image = ImageOps.grayscale(image)
#             image = ImageEnhance.Contrast(image).enhance(1.7)

#             text = pytesseract.image_to_string(
#                 image, config="--psm 6"
#             ).strip()

#         return text, None

#     except pytesseract.TesseractNotFoundError:
#         return "", (
#             "Tesseract OCR was not found. Install the Tesseract "
#             "Windows application and check its installation path."
#         )
#     except Exception as error:
#         return "", f"Could not read this image: {error}"


# def screen_text(text):
#     """Basic preliminary screening; not a legal determination."""
#     checks = [
#         ("Product / commodity name",
#          bool(re.search(r"\b(product|rice|chocolate|biscuit|soap|tea|oil)\b",
#                         text, re.I))),
#         ("Manufacturer / packer / importer details",
#          bool(re.search(r"manufactured by|packed by|imported by|manufacturer",
#                         text, re.I))),
#         ("Net quantity and units",
#          bool(re.search(r"\b(net\s*(qty|quantity)?|quantity)\b.*"
#                         r"\d+\s*(kg|g|mg|l|ml|litre|liter|pcs?)\b",
#                         text, re.I | re.S))),
#         ("MRP / retail sale price",
#          bool(re.search(r"\b(mrp|maximum retail price)\b", text, re.I))),
#         ("Date declaration",
#          bool(re.search(r"\b(best before|date of manufacture|mfg|"
#                         r"manufactured on|expiry|use by|packed on)\b",
#                         text, re.I))),
#         ("Country of origin (if applicable)",
#          bool(re.search(r"\b(country of origin|made in|product of)\b",
#                         text, re.I))),
#     ]

#     return [
#         {
#             "name": name,
#             "found": found,
#             "status": "Text found" if found else "Needs review"
#         }
#         for name, found in checks
#     ]


# def save_scan(filename, text):
#     with sqlite3.connect(DATABASE) as con:
#         con.execute(
#             "INSERT INTO scans (filename, extracted_text, scan_date) "
#             "VALUES (?, ?, ?)",
#             (filename, text, datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
#         )


# @app.route("/")
# def index():
#     return render_template("index.html")


# @app.route("/scan", methods=["GET", "POST"])
# def scan():
#     if request.method == "POST":
#         file = request.files.get("product_image")

#         if not file or not file.filename:
#             flash("Please select a product label image.")
#             return redirect(url_for("scan"))

#         extension = file.filename.rsplit(".", 1)[-1].lower()
#         if "." not in file.filename or extension not in ALLOWED_EXTENSIONS:
#             flash("Upload a PNG, JPG, JPEG, or WEBP image.")
#             return redirect(url_for("scan"))

#         # Generate a safe unique filename rather than trusting user input.
#         filename = datetime.now().strftime("%Y%m%d%H%M%S%f") + "." + extension
#         image_path = UPLOAD_FOLDER / filename
#         file.save(image_path)

#         text, error = extract_text(str(image_path))
#         checks = screen_text(text) if text else []

#         save_scan(filename, text)

#         return render_template(
#             "result.html",
#             filename=filename,
#             extracted_text=text,
#             checks=checks,
#             ocr_error=error
#         )

#     return render_template("scan.html")


# @app.route("/history")
# def history():
#     with sqlite3.connect(DATABASE) as con:
#         con.row_factory = sqlite3.Row
#         records = con.execute(
#             "SELECT * FROM scans ORDER BY id DESC"
#         ).fetchall()

#     return render_template("history.html", records=records)


# @app.errorhandler(413)
# def too_large(_error):
#     flash("Image is too large. Maximum upload size is 10 MB.")
#     return redirect(url_for("scan"))


# init_db()

# if __name__ == "__main__":
#     app.run(debug=True)


import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import pytesseract
from PIL import (
    Image,
    ImageOps,
    ImageEnhance,
    ImageChops,
)
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from werkzeug.utils import secure_filename


# ==================================================
# 1. APPLICATION CONFIGURATION
# ==================================================

app = Flask(__name__)

app.secret_key = "labelcheck-local-development-key"

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
DATABASE_PATH = BASE_DIR / "history.db"

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    "png", "jpg", "jpeg", "webp", "bmp"
}

# Update this path if Tesseract is installed elsewhere.
TESSERACT_PATH = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

if os.path.isfile(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


# ==================================================
# 2. DATABASE CONNECTION AND MIGRATION
# ==================================================

def get_db_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    """
    Create the scans table if necessary.
    Add missing columns to an older database without
    deleting existing scan records.
    """

    with get_db_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL DEFAULT '',
                extracted_text TEXT,
                scan_date TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Needs review'
            )
        """)

        existing_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(scans)"
            ).fetchall()
        }

        # Migrate databases created by older versions.
        migrations = {
            "filename": (
                "ALTER TABLE scans ADD COLUMN "
                "filename TEXT NOT NULL DEFAULT ''"
            ),
            "extracted_text": (
                "ALTER TABLE scans ADD COLUMN extracted_text TEXT"
            ),
            "scan_date": (
                "ALTER TABLE scans ADD COLUMN "
                "scan_date TEXT NOT NULL DEFAULT ''"
            ),
            "status": (
                "ALTER TABLE scans ADD COLUMN "
                "status TEXT NOT NULL DEFAULT 'Needs review'"
            ),
        }

        for column_name, sql in migrations.items():
            if column_name not in existing_columns:
                connection.execute(sql)

        connection.commit()


# Run the database setup every time the app starts.
init_database()


# ==================================================
# 3. FILE VALIDATION
# ==================================================

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# ==================================================
# 4. IMAGE PREPROCESSING
# ==================================================

def preprocess_image(image_path):
    """
    Enlarge the product label and improve contrast
    to help OCR recognize small printed text.
    """

    with Image.open(image_path) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")

    # Crop excess white background around the package.
    white_background = Image.new("RGB", image.size, "white")
    difference = ImageChops.difference(
        image,
        white_background
    ).convert("L")

    difference = difference.point(
        lambda pixel: 255 if pixel > 30 else 0
    )

    bbox = difference.getbbox()

    if bbox:
        image = image.crop(bbox)

    # Add a white margin around the label.
    image = ImageOps.expand(
        image,
        border=25,
        fill="white"
    )

    # Enlarge the label for small-print recognition.
    width, height = image.size
    image = image.resize(
        (width * 3, height * 3),
        Image.Resampling.LANCZOS
    )

    # Convert to grayscale and improve contrast.
    image = ImageOps.grayscale(image)
    image = ImageOps.autocontrast(image)
    image = ImageEnhance.Contrast(image).enhance(2.0)
    image = ImageEnhance.Sharpness(image).enhance(2.0)

    return image


# ==================================================
# 5. OCR TEXT EXTRACTION
# ==================================================

def extract_text_from_image(image_path):
    """
    Read printed text using Tesseract OCR.
    Try multiple page segmentation modes.
    """

    if not os.path.isfile(TESSERACT_PATH):
        raise RuntimeError(
            "Tesseract OCR was not found. Install the "
            "Tesseract Windows application and check "
            "TESSERACT_PATH in app.py."
        )

    image = preprocess_image(image_path)

    recognized_results = []

    # Mode 6: a uniform block of text.
    # Mode 11: scattered text.
    # Mode 4: text arranged in columns.
    for page_mode in ("6", "11", "4"):
        try:
            result = pytesseract.image_to_string(
                image,
                lang="eng",
                config=f"--oem 3 --psm {page_mode}",
                timeout=60,
            ).strip()

            if result:
                recognized_results.append(result)

        except pytesseract.TesseractError:
            continue

    if not recognized_results:
        return ""

    # Prefer the result with the most recognized text.
    return max(
        recognized_results,
        key=lambda text: len(
            re.sub(r"\s+", "", text)
        )
    )


# ==================================================
# 6. DECLARATION SCREENING
# ==================================================

def screen_text(text):
    """
    Identify possible label declarations using
    keyword patterns. This is preliminary screening,
    not a legal compliance decision.
    """

    normalized_text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    fields = [
        (
            "Commodity / product name",
            r"\b(chocolate|biscuit|rice|sugar|milk|"
            r"soap|oil|flour|snack|food|product)\b",
        ),
        (
            "Manufacturer / packer / importer details",
            r"\b(manufactured by|manufactured for|"
            r"manufacturer|packed by|packer|"
            r"imported by|importer|marketed by)\b",
        ),
        (
            "Net quantity and units",
            r"\b(net\s*(?:wt\.?|weight|quantity|qty\.?)?)"
            r"\b.{0,45}\b\d+(?:\.\d+)?\s*"
            r"(?:kg|g|gm|grams?|mg|ml|l|litres?|liters?)\b"
            r"|\b\d+(?:\.\d+)?\s*"
            r"(?:kg|grams?|gm|g|mg|ml|litres?|liters?|l)\b",
        ),
        (
            "MRP / retail sale price",
            r"\b(m\.?\s*r\.?\s*p\.?|"
            r"maximum retail price|retail sale price|"
            r"inclusive of all taxes)\b",
        ),
        (
            "Date declarations",
            r"\b(date of manufacture|manufactured on|"
            r"mfg\.?\s*date|mfg\.?|packed on|"
            r"packing date|best before|use by|"
            r"expiry date|expires on|date of packing)\b",
        ),
        (
            "Country of origin (where applicable)",
            r"\b(country of origin|made in|"
            r"product of|origin\s*:)\b",
        ),
    ]

    checks = []

    for field_name, pattern in fields:
        match = re.search(
            pattern,
            normalized_text,
            flags=re.IGNORECASE
        )

        if match:
            start = max(0, match.start() - 45)
            end = min(
                len(normalized_text),
                match.end() + 75
            )

            evidence = normalized_text[start:end]

            checks.append({
                "field": field_name,
                "status": "Detected",
                "evidence": evidence,
            })

        else:
            checks.append({
                "field": field_name,
                "status": "Needs review",
                "evidence": (
                    "No matching text pattern was identified."
                ),
            })

    return checks


# ==================================================
# 7. HOME PAGE
# ==================================================

@app.route("/")
def index():
    return render_template("index.html")


# ==================================================
# 8. SCAN PRODUCT
# ==================================================

@app.route("/scan", methods=["GET", "POST"])
def scan():

    if request.method == "GET":
        return render_template("scan.html")

    uploaded_file = request.files.get("image")

    if (
        uploaded_file is None
        or uploaded_file.filename.strip() == ""
    ):
        flash("Please select a product label image.")
        return redirect(url_for("scan"))

    if not allowed_file(uploaded_file.filename):
        flash(
            "Unsupported image format. "
            "Use PNG, JPG, JPEG, WEBP, or BMP."
        )
        return redirect(url_for("scan"))

    original_filename = secure_filename(
        uploaded_file.filename
    )

    if not original_filename:
        flash("The selected filename is invalid.")
        return redirect(url_for("scan"))

    # Generate a unique filename to avoid overwriting uploads.
    timestamp = datetime.now().strftime(
        "%Y%m%d%H%M%S%f"
    )

    saved_filename = f"{timestamp}_{original_filename}"
    image_path = UPLOAD_FOLDER / saved_filename

    uploaded_file.save(image_path)

    extracted_text = ""
    error_message = ""

    # Run OCR.
    try:
        extracted_text = extract_text_from_image(
            str(image_path)
        )

        if not extracted_text:
            error_message = (
                "No readable text was recognized. Try a "
                "sharper image with the label filling more "
                "of the picture and the printed text in focus."
            )

    except RuntimeError as error:
        error_message = str(error)

    except Exception:
        app.logger.exception("OCR processing failed")

        error_message = (
            "OCR processing failed. Check the terminal "
            "for details and confirm Tesseract is installed."
        )

    # Screen fields only if OCR returned text.
    checks = (
        screen_text(extracted_text)
        if extracted_text
        else []
    )

    if extracted_text:
        scan_status = "Text extracted - review required"
    else:
        scan_status = "OCR failed - review required"

    # Save scan results. The database migration above
    # ensures older databases have the necessary columns.
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO scans (
                filename,
                extracted_text,
                scan_date,
                status
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                saved_filename,
                extracted_text,
                datetime.now().strftime(
                    "%d-%m-%Y %I:%M:%S %p"
                ),
                scan_status,
            ),
        )

        connection.commit()
        scan_id = cursor.lastrowid

    return render_template(
        "result.html",
        scan_id=scan_id,
        filename=original_filename,
        image_filename=saved_filename,
        extracted_text=extracted_text,
        checks=checks,
        error_message=error_message,
    )


# ==================================================
# 9. SCAN HISTORY
# ==================================================

@app.route("/history")
def history():

    with get_db_connection() as connection:
        scans = connection.execute(
            """
            SELECT
                id,
                filename,
                extracted_text,
                scan_date,
                status
            FROM scans
            ORDER BY id DESC
            """
        ).fetchall()

    return render_template(
        "history.html",
        scans=scans
    )


# ==================================================
# 10. UPLOAD SIZE ERROR
# ==================================================

@app.errorhandler(413)
def file_too_large(error):
    flash(
        "The selected image exceeds the 10 MB limit. "
        "Please choose a smaller image."
    )
    return redirect(url_for("scan"))


# ==================================================
# 11. START APPLICATION
# ==================================================

if __name__ == "__main__":
    app.run(debug=True)
