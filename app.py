# --- SQL Script Generation Endpoint ---
from sql_generator import generate_sql_scripts

# ...existing code...

# Place this after the Flask app is created

def register_sql_scripts_endpoint(app):
    @app.route('/generate_sql_scripts', methods=['POST'])
    def generate_sql_scripts_endpoint():
        try:
            data = request.get_json() or {}
            source_table = data.get('source_table', 'silver.elig')
            output_table = data.get('output_table', 'output_Table')
            # Use the mappings.json file and default domain/data dict paths
            mappings_path = 'mappings.json'
            domain_model_path = 'domain_model/Domain Model Eligibility.xlsx'
            data_dict_path = 'data_dict/member eligibility data dictitonary.xlsx'
            sql_chunks = generate_sql_scripts(
                source_table=source_table,
                mappings_path=mappings_path,
                domain_model_path=domain_model_path,
                data_dict_path=data_dict_path,
                output_table=output_table
            )
            return jsonify({'success': True, 'sql_chunks': sql_chunks})
        except Exception as e:
            import traceback
            return jsonify({'success': False, 'error': str(e), 'trace': traceback.format_exc()})
# --- Data Dictionary & Domain Model Parsing Utilities ---
import pandas as pd


# --- LLM Context Builder ---
def build_llm_context(data_dict_df, domain_model_df):
    context = []
    context.append('SOURCE DATA COLUMNS (sample):')
    for _, row in data_dict_df.head(20).iterrows():
        context.append(f"- {row['column_name']} ({row.get('data_type','')}): {row.get('description','')}")
    context.append('\nTARGET DOMAIN MODEL:')
    for _, row in domain_model_df.iterrows():
        context.append(f"- {row['column_name']} ({row.get('data_type','')}): {row.get('description','')}")
    context.append('\nTASK: Map each source field to the most appropriate stage field.')
    return '\n'.join(context)

from flask import Flask, render_template, request, jsonify, redirect, url_for
import csv
import os
import json
from werkzeug.utils import secure_filename
import re
from llm_mapper import generate_mappings as llm_generate_mappings
from dotenv import load_dotenv
from utils import parse_domain_model, parse_data_dict

load_dotenv()





# Helper to read uploaded context files (or fallback to default)
def get_context_file(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return default

# Default context (used if no file uploaded)
DEFAULT_DOMAIN_MODEL = "Eligibility Domain Model: ..."
DEFAULT_DATA_DICTIONARY = "Source Data Dictionary: ..."

# ...existing code...

app = Flask(__name__)
register_sql_scripts_endpoint(app)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Paths for uploaded context files (must be after app is defined)
DATA_DICT_UPLOAD_PATH = os.path.join(app.config['UPLOAD_FOLDER'], 'context', 'data_dict.txt')
DOMAIN_MODEL_UPLOAD_PATH = os.path.join(app.config['UPLOAD_FOLDER'], 'domain', 'domain_model.txt')

@app.route('/upload_data_dict', methods=['POST'])
def upload_data_dict():
    if 'data_dict_file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    file = request.files['data_dict_file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(DATA_DICT_UPLOAD_PATH), exist_ok=True)
    filename = file.filename.lower()
    try:
        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            df = parse_data_dict(file)
            # Save normalized CSV for LLM context
            df.to_csv(DATA_DICT_UPLOAD_PATH, index=False)
        elif filename.endswith('.csv'):
            df = pd.read_csv(file)
            df.to_csv(DATA_DICT_UPLOAD_PATH, index=False)
        else:
            # Save as plain text
            file.save(DATA_DICT_UPLOAD_PATH)
        return jsonify({'success': True, 'message': 'Data dictionary uploaded successfully.'})
    except Exception as e:
        return jsonify({'error': f'Failed to process file: {str(e)}'}), 400

@app.route('/upload_domain_model', methods=['POST'])
def upload_domain_model():
    if 'domain_model_file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    file = request.files['domain_model_file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(DOMAIN_MODEL_UPLOAD_PATH), exist_ok=True)
    filename = file.filename.lower()
    try:
        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            df = parse_domain_model(file)
            df.to_csv(DOMAIN_MODEL_UPLOAD_PATH, index=False)
        elif filename.endswith('.csv'):
            df = pd.read_csv(file)
            df.to_csv(DOMAIN_MODEL_UPLOAD_PATH, index=False)
        else:
            file.save(DOMAIN_MODEL_UPLOAD_PATH)
        return jsonify({'success': True, 'message': 'Domain model uploaded successfully.'})
    except Exception as e:
        return jsonify({'error': f'Failed to process file: {str(e)}'}), 400


