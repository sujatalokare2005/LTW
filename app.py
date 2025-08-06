from flask import Flask, render_template, request, redirect, url_for, session
import os
from PIL import Image, ImageOps, ImageFilter
import pytesseract
from pdf2image import convert_from_path
import google.generativeai as genai
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Change this to a secure random key!

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configure Gemini API
genai.configure(api_key="AIzaSyCuQclK-x6Jb0PUy0feddPThBMtO1Kt3Bs")

languages = ["English", "Hindi", "Marathi", "Spanish", "French", "German", "Chinese", "Japanese"]

def preprocess_image(image: Image.Image) -> Image.Image:
    grayscale = ImageOps.grayscale(image)
    contrast = ImageOps.autocontrast(grayscale)
    return contrast.filter(ImageFilter.MedianFilter())

def extract_text_from_image(image_path):
    try:
        image = Image.open(image_path)
        processed = preprocess_image(image)
        return pytesseract.image_to_string(processed)
    except Exception as e:
        return f"OCR Error (Image): {e}"

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        pages = convert_from_path(pdf_path)
        for page in pages:
            processed = preprocess_image(page)
            text += pytesseract.image_to_string(processed) + "\n"
        return text.strip()
    except Exception as e:
        return f"OCR Error (PDF): {e}"

@app.route('/', methods=['GET'])
def index():
    # Get stored session data
    result = session.pop('result', None)
    user_text = session.pop('user_text', '')
    selected_language = session.pop('selected_language', '')

    return render_template('index.html',
                           result=result,
                           languages=languages,
                           user_text=user_text,
                           selected_language=selected_language)

@app.route('/', methods=['POST'])
def translate():
    user_text = request.form.get('text', '').strip()
    target_lang = request.form['language']
    file = request.files.get('file')
    extracted_text = ""

    if file and file.filename:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                extracted_text = extract_text_from_image(filepath)
            elif filename.lower().endswith('.pdf'):
                extracted_text = extract_text_from_pdf(filepath)
            else:
                extracted_text = "Unsupported file type."
        except Exception as e:
            extracted_text = f"OCR Error: {e}"

    text_to_translate = extracted_text or user_text

    if text_to_translate and not text_to_translate.lower().startswith("ocr error"):
        prompt = f"Translate the following to {target_lang}:\n{text_to_translate}"
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            result = response.text
        except Exception as e:
            result = f"Error translating: {e}"
    else:
        result = extracted_text or "No text found to translate."

    # Store results and inputs in session
    session['result'] = result
    session['user_text'] = user_text
    session['selected_language'] = target_lang

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
