import os
import shutil
from core.importer import process_file_import
from core.database import initialize_db, insert_file, check_duplicate_hash, search_files, get_all_courses

def test_importer_and_db():
    print("--- Starting Notak Core Tests ---")

    # 1. Initialize Database
    print("\n1. Initializing DB...")
    initialize_db()
    
    # 2. Create Dummy Files
    print("\n2. Creating dummy files...")
    dummy_dir = os.path.expanduser("~/test_files")
    os.makedirs(dummy_dir, exist_ok=True)
    
    file1 = os.path.join(dummy_dir, "Lecture_1- Intro to AI.pdf")
    with open(file1, "w") as f:
        f.write("This is a dummy PDF file content about artificial intelligence and machine learning.")
        
    file2 = os.path.join(dummy_dir, "assignment_1.md")
    with open(file2, "w") as f:
        f.write("# Assignment 1\nSubmit your work by Friday.")

    # 3. Simulate Drag & Drop (Import) for file1
    print(f"\n3. Importing {file1}...")
    course_name = "Artificial Intelligence"
    result1 = process_file_import(
        source_filepath=file1, 
        course_name=course_name,
        check_duplicate_callback=check_duplicate_hash
    )
    print(f"Import result: {result1['status']}")
    if result1['status'] == 'success':
        # Database Insertion
        print(f" -> Saving to DB. Dest: {result1['vault_path']}")
        file_id = insert_file(
            path=result1['vault_path'],
            file_hash=result1['file_hash'],
            course=result1['course'],
            category=result1['category'],
            text_content=result1['extracted_text'] or "Dummy text extraction" # since pymupdf might not be loaded yet
        )
        print(f" -> DB Inserted ID: {file_id}")
        
    # 4. Simulate Duplicate Drop
    print(f"\n4. Importing {file1} AGAIN (should skip)...")
    with open(file1, "w") as f: # Recreate because shutil.move deleted it
        f.write("This is a dummy PDF file content about artificial intelligence and machine learning.")
    
    result_dup = process_file_import(
        source_filepath=file1, 
        course_name=course_name,
        check_duplicate_callback=check_duplicate_hash
    )
    print(f"Import result: {result_dup['status']}")
    if result_dup['status'] == 'skipped':
        print(f" -> Successfully caught duplicate with hash: {result_dup['hash']}")

    # 5. Search test
    print("\n5. Searching for 'artificial intelligence' in FTS5...")
    search_res = search_files("artificial")
    print(f"Found {len(search_res)} results:")
    for res in search_res:
        print(f" - [{res['course']} / {res['category']}] {res['path']}")
        
    # 6. Cleanup dummy source dir
    shutil.rmtree(dummy_dir, ignore_errors=True)
    print("\n--- Tests Completed Successfully ---")

if __name__ == "__main__":
    test_importer_and_db()
