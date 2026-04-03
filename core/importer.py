import os
import shutil
import hashlib
import datetime
import re

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    Image = None

VAULT_DIR = os.path.expanduser("~/StudyVault")

def get_file_hash(filepath: str) -> str:
    """Calculate the SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        # Read file in 4K blocks
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def clean_filename(filename: str) -> str:
    """Helper to strip bad characters from filename."""
    name, ext = os.path.splitext(filename)
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name)

def generate_vault_filename(original_filename: str) -> str:
    """Append _day_month_yr_sf26 to the filename."""
    name, ext = os.path.splitext(original_filename)
    clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
    date_str = datetime.datetime.now().strftime("%d_%b_%y").lower()
    return f"{clean_name}_{date_str}_sf26{ext}"

def split_filename_for_display(filename: str) -> tuple:
    """
    Takes a filename like 'refreshing_31_mar_26_sf26.pdf' and returns
    a tuple for smart card UI: ('refreshing', '31_mar_26_sf26.pdf').
    """
    name, ext = os.path.splitext(filename)
    if name.endswith("_sf26"):
        parts = name.split('_')
        if len(parts) >= 5:
            display_name = "_".join(parts[:-4])
            suffix = "_".join(parts[-4:]) + ext
            if display_name:
                return display_name, suffix
            
    return filename, ""

def get_category_for_file(filepath: str) -> str:
    """Determine the subfolder category based on file extension."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.pdf':
        return 'PDFs'
    elif ext in ['.ppt', '.pptx']:
        return 'Slides'
    elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
        return 'Images'
    elif ext in ['.md', '.txt', '.docx']:
        return 'Notes'
    else:
        return 'Other'

def extract_text(filepath: str) -> str:
    """Extract text from PDF or Image for indexing."""
    ext = os.path.splitext(filepath)[1].lower()
    text = ""
    try:
        if ext == '.pdf' and fitz:
            doc = fitz.open(filepath)
            for page in doc:
                text += page.get_text()
            doc.close()
        elif ext in ['.png', '.jpg', '.jpeg', '.bmp'] and pytesseract and Image:
            text = pytesseract.image_to_string(Image.open(filepath))
    except Exception as e:
        print(f"Error extracting text from {filepath}: {e}")
    return text.strip()

def process_file_import(source_filepath: str, course_name: str, check_duplicate_callback=None) -> dict:
    """
    Import a file into the Vault.
    Returns a dict with status and details.
    """
    if not os.path.exists(source_filepath):
        return {"status": "error", "message": "Source file does not exist."}

    file_hash = get_file_hash(source_filepath)
    
    # Check for duplicates using the callback (which hits the DB)
    if check_duplicate_callback and check_duplicate_callback(file_hash):
        return {"status": "skipped", "message": "Duplicate file detected.", "hash": file_hash}

    category = get_category_for_file(source_filepath)
    new_filename = generate_vault_filename(os.path.basename(source_filepath))
    
    dest_dir = os.path.join(VAULT_DIR, course_name, category)
    os.makedirs(dest_dir, exist_ok=True)
    
    dest_filepath = os.path.join(dest_dir, new_filename)
    
    # Actually copy file
    shutil.copy2(source_filepath, dest_filepath)
    
    # Extract text after moving for indexing
    extracted_text = extract_text(dest_filepath)

    return {
        "status": "success",
        "original_path": source_filepath,
        "vault_path": dest_filepath,
        "file_hash": file_hash,
        "extracted_text": extracted_text,
        "category": category,
        "course": course_name
    }
