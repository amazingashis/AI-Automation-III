import os
import shutil
from llm_mapper import process_domain_model
from sql_generator import generate_sql_scripts

UPLOADS_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), 'scripts')

def main():
    print("Welcome to the Subproject Script Generator!")
    print("Please place your domain model, data dictionary, and source files in the 'uploads/' folder.")
    input("Press Enter when ready to generate scripts...")

    # Example: Find files
    files = os.listdir(UPLOADS_DIR)
    domain_model = next((f for f in files if 'domain' in f.lower()), None)
    data_dict = next((f for f in files if 'dict' in f.lower()), None)
    source_file = next((f for f in files if 'csv' in f.lower()), None)

    if not (domain_model and data_dict and source_file):
        print("Missing required files. Please check uploads folder.")
        return

    # Process domain model (reusing logic)
    domain_model_path = os.path.join(UPLOADS_DIR, domain_model)
    data_dict_path = os.path.join(UPLOADS_DIR, data_dict)
    source_file_path = os.path.join(UPLOADS_DIR, source_file)

    print("Processing domain model and data dictionary...")
    process_domain_model(domain_model_path, data_dict_path)

    print("Generating SQL scripts using LLM...")
    generate_sql_scripts(domain_model_path, data_dict_path, source_file_path, SCRIPTS_DIR)

    print(f"Scripts generated in {SCRIPTS_DIR}")

if __name__ == "__main__":
    main()