# Paths for uploaded context files (must be after app is defined)
DATA_DICT_UPLOAD_PATH = os.path.join(app.config['UPLOAD_FOLDER'], 'context', 'data_dict.txt')
DOMAIN_MODEL_UPLOAD_PATH = os.path.join(app.config['UPLOAD_FOLDER'], 'domain', 'domain_model.txt')

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Predefined stage fields for Eligibility data type
STAGE_FIELDS = [
    'memberFirst',
    'memberLast',
    'mbrDOB',
    'mbrGender',
    'ssn',
    'memberID',
    'enrollmentStatus',
    'enrollmentEffectiveDate',
    'terminationDate',
    'planID',
    'product',
    'lob',
    'memberMonth',
    'dualEligibilityInd',
    'coverageDesc',
    # Employer Group is now an object with subfields
    'employerGroups'  # Object with keys: groupName, groupStatus, addressLine1, addressLine2, zip
]

# Predefined transformation rules/functions
TRANSFORMATION_RULES = {
    'Trim': 'strip()',
    'Upper': 'upper()',
    'Lower': 'lower()',
    'Title': 'title()',
    'Left': 'left(n)',
    'Right': 'right(n)',
    'Substring': 'substring(start, length)',
    'Replace': 'replace(old, new)',
    'Concatenate': 'concatenate(field1, field2)',
    'DateFormat': 'date_format(format)',
    'IsNull': 'is_null()',
    'NotNull': 'not_null()',
    'Length': 'length()',
    'Contains': 'contains(substring)'
}

# Global variables to store current session data
current_source_headers = []
current_mappings = {}
# Load mappings from mappings.json if it exists
if os.path.exists('mappings.json'):
    try:
        with open('mappings.json', 'r', encoding='utf-8') as f:
            current_mappings = json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load mappings.json: {e}")
current_source_data = []

# Databricks API configuration
import openai
DATABRICKS_BASE_URL = "https://dbc-3735add4-1cb6.cloud.databricks.com/serving-endpoints"
DATABRICKS_MODEL = "databricks-claude-sonnet-4"
# Get Databricks token from environment variable
DATABRICKS_TOKEN = os.environ.get('DATABRICKS_TOKEN')

@app.route('/')
def index():
    # Read input file headers and sample data for display
    sample_headers = []
    sample_rows = []
    try:
        csv_path = os.path.join('source_file', 'member_enrollment_file.csv')
        with open(csv_path, 'r', encoding='utf-8') as f:
            import csv
            reader = csv.reader(f)
            sample_headers = next(reader)
            sample_rows = [row for _, row in zip(range(10), reader)]
    except Exception:
        pass
    return render_template('index.html', 
                         stage_fields=STAGE_FIELDS, 
                         transformation_rules=TRANSFORMATION_RULES,
                         source_headers=sample_headers,
                         source_sample_rows=sample_rows,
                         mappings=current_mappings)

