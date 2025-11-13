from flask import Flask, request, jsonify, render_template, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# Инициализация путей для шаблонов и статических файлов
frontend_folder = os.path.join(os.getcwd(), 'frontend')
static_css_folder = os.path.join(os.getcwd(), 'static')

app = Flask(__name__, template_folder=frontend_folder, static_folder=static_css_folder)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.abspath('backend/data/cosmetics.db')}"
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация базы данных и авторизации
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Модели базы данных
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    scans = db.relationship('Scan', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class Scan(db.Model):
    __tablename__ = 'scans'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    input_type = db.Column(db.String(50))
    input_method = db.Column(db.String(50))
    original_text = db.Column(db.Text)
    ingredients_detected = db.Column(db.JSON)
    image_filename = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'input_type': self.input_type,
            'input_method': self.input_method,
            'original_text': self.original_text,
            'ingredients_detected': self.ingredients_detected,
            'image_filename': self.image_filename,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Загрузка файлов
def save_uploaded_file(file):
    """Сохраняет загруженный файл"""
    import uuid
    from datetime import datetime
    
    uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    
    file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{file_ext}"
    filepath = os.path.join(uploads_dir, filename)
    
    file.save(filepath)
    return filename

# Простой анализ текста
def check_ingredients(text):
    ingredients = []
    
    if "sodium laureth sulfate" in text.lower():
        ingredients.append({
            "name": "Sodium Laureth Sulfate",
            "risk_level": "medium",
            "category": "surfactant",
            "description": "Пінник, може викликати подразнення шкіри"
        })
    
    if "methylparaben" in text.lower():
        ingredients.append({
            "name": "Methylparaben", 
            "risk_level": "medium",
            "category": "preservative",
            "description": "Консервант з можливим гормональним впливом"
        })
    
    if "parfum" in text.lower():
        ingredients.append({
            "name": "Parfum",
            "risk_level": "high", 
            "category": "fragrance",
            "description": "Ароматизатор, може викликати алергії"
        })
    
    return ingredients

# Загрузка текстовых файлов
@app.route('/api/upload_text_file', methods=['POST'])
@login_required
def upload_text_file():
    try:
        file = request.files.get('file')
        if not file:
            return jsonify({"status": "error", "message": "Файл не загружен"}), 400
        
        text = file.read().decode('utf-8')
        ingredients = check_ingredients(text)

        scan_id = None
        if current_user.is_authenticated:
            scan = Scan(
                user_id=current_user.id,
                input_type='manual',
                input_method='file',
                original_text=text,
                ingredients_detected=ingredients
            )
            db.session.add(scan)
            db.session.commit()
            scan_id = scan.id

        return jsonify({
            "status": "success", 
            "text": text,
            "ingredients": ingredients,
            "scan_id": scan_id
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Анализ изображений
@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        file = request.files.get('image')
        if not file:
            return jsonify({"status": "error", "message": "Файл зображення не знайдено"}), 400

        # Пример обработки изображения (заменить на OCR)
        text = extract_text(file)
        ingredients = check_ingredients(text)

        scan_id = None
        if current_user.is_authenticated:
            file.stream.seek(0)
            scan = Scan(
                user_id=current_user.id,
                input_type='camera',
                input_method='photo', 
                original_text=text,
                image_filename=save_uploaded_file(file),
                ingredients_detected=ingredients
            )
            db.session.add(scan)
            db.session.commit()
            scan_id = scan.id

        return jsonify({
            "status": "success", 
            "text": text,
            "ingredients": ingredients,
            "scan_id": scan_id
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Инициализация базы данных
def init_db():
    with app.app_context():
        db.create_all()
        print("✅ База даних створена")

@app.route('/api/status', methods=['GET'])
@login_required
def api_status():
    """Проверка статуса аутентификации пользователя"""
    return jsonify({
        "status": "authenticated",
        "user": current_user.to_dict()
    })

# Функция для загрузки главной страницы
@app.route('/')
def index():
    return render_template('index.html')

# Функция user_loader, необходимая для Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

if __name__ == '__main__':
    init_db()  # Инициализация базы данных при старте
    print("🚀 Запуск додатка...")
    app.run(debug=True)
