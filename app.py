import os
import fitz  # PyMuPDF
from docx import Document
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from mistralai.client import MistralClient
import google.generativeai as genai
from database import db, User, Summary
import tempfile
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///summarization.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# API Keys (replace with your actual keys)
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY', '8G1wusJZc0WG10IVBuzqvrVYIMxOSW2O')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyA7N2IsdchHxteEgkW81hf0bpgtoUWqPvs')

# Initialize AI clients
mistral_client = MistralClient(api_key=MISTRAL_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.0-flash')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Language mapping for prompts
LANGUAGE_PROMPTS = {
    'english': 'Provide the summary in English',
    'spanish': 'Proporcione el resumen en español',
    'french': 'Fournissez le résumé en français',
    'german': 'Geben Sie die Zusammenfassung auf Deutsch',
    'italian': 'Fornisci il riassunto in italiano',
    'portuguese': 'Forneça o resumo em português',
    'hindi': 'सारांश हिंदी में प्रदान करें',
    'kannada': 'ಸಾರಾಂಶವನ್ನು ಕನ್ನಡದಲ್ಲಿ ನೀಡಿ',
    'chinese': '用中文提供摘要',
    'japanese': '要約を日本語で提供する'
}

def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    try:
        text = ""
        with fitz.open(file_path) as pdf:
            for page in pdf:
                text += page.get_text()
        return text.strip()
    except Exception as e:
        raise Exception(f"Error reading PDF: {e}")

def extract_text_from_docx(file_path):
    """Extract text from DOCX file"""
    try:
        doc = Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Error reading DOCX: {e}")

def extract_text_from_txt(file_path):
    """Extract text from TXT file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except Exception as e:
        raise Exception(f"Error reading TXT file: {e}")

def create_summary_prompt(text, summary_type, language):
    """Create prompt for summarization"""
    # Truncate text if too long
    if len(text) > 10000:
        text = text[:10000] + "\n\n[Document truncated for length...]"
    
    summary_types = {
        'concise': 'Provide a CONCISE summary in 2-3 paragraphs',
        'detailed': 'Provide a DETAILED and comprehensive summary in 4-6 paragraphs',
        'bullet': 'Provide a summary in BULLET POINT format',
        'executive': 'Provide an EXECUTIVE SUMMARY in 1 paragraph'
    }
    
    base_instruction = summary_types.get(summary_type, summary_types['concise'])
    language_instruction = LANGUAGE_PROMPTS.get(language, LANGUAGE_PROMPTS['english'])
    
    prompt = f"""
    DOCUMENT TO SUMMARIZE:
    ```text
    {text}
    ```

    INSTRUCTIONS:
    {base_instruction}
    {language_instruction}

    Please provide a well-structured, professional summary that accurately captures the essence of the document.

    IMPORTANT: 
    - Maintain the original meaning and facts
    - Use clear, professional language
    - Structure the summary logically
    - Highlight the most important information

    SUMMARY:
    """
    
    return prompt

def generate_mistral_summary(text, summary_type, language):
    """Generate summary using Mistral AI"""
    try:
        prompt = create_summary_prompt(text, summary_type, language)
        
        messages = [{"role": "user", "content": prompt}]
        
        chat_response = mistral_client.chat(
            model="mistral-large-latest",
            messages=messages
        )
        
        return chat_response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Mistral AI error: {e}")

def generate_gemini_summary(text, summary_type, language):
    """Generate summary using Google Gemini"""
    try:
        prompt = create_summary_prompt(text, summary_type, language)
        
        chat = gemini_model.start_chat(history=[])
        response = chat.send_message(prompt)
        
        return response.text
    except Exception as e:
        raise Exception(f"Gemini AI error: {e}")

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    recent_summaries = Summary.query.filter_by(user_id=current_user.id)\
        .order_by(Summary.created_at.desc()).limit(5).all()
    return render_template('dashboard.html', summaries=recent_summaries)

@app.route('/upload')
@login_required
def upload():
    return render_template('upload.html')

@app.route('/history')
@login_required
def history():
    summaries = Summary.query.filter_by(user_id=current_user.id)\
        .order_by(Summary.created_at.desc()).all()
    return render_template('history.html', summaries=summaries)

@app.route('/summarize', methods=['POST'])
@login_required
def summarize():
    try:
        text = request.form.get('text', '')
        file = request.files.get('file')
        model_choice = request.form.get('model', 'mistral')
        language = request.form.get('language', 'english')
        summary_type = request.form.get('summary_type', 'concise')
        filename = None
        
        # Handle file upload
        if file and file.filename:
            filename = file.filename
            file_extension = filename.rsplit('.', 1)[1].lower()
            
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_file:
                file.save(temp_file.name)
                
                if file_extension == 'pdf':
                    text = extract_text_from_pdf(temp_file.name)
                elif file_extension == 'docx':
                    text = extract_text_from_docx(temp_file.name)
                elif file_extension == 'txt':
                    text = extract_text_from_txt(temp_file.name)
                else:
                    return jsonify({'error': 'Unsupported file format'}), 400
            
            # Clean up temporary file
            os.unlink(temp_file.name)
        
        if not text.strip():
            return jsonify({'error': 'No text provided for summarization'}), 400
        
        # Generate summary based on model choice
        if model_choice == 'mistral':
            summary = generate_mistral_summary(text, summary_type, language)
        else:
            summary = generate_gemini_summary(text, summary_type, language)
        
        # Save to database
        new_summary = Summary(
            user_id=current_user.id,
            original_text=text[:1000] + "..." if len(text) > 1000 else text,
            summary=summary,
            model_used=model_choice,
            language=language,
            summary_type=summary_type,
            filename=filename
        )
        db.session.add(new_summary)
        db.session.commit()
        
        return jsonify({
            'summary': summary,
            'summary_id': new_summary.id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
from flask import jsonify
import json
from datetime import datetime, timedelta

# Add this route to app.py
@app.route('/analytics')
@login_required
def analytics():
    # Get user's summaries for analytics
    summaries = Summary.query.filter_by(user_id=current_user.id).all()
    
    # Calculate statistics
    total_summaries = len(summaries)
    mistral_count = len([s for s in summaries if s.model_used == 'mistral'])
    gemini_count = len([s for s in summaries if s.model_used == 'gemini'])
    
    # Language distribution
    language_stats = {}
    for summary in summaries:
        lang = summary.language
        language_stats[lang] = language_stats.get(lang, 0) + 1
    
    # Summary type distribution
    type_stats = {}
    for summary in summaries:
        summary_type = summary.summary_type
        type_stats[summary_type] = type_stats.get(summary_type, 0) + 1
    
    # Recent activity (last 7 days)
    recent_summaries = Summary.query.filter(
        Summary.user_id == current_user.id,
        Summary.created_at >= datetime.utcnow() - timedelta(days=7)
    ).all()
    
    # Mock accuracy data (in real app, you'd calculate this based on user feedback)
    accuracy_data = {
        'mistral': 85,
        'gemini': 78,
        'overall': 82
    }
    
    return render_template('analytics.html',
                         total_summaries=total_summaries,
                         mistral_count=mistral_count,
                         gemini_count=gemini_count,
                         language_stats=language_stats,
                         type_stats=type_stats,
                         recent_summaries=len(recent_summaries),
                         accuracy_data=accuracy_data)

@app.route('/api/analytics-data')
@login_required
def analytics_data():
    summaries = Summary.query.filter_by(user_id=current_user.id).all()
    
    # Model usage data
    model_data = {
        'Mistral AI': len([s for s in summaries if s.model_used == 'mistral']),
        'Google Gemini': len([s for s in summaries if s.model_used == 'gemini'])
    }
    
    # Language distribution
    language_data = {}
    for summary in summaries:
        lang = summary.language.title()
        language_data[lang] = language_data.get(lang, 0) + 1
    
    # Summary type distribution
    type_data = {}
    for summary in summaries:
        stype = summary.summary_type.title()
        type_data[stype] = type_data.get(stype, 0) + 1
    
    # Accuracy comparison (mock data - in production, use actual accuracy metrics)
    accuracy_comparison = {
        'Mistral AI': 85,
        'Google Gemini': 78
    }
    
    return jsonify({
        'model_usage': model_data,
        'language_distribution': language_data,
        'type_distribution': type_data,
        'accuracy_comparison': accuracy_comparison
    })
@app.route('/summary/<int:summary_id>')
@login_required
def view_summary(summary_id):
    summary = Summary.query.filter_by(id=summary_id, user_id=current_user.id).first_or_404()
    return render_template('summary.html', summary=summary)

# Initialize database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)