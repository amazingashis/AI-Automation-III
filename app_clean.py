from flask import Flask, render_template, request, jsonify, redirect, url_for
import csv
import os
import json
from werkzeug.utils import secure_filename
import re
from llm_mapper import generate_mappings as llm_generate_mappings

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

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
    'Employer Group: groupName',
    'Employer Group: groupStatus',
    'Employer Group: addressLine1',
    'Employer Group: addressLine2',
    'Employer Group: zip'
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
current_source_data = []

# LMStudio configuration
LMSTUDIO_BASE_URL = "http://localhost:1234/v1"
LLM_MODEL = "google/gemma-3n-e4b"

@app.route('/')
def index():
    return render_template('index.html', 
                         stage_fields=STAGE_FIELDS, 
                         transformation_rules=TRANSFORMATION_RULES,
                         source_headers=current_source_headers,
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
    
    if not stage_field or not mapping_expression:
        return jsonify({'error': 'Stage field and mapping expression are required'}), 400
    
    # Validate the mapping expression (basic validation)
    if validate_mapping_expression(mapping_expression):
        current_mappings[stage_field] = mapping_expression
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
    """API endpoint to generate mappings using LLM."""
    
    global current_source_headers, current_source_data
    
    if not current_source_headers:
        return jsonify({'error': 'No source file uploaded'}), 400
    
    try:
        # Get LMStudio configuration from request if provided
        data = request.get_json() or {}
        lmstudio_url = data.get('lmstudio_url', LMSTUDIO_BASE_URL)
        model = data.get('model', LLM_MODEL)
        
        # Generate mappings using the new LLM mapper module
        result = llm_generate_mappings(
            current_source_headers, 
            current_source_data[:10],  # Top 10 rows
            STAGE_FIELDS,
            lmstudio_url,
            model
        )
        
        if result['success']:
            # Update current mappings with LLM suggestions
            global current_mappings
            current_mappings.update(result['mappings'])
            
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate LLM mappings: {str(e)}'}), 500

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
