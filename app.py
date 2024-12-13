from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import PyPDF2
import google.generativeai as genai
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract

app = Flask(__name__)

# Конфигурация ключа API и папки для загрузки файлов
GEMENI_API_KEY = "AIzaSyDlrwNCFtUiAR2EeFKY2lElnj3cgFxdNK8"  # Убедитесь, что API ключ правильный
app.secret_key = 'SKILLSET_JUNIORS'  # Секретный ключ для сессий

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blox.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'  # Укажите папку для загрузки файлов

db = SQLAlchemy(app)

# Модель базы данных для пользователей
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"

# Модель базы данных для расходов
# class Expense(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     amount = db.Column(db.Float, nullable=False)
#     category = db.Column(db.String(120), nullable=False)
#     description = db.Column(db.String(255))
#     date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Expense {self.amount} {self.category}>"

# Создание базы данных
with app.app_context():
    db.create_all()


# Главная страница
@app.route("/")
def index():
    return render_template("index.html")

@app.template_filter('format_date')
def format_date(value):
    if isinstance(value, (datetime, datetime.date)):
        return value.strftime('%d-%m-%Y')
    return value

@app.route("/features")
def features():
    return render_template("features.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/AntiSpam")
def AntiSpam():
    return render_template("AntiSpam.html")

@app.route("/digital")
def digital():
    return render_template("digital.html")

# Маршрут для главной страницы расходов
# #  @app.route('/expense', methods=['GET', 'POST'])
# # def expense():
# #     if request.method == 'POST':
# #         amount = float(request.form['amount'])
# #         category = request.form['category']
# #         description = request.form['description']
        
# #         # Добавление расхода в базу данных
#         new_expense = Expense(amount=amount, category=category, description=description)
#         db.session.add(new_expense)
#         db.session.commit()
        
#         return redirect(url_for('expense'))
    
#     expenses = Expense.query.order_by(Expense.date.desc()).all()
#     total_expenses = sum(expense.amount for expense in expenses)
    
#     return render_template('expense.html', expenses=expenses, total_expenses=total_expenses)

# # Маршрут для удаления расхода
# @app.route('/delete/<int:expense_id>')
# def delete(expense_id):
#     expense_to_delete = Expense.query.get_or_404(expense_id)
#     db.session.delete(expense_to_delete)
#     db.session.commit()
    
#     return redirect(url_for('expense'))

# Configure Gemini API
genai.configure(api_key=GEMENI_API_KEY)  # Используем ваш API ключ
model = genai.GenerativeModel(
    'models/gemini-1.5-flash', 
    system_instruction="You are a professional lawyer who analyzes documents for scams."
)

def extract_text_from_file(file):
    """Extract text from different file types"""
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # PDF extraction
    if filename.lower().endswith('.pdf'):
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
        return text

    # Image extraction (OCR)
    elif filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
        image = Image.open(filepath)
        text = pytesseract.image_to_string(image)
        return text

    return ""

def analyze_text_for_scam(text):
    """Analyze text using Gemini API for potential scam indicators"""
    prompt = f"""
    Analyze the following text for potential scam indicators. 
    Provide a structured response with:
    1. Scam Risk Level (Low/Medium/High)
    2. Suspicious Phrases or Keywords
    3. Red Flags
    4. Recommended Actions

    If text in russian, provide an answer in russian. Otherwise, English.

    Text to analyze:
    {text}
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Analysis Error: {str(e)}"

@app.route('/AntiSpam', methods=['POST'])
def analyze():
    # Text input analysis
    text_input = request.form.get('text_input', '')
    
    # File input analysis
    file = request.files.get('file_input')
    
    if file and file.filename:
        text_input = extract_text_from_file(file)
    
    if not text_input:
        return jsonify({"error": "No text provided for analysis"})

    analysis_result = analyze_text_for_scam(text_input)
    return jsonify({"result": analysis_result})

@app.route('/ask_question', methods=['POST'])
def ask_question():
    # Get the question from the form data
    question = request.form.get('question')

    # Validate that a question was provided
    if not question:
        return jsonify({"answer": "No question provided."}), 400

    try:
        # Create the prompt (adjust if necessary)
        prompt = f'Answer this question: {question}'
        
        # Generate the content using the model
        response = model.generate_content(prompt)
        
        # Check if the response has the 'text' attribute
        if hasattr(response, 'text'):
            return jsonify({"answer": response.text})
        else:
            return jsonify({"answer": "Model response did not contain expected text."}), 500

    except Exception as e:
        # If any error occurs during generation, log and return a friendly error message
        print(f"Error generating response: {e}")
        return jsonify({"answer": "Sorry, there was an error while processing your question."}), 500

if __name__ == "__main__":
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)  # Создание папки для загрузок
    app.run(host="2a0d:b201:14:5143:48bd:375a:6d7f:3a6c", port=5000, debug=True)