@app.route('/upload_source_file', methods=['POST'])
def upload_source_file():
    global current_source_headers, current_source_data
    
    if 'source_file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['source_file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and file.filename.endswith('.csv'):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Read CSV headers and sample data
            with open(filepath, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                current_source_headers = next(reader)  # First row as headers
                
                # Read first 10 rows for sample data
                current_source_data = []
                for i, row in enumerate(reader):
                    if i >= 10:  # Only read first 10 rows
                        break
                    current_source_data.append(row)
            
            return jsonify({
                'success': True,
                'headers': current_source_headers,
                'filename': filename,
                'sample_rows': len(current_source_data)
            })
        except Exception as e:
            return jsonify({'error': f'Error reading file: {str(e)}'}), 400
    
    return jsonify({'error': 'Invalid file format. Please upload a CSV file.'}), 400

@app.route('/save_mapping', methods=['POST'])
def save_mapping():
    global current_mappings
    
    data = request.get_json()
    stage_field = data.get('stage_field')
    mapping_expression = data.get('mapping_expression')
    
    if not stage_field or mapping_expression is None:
        return jsonify({'error': 'Stage field and mapping expression are required'}), 400


    # Special handling for employerGroups object
    if stage_field == 'employerGroups':
        try:
            # mapping_expression is a JSON stringified object
            group_obj = json.loads(mapping_expression) if isinstance(mapping_expression, str) else mapping_expression
            if not isinstance(group_obj, dict):
                raise ValueError('Employer Groups must be an object')
            # Only keep allowed keys
            allowed_keys = ['groupName', 'groupStatus', 'addressLine1', 'addressLine2', 'zip']
            filtered = {k: group_obj.get(k, '') for k in allowed_keys}
            current_mappings[stage_field] = filtered
            return jsonify({'success': True, 'message': 'Employer Group mapping saved'})
        except Exception as e:
            return jsonify({'error': f'Invalid Employer Group object: {e}'})

    # Validate the mapping expression (basic validation)

    if validate_mapping_expression(mapping_expression):
        current_mappings[stage_field] = mapping_expression
        # Save mappings to JSON file for persistence
        try:
            with open('mappings.json', 'w', encoding='utf-8') as f:
                json.dump(current_mappings, f, indent=2)
        except Exception as e:
            return jsonify({'error': f'Failed to save mappings to file: {e}'}), 500
        return jsonify({'success': True, 'message': 'Mapping saved successfully'})
    else:
        return jsonify({'error': 'Invalid mapping expression'}), 400

@app.route('/get_mappings', methods=['GET'])
def get_mappings():
    return jsonify(current_mappings)

@app.route('/clear_mappings', methods=['POST'])
def clear_mappings():
    global current_mappings
    current_mappings = {}
    return jsonify({'success': True, 'message': 'All mappings cleared'})

@app.route('/preview_transformation', methods=['POST'])
def preview_transformation():
    data = request.get_json()
    expression = data.get('expression', '')
    sample_data = data.get('sample_data', '')
    
    try:
        # Apply the transformation to sample data
        result = apply_transformation(expression, sample_data)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'error': f'Transformation error: {str(e)}'})

