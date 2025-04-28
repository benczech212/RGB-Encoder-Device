# main.py
from flask import Flask, render_template, request, jsonify, send_from_directory
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBAPP_DIR = os.path.join(BASE_DIR, '../webapp')

app = Flask(__name__, static_folder=os.path.join(WEBAPP_DIR, 'static'), template_folder=WEBAPP_DIR)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/<filename>')
def serve_html_pages(filename):
    if filename.endswith(".html"):
        return send_from_directory(WEBAPP_DIR, filename)
    return "Not found", 404

@app.route('/set_color', methods=['POST'])
def set_color():
    # example stub — update for HSL/HSV as needed
    r = int(request.form.get('r', 0))
    g = int(request.form.get('g', 0))
    b = int(request.form.get('b', 0))
    print(f"New RGB color: ({r}, {g}, {b})")
    return jsonify(success=True)

if __name__ == '__main__':
    os.chdir(WEBAPP_DIR)
    print(f"Running from: {WEBAPP_DIR}")
    app.run(debug=True)
