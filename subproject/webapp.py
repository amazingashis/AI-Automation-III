
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from flask import Flask, request, render_template_string, send_from_directory
from werkzeug.utils import secure_filename
from sql_generator_full import generate_sql_scripts


UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
DOMAIN_MODEL_FOLDER = os.path.join(UPLOAD_FOLDER, 'domain_model')
DATA_DICT_FOLDER = os.path.join(UPLOAD_FOLDER, 'data_dict')
SOURCE_FILE_FOLDER = os.path.join(UPLOAD_FOLDER, 'source_file')
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
        upload_dirs = {
            'domain_model': DOMAIN_MODEL_FOLDER,
            'data_dict': DATA_DICT_FOLDER,
            'source_file': SOURCE_FILE_FOLDER
        }
        for key in ['domain_model', 'data_dict', 'source_file']:
            file = request.files.get(key)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                save_dir = upload_dirs[key]
                os.makedirs(save_dir, exist_ok=True)
                file_path = os.path.join(save_dir, filename)
                file.save(file_path)
                files[key] = file_path
        if len(files) == 3:
            domain_model_path = files['domain_model']
            data_dict_path = files['data_dict']
            source_file_path = files['source_file']
            # Generate SQL script directly
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
    os.makedirs(DOMAIN_MODEL_FOLDER, exist_ok=True)
    os.makedirs(DATA_DICT_FOLDER, exist_ok=True)
    os.makedirs(SOURCE_FILE_FOLDER, exist_ok=True)
    os.makedirs(SCRIPTS_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=5001, debug=True)