@app.route('/generate_llm_mappings', methods=['POST'])
def generate_llm_mappings_endpoint():
    """API endpoint to generate mappings using LLM via Databricks API."""
    global current_source_headers, current_source_data
    if not current_source_headers:
        return jsonify({'error': 'No source file uploaded'}), 400
    import sys
    try:
        print("[INFO] Starting LLM mapping generation...", file=sys.stderr)
        # Use parsed/normalized context for LLM
        try:
            data_dict_df = pd.read_csv(DATA_DICT_UPLOAD_PATH)
            domain_model_df = pd.read_csv(DOMAIN_MODEL_UPLOAD_PATH)
            llm_context = build_llm_context(data_dict_df, domain_model_df)
        except Exception as e:
            llm_context = f"[ERROR] Could not parse context files: {e}"
        extra_context = f"""
{llm_context}

INSTRUCTIONS:
You are an expert in US health care domain. Return ONLY a single JSON dictionary where each key is a stage field from the list below, and each value is the name of the most appropriate source field (from the source data) to map to that stage field.
For the field 'employerGroups', return an object with the following keys: groupName, groupStatus, addressLine1, addressLine2, zip. Each value should be the name of the most appropriate source field for that subfield. Example:

"employerGroups": {{
    "groupName": "...",
    "groupStatus": "...",
    "addressLine1": "...",
    "addressLine2": "...",
    "zip": "..."
}}

Do NOT include any transformation logic, mapping expressions, nested keys (except for employerGroups), reasoning, SQL scripts, or extra information.
Do NOT include a 'mappings' key, just the dictionary itself.
If a mapping is not possible, use an empty string as the value.
Stage fields: {', '.join(STAGE_FIELDS)}
"""
        result = llm_generate_mappings(
            current_source_headers,
            current_source_data[:10],  # Top 10 rows
            STAGE_FIELDS,
            token=DATABRICKS_TOKEN,
            extra_context=extra_context
        )
        print("[INFO] LLM response received:", file=sys.stderr)
        print(result, file=sys.stderr)
        if result['success']:
            # Expect a dictionary of mappings, with employerGroups as an object
            mappings = result.get('mappings')
            llm_mappings = mappings if isinstance(mappings, dict) else {}
            # Normalize mapping keys to match STAGE_FIELDS (case-insensitive, strip)
            stage_fields_norm = {sf.lower().strip(): sf for sf in STAGE_FIELDS}
            filtered = {}
            # Collect employer group subfields if present as top-level keys
            employer_group_keys = ['groupName', 'groupStatus', 'addressLine1', 'addressLine2', 'zip']
            employer_group_obj = {}
            employer_groups_valid = False
            for k, v in llm_mappings.items():
                k_norm = k.lower().strip()
                if k_norm == 'employergroups':
                    # Handle both dict and stringified dict
                    group_obj = v
                    if isinstance(group_obj, str):
                        try:
                            import json as _json
                            group_obj = _json.loads(group_obj)
                        except Exception:
                            group_obj = None
                    if isinstance(group_obj, dict):
                        allowed_keys = employer_group_keys
                        filtered['employerGroups'] = {subk: group_obj.get(subk, '') for subk in allowed_keys}
                        employer_groups_valid = True
                elif k in employer_group_keys:
                    employer_group_obj[k] = v.strip().strip('"') if isinstance(v, str) else ''
                elif k_norm in stage_fields_norm and isinstance(v, str):
                    filtered[stage_fields_norm[k_norm]] = v.strip().strip('"')
            # Always use subfields from top-level keys if present and not already set
            if employer_group_obj:
                filtered['employerGroups'] = {subk: employer_group_obj.get(subk, '') for subk in employer_group_keys}
            import sys
            print(f"[DEBUG] Filtered mappings to update: {filtered}", file=sys.stderr)
            print("[DEBUG] Mapping fields returned to UI:", list(filtered.keys()), file=sys.stderr)
            global current_mappings
            current_mappings.update(filtered)
            # Only return mappings for UI update
            return jsonify({'success': True, 'processing': False, 'mappings': filtered})
        return jsonify(result)
    except Exception as e:
        # If the error is about Databricks IP ACL, provide a clear message
        error_msg = str(e)
        print(f"[ERROR] LLM mapping generation failed: {error_msg}", file=sys.stderr)
        if 'blocked by Databricks IP ACL' in error_msg or '403' in error_msg:
            return jsonify({'error': 'Access denied: Your IP address is blocked by Databricks IP ACL. Please contact your Databricks admin to allow your IP or use an allowed network.', 'processing': False}), 403
        return jsonify({'error': f'Failed to generate LLM mappings: {error_msg}', 'processing': False}), 500

def validate_mapping_expression(expression):
    """Basic validation for mapping expressions"""
    # Check for common Python function patterns
    allowed_functions = ['upper', 'lower', 'strip', 'title', 'replace', 'substring', 'left', 'right']
    
    # Remove whitespace and check if expression contains valid patterns
    cleaned_expr = expression.replace(' ', '').lower()
    
    # Allow field names, function calls, and basic operators
    pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*(\([^)]*\))?(\.[a-zA-Z_][a-zA-Z0-9_]*(\([^)]*\))?)*$'
    
    if re.match(pattern, expression.replace(' ', '')):
        return True
    
    # Additional validation for compound expressions
    if any(func in cleaned_expr for func in allowed_functions):
        return True
    
    return False

def apply_transformation(expression, sample_data):
    """Apply transformation to sample data for preview"""
    # This is a simplified transformation engine
    # In a production environment, you'd want more robust error handling
    
    result = sample_data
    
    # Parse and apply transformations
    if 'upper(' in expression.lower():
        result = result.upper()
    elif 'lower(' in expression.lower():
        result = result.lower()
    elif 'strip(' in expression.lower() or 'trim(' in expression.lower():
        result = result.strip()
    elif 'title(' in expression.lower():
        result = result.title()
    
    return result

@app.route('/export_mappings', methods=['GET'])
def export_mappings():
    """Export current mappings as JSON"""
    return jsonify({
        'mappings': current_mappings,
        'source_headers': current_source_headers,
        'stage_fields': STAGE_FIELDS
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
