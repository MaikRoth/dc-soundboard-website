import os
import json
from flask import Flask, request, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
UPLOAD_FOLDER = 'uploads'
SOUND_FILES_JSON = 'sound_files.json'
ALLOWED_EXTENSIONS = {'mp3'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'supersecretkey'  # Needed for flash messages

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    if os.path.exists(SOUND_FILES_JSON):
        with open(SOUND_FILES_JSON, 'r') as f:
            sound_files = json.load(f)["sounds"]
    else:
        sound_files = []
    return render_template('index.html', sounds=sound_files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files or 'name' not in request.form:
        flash('No file or name provided')
        return redirect(request.url)
    file = request.files['file']
    name = request.form['name'].strip()
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(name) + '.mp3'
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            file.save(filepath)
            if os.path.exists(SOUND_FILES_JSON):
                with open(SOUND_FILES_JSON, 'r') as f:
                    sound_files = json.load(f)["sounds"]
            else:
                sound_files = []
            sound_files.append(name)
            with open(SOUND_FILES_JSON, 'w') as f:
                json.dump({"sounds": sound_files}, f)
            flash('File successfully uploaded and saved')
        else:
            flash('File with this name already exists')
        return redirect(url_for('index'))
    else:
        flash('Invalid file type')
        return redirect(request.url)

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
