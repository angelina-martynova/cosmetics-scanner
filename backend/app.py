from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from ocr import extract_text
from checker import IngredientChecker
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
login_manager.login_view = 'login_page'

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

# Аутентификация
@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/scans')
@login_required
def scans_page():
    return render_template('scans.html')

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"status": "error", "message": "Електронна пошта та пароль обов'язкові"}), 400
        
        # Проверяем существует ли пользователь
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({"status": "error", "message": "Користувач з такою поштою вже існує"}), 400
        
        # Создаем нового пользователя
        new_user = User(email=email)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            "status": "success", 
            "message": "Реєстрація успішна! Тепер ви можете увійти."
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"status": "error", "message": "Електронна пошта та пароль обов'язкові"}), 400
        
        # Ищем пользователя
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            return jsonify({"status": "error", "message": "Невірна електронна пошта або пароль"}), 401
        
        # Обновляем время последнего входа
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Логиним пользователя
        login_user(user)
        
        return jsonify({
            "status": "success", 
            "message": "Вхід успішний!",
            "user": user.to_dict()
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"status": "success", "message": "Вихід успішний"})

# API для управления сканированиями
@app.route('/api/scans', methods=['GET'])
@login_required
def get_user_scans():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        scans = Scan.query.filter_by(user_id=current_user.id)\
                         .order_by(Scan.created_at.desc())\
                         .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            "status": "success",
            "scans": [scan.to_dict() for scan in scans.items],
            "total": scans.total,
            "pages": scans.pages,
            "current_page": page
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/scans/<int:scan_id>', methods=['GET'])
@login_required
def get_scan(scan_id):
    try:
        scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first()
        
        if not scan:
            return jsonify({"status": "error", "message": "Сканування не знайдено"}), 404
            
        return jsonify({
            "status": "success",
            "scan": scan.to_dict()
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/scans/<int:scan_id>', methods=['DELETE'])
@login_required
def delete_scan(scan_id):
    try:
        scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first()
        
        if not scan:
            return jsonify({"status": "error", "message": "Сканування не знайдено"}), 404
        
        db.session.delete(scan)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Сканування успішно видалено"
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/scans/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_scans():
    try:
        data = request.get_json()
        scan_ids = data.get('scan_ids', [])
        
        if not scan_ids:
            return jsonify({"status": "error", "message": "Не вказано сканувань для видалення"}), 400
        
        # Удаляем только сканирования принадлежащие текущему пользователю
        scans_to_delete = Scan.query.filter(
            Scan.id.in_(scan_ids),
            Scan.user_id == current_user.id
        ).all()
        
        for scan in scans_to_delete:
            db.session.delete(scan)
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": f"Успішно видалено {len(scans_to_delete)} сканувань"
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Загрузка текстовых файлов
@app.route('/api/upload_text_file', methods=['POST'])
def upload_text_file():
    try:
        print("Received file upload request")
        
        if 'file' not in request.files:
            print("No file in request")
            return jsonify({"status": "error", "message": "Файл не загружен"}), 400
        
        file = request.files['file']
        print(f"File received: {file.filename}, {file.content_type}")
        
        if file.filename == '':
            print("Empty filename")
            return jsonify({"status": "error", "message": "Файл не выбран"}), 400
        
        # Проверяем расширение файла
        allowed_extensions = {'.txt', '.doc', '.docx', '.pdf'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            print(f"Unsupported file extension: {file_ext}")
            return jsonify({"status": "error", "message": f"Неподдерживаемый формат файла: {file_ext}"}), 400
        
        # Читаем содержимое файла
        try:
            if file_ext == '.txt':
                text = file.read().decode('utf-8')
            elif file_ext in {'.doc', '.docx', '.pdf'}:
                # Пока возвращаем заглушку для нетекстовых форматов
                text = f"[Файл {file.filename} - для обработки .doc/.docx/.pdf нужны дополнительные библиотеки]"
            else:
                text = file.read().decode('utf-8', errors='ignore')
                
            print(f"File content length: {len(text)}")
            
        except Exception as e:
            print(f"Error reading file: {e}")
            return jsonify({"status": "error", "message": f"Ошибка чтения файла: {str(e)}"}), 400
        
        # Анализируем ингредиенты
        ingredients = check_ingredients(text)
        print(f"Found ingredients: {len(ingredients)}")

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
            print(f"Scan saved with ID: {scan_id}")

        return jsonify({
            "status": "success", 
            "text": text,
            "ingredients": ingredients,
            "scan_id": scan_id
        })
        
    except Exception as e:
        print(f"Error in upload_text_file: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500  

# Aнализ текста Checker.py
ingredient_checker = IngredientChecker()

def check_ingredients(text):
    """Проверка текста на наличие опасных ингредиентов"""
    if not text:
        return []
    
    return ingredient_checker.find_ingredients(text)

# Анализ текста (ручной ввод)
@app.route('/api/analyze_text', methods=['POST'])
def analyze_text():
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"status": "error", "message": "Текст не предоставлен"}), 400
        
        text = data['text']
        ingredients = check_ingredients(text)

        scan_id = None
        if current_user.is_authenticated:
            scan = Scan(
                user_id=current_user.id,
                input_type='manual',
                input_method='text',
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

        # OCR обработка изображения
        text = extract_text(file)
        ingredients = check_ingredients(text)

        scan_id = None
        if current_user.is_authenticated:
            # Сохраняем только информацию о сканировании, НЕ сохраняем файл
            scan = Scan(
                user_id=current_user.id,
                input_type='camera',
                input_method='photo', 
                original_text=text,
                image_filename=None,  # Не сохраняем файл
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