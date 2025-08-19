
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from flask import Flask, request, render_template_string, send_from_directory
from werkzeug.utils import secure_filename
from llm_mapper_full import process_domain_model
from sql_generator_full import generate_sql_scripts

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
SCRIPTS_FOLDER = os.path.join(os.path.dirname(__file__), 'scripts')
ALLOWED_EXTENSIONS = {'xlsx', 'csv', 'txt'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

HTML_FORM = '''
<!doctype html>
<title>LLM SQL Script Generator</title>
<h2>Upload Domain Model, Data Dictionary, and Source File</h2>
<form method=post enctype=multipart/form-data>
  Domain Model: <input type=file name=domain_model><br><br>
  Data Dictionary: <input type=file name=data_dict><br><br>
  Source File: <input type=file name=source_file><br><br>
  <input type=submit value=Upload>
</form>
{% if sql_script %}
  <h3>Generated SQL Script:</h3>
  <pre>{{ sql_script }}</pre>
  <a href="/download/{{ script_filename }}">Download Script</a>
{% endif %}
'''

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def upload_files():
    sql_script = None
    script_filename = None
    if request.method == 'POST':
        files = {}
        for key in ['domain_model', 'data_dict', 'source_file']:
            file = request.files.get(key)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                files[key] = filename
        if len(files) == 3:
            domain_model_path = os.path.join(UPLOAD_FOLDER, files['domain_model'])
            data_dict_path = os.path.join(UPLOAD_FOLDER, files['data_dict'])
            source_file_path = os.path.join(UPLOAD_FOLDER, files['source_file'])
            # Process and generate script
            process_domain_model(domain_model_path, data_dict_path)
            generate_sql_scripts(domain_model_path, data_dict_path, source_file_path, SCRIPTS_FOLDER)
            # Find the generated script (assume .sql file)
            scripts = [f for f in os.listdir(SCRIPTS_FOLDER) if f.endswith('.sql')]
            if scripts:
                script_filename = scripts[0]
                with open(os.path.join(SCRIPTS_FOLDER, script_filename)) as f:
                    sql_script = f.read()
    return render_template_string(HTML_FORM, sql_script=sql_script, script_filename=script_filename)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(SCRIPTS_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(SCRIPTS_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=5001, debug=True)
