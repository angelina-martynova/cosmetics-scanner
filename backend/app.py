from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from ocr import extract_text
from checker import IngredientChecker
from export import ScanExporter
import os
import json

frontend_folder = os.path.join(os.getcwd(), 'frontend')
static_css_folder = os.path.join(os.getcwd(), 'static')

app = Flask(__name__, template_folder=frontend_folder, static_folder=static_css_folder)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:AdminPostgres123!@localhost:5432/cosmetics_db'
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

scan_exporter = ScanExporter()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    scans = db.relationship('Scan', backref='user', lazy=True, cascade="all, delete-orphan")

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
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

class Ingredient(db.Model):
    __tablename__ = 'ingredients'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    risk_level = db.Column(db.String(20), default='medium')
    category = db.Column(db.String(50))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'risk_level': self.risk_level,
            'category': self.category,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

class Scan(db.Model):
    __tablename__ = 'scans'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    input_type = db.Column(db.String(50))
    input_method = db.Column(db.String(50))
    original_text = db.Column(db.Text)
    safety_status = db.Column(db.String(20), default='safe')
    image_filename = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    ingredients_detected = db.Column(db.JSON)

    def get_ingredients_list(self):
        if not self.ingredients_detected:
            return []
        
        try:
            if isinstance(self.ingredients_detected, str):
                ingredients = json.loads(self.ingredients_detected)
            else:
                ingredients = self.ingredients_detected
            
            if isinstance(ingredients, list):
                return ingredients
            
            return []
            
        except (json.JSONDecodeError, TypeError):
            return []

    def to_dict(self):
        ingredients_list = self.get_ingredients_list()
        
        safety_status = self.safety_status
        if not safety_status and ingredients_list:
            high_risk_count = sum(1 for ing in ingredients_list 
                                if isinstance(ing, dict) and ing.get('risk_level') == 'high')
            if high_risk_count > 0:
                safety_status = 'danger'
            elif len(ingredients_list) > 0:
                safety_status = 'warning'
            else:
                safety_status = 'safe'
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'input_type': self.input_type,
            'input_method': self.input_method,
            'original_text': self.original_text,
            'safety_status': safety_status or 'safe',
            'image_filename': self.image_filename,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'ingredients': ingredients_list,
            'ingredients_count': len(ingredients_list)
        }

def save_uploaded_file(file):
    import uuid
    from datetime import datetime
    
    uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    
    file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{file_ext}"
    filepath = os.path.join(uploads_dir, filename)
    
    file.save(filepath)
    return filename

ingredient_checker = IngredientChecker()

def check_ingredients(text):
    if not text:
        return []
    return ingredient_checker.find_ingredients(text)

def create_scan(user_id, text, detected_ingredients, input_type='manual', input_method='text'):
    safety_status = 'safe'
    
    ingredients_for_json = []
    if detected_ingredients:
        for ing in detected_ingredients:
            if isinstance(ing, dict):
                ingredients_for_json.append({
                    'id': ing.get('id', 0),
                    'name': ing.get('name', 'Unknown'),
                    'risk_level': ing.get('risk_level', 'medium'),
                    'category': ing.get('category', ''),
                    'description': ing.get('description', '')
                })
            else:
                ingredients_for_json.append({
                    'id': 0,
                    'name': str(ing),
                    'risk_level': 'unknown',
                    'category': '',
                    'description': ''
                })
        
        high_risk_count = sum(1 for ing in ingredients_for_json 
                            if ing.get('risk_level') == 'high')
        
        if high_risk_count > 0:
            safety_status = 'danger'
        elif len(ingredients_for_json) > 0:
            safety_status = 'warning'
        else:
            safety_status = 'safe'
    
    image_filename = None
    
    scan = Scan(
        user_id=user_id,
        input_type=input_type,
        input_method=input_method,
        original_text=text,
        safety_status=safety_status,
        image_filename=image_filename,
        ingredients_detected=ingredients_for_json
    )
    
    db.session.add(scan)
    db.session.commit()
    
    print(f"✅ Создан скан ID: {scan.id} с {len(ingredients_for_json)} ингредиентами")
    return scan.id

@app.route('/api/upload_text_file', methods=['POST'])
def upload_text_file():
    try:
        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "Файл не загружен"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"status": "error", "message": "Файл не выбран"}), 400
        
        allowed_extensions = {'.txt', '.doc', '.docx', '.pdf'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            return jsonify({"status": "error", "message": f"Неподдерживаемый формат файла: {file_ext}"}), 400
        
        try:
            if file_ext == '.txt':
                text = file.read().decode('utf-8')
            elif file_ext in {'.doc', '.docx', '.pdf'}:
                text = f"[Файл {file.filename} - для обработки .doc/.docx/.pdf нужны дополнительные библиотеки]"
            else:
                text = file.read().decode('utf-8', errors='ignore')
                
        except Exception as e:
            return jsonify({"status": "error", "message": f"Ошибка чтения файла: {str(e)}"}), 400
        
        detected_ingredients = check_ingredients(text)
        
        print(f"\n📁 Загружен текстовый файл: {file.filename}")
        print(f"📄 Текст: {text[:100]}...")
        print(f"🔍 Найдено ингредиентов: {len(detected_ingredients)}")

        scan_id = None
        if current_user.is_authenticated:
            scan_id = create_scan(
                user_id=current_user.id,
                text=text,
                detected_ingredients=detected_ingredients,
                input_type='manual',
                input_method='device'
            )

        return jsonify({
            "status": "success", 
            "text": text,
            "ingredients": detected_ingredients,
            "ingredients_count": len(detected_ingredients),
            "scan_id": scan_id
        })
        
    except Exception as e:
        print(f"❌ Ошибка в upload_text_file: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/analyze_text', methods=['POST'])
def analyze_text():
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"status": "error", "message": "Текст не предоставлен"}), 400
        
        text = data['text']
        detected_ingredients = check_ingredients(text)
        
        print(f"\n⌨️ Ручной ввод текста")
        print(f"📄 Текст: {text[:100]}...")
        print(f"🔍 Найдено ингредиентов: {len(detected_ingredients)}")

        scan_id = None
        if current_user.is_authenticated:
            scan_id = create_scan(
                user_id=current_user.id,
                text=text,
                detected_ingredients=detected_ingredients,
                input_type='manual',
                input_method='text'
            )

        return jsonify({
            "status": "success", 
            "text": text,
            "ingredients": detected_ingredients,
            "ingredients_count": len(detected_ingredients),
            "scan_id": scan_id
        })
    except Exception as e:
        print(f"❌ Ошибка в analyze_text: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
  
@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        file = request.files.get('image')
        if not file:
            return jsonify({"status": "error", "message": "Файл зображення не знайдено"}), 400

        input_method = request.form.get('input_method', 'camera')
        
        text = extract_text(file)
        detected_ingredients = check_ingredients(text)
        
        print(f"\n📸 Анализ изображения (метод: {input_method})")
        print(f"📄 Текст из OCR: {text[:100]}...")
        print(f"🔍 Найдено ингредиентов: {len(detected_ingredients)}")
        
        for ing in detected_ingredients:
            print(f"  • {ing.get('name')} (риск: {ing.get('risk_level')})")

        scan_id = None
        if current_user.is_authenticated:
            scan_id = create_scan(
                user_id=current_user.id,
                text=text,
                detected_ingredients=detected_ingredients,
                input_type='camera',
                input_method=input_method
            )

        return jsonify({
            "status": "success", 
            "text": text,
            "ingredients": detected_ingredients,
            "ingredients_count": len(detected_ingredients),
            "scan_id": scan_id
        })
    except Exception as e:
        print(f"❌ Ошибка в analyze: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/ingredients', methods=['GET'])
def get_ingredients():
    try:
        risk_level = request.args.get('risk_level')
        search = request.args.get('search')
        
        query = Ingredient.query
        
        if risk_level:
            query = query.filter_by(risk_level=risk_level)
        if search:
            query = query.filter(Ingredient.name.ilike(f'%{search}%'))
        
        ingredients = query.order_by(Ingredient.name).all()
        
        return jsonify({
            "status": "success",
            "count": len(ingredients),
            "ingredients": [ing.to_dict() for ing in ingredients]
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/scans', methods=['GET'])
@login_required
def get_user_scans():
    try:
        print(f"\n📋 Запрос сканов пользователя: {current_user.email}")
        
        scans = Scan.query.filter_by(user_id=current_user.id)\
                         .order_by(Scan.created_at.desc())\
                         .all()
        
        scans_data = []
        for scan in scans:
            scan_dict = scan.to_dict()
            
            ingredients_list = scan.get_ingredients_list()
            print(f"  Скан {scan.id}: {len(ingredients_list)} ингредиентов, статус: {scan.safety_status}")
            
            scans_data.append(scan_dict)
        
        print(f"📊 Всего сканов: {len(scans_data)}")
        
        return jsonify({
            "status": "success",
            "scans": scans_data,
            "total": len(scans_data),
            "user": current_user.email
        })
        
    except Exception as e:
        print(f"❌ Ошибка в get_user_scans: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/api/scans/<int:scan_id>', methods=['GET'])
@login_required
def get_scan(scan_id):
    try:
        scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first()
        
        if not scan:
            return jsonify({"status": "error", "message": "Сканування не знайдено"}), 404
        
        scan_data = scan.to_dict()
        
        ingredients_list = scan.get_ingredients_list()
        scan_data['ingredients_detailed'] = ingredients_list
        scan_data['ingredients_count'] = len(ingredients_list)
        
        return jsonify({
            "status": "success",
            "scan": scan_data
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

@app.route('/api/scans/<int:scan_id>/export/pdf', methods=['GET'])
@login_required
def export_scan_to_pdf(scan_id):
    """Экспорт одного скана в PDF"""
    try:
        scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first()
        
        if not scan:
            return jsonify({"status": "error", "message": "Сканування не знайдено"}), 404
        
        # Подготавливаем данные
        scan_data = scan.to_dict()
        ingredients_list = scan.get_ingredients_list()
        
        export_data = {
            'id': scan_data['id'],
            'created_at': scan_data['created_at'],
            'input_type': scan_data['input_type'],
            'input_method': scan_data['input_method'],
            'safety_status': scan_data['safety_status'],
            'original_text': scan_data['original_text'],
            'ingredients_count': scan_data['ingredients_count'],
            'ingredients_detailed': ingredients_list
        }
        
        print(f"📋 Экспорт скана {scan_id} в PDF")
        
        # Создаем PDF в памяти
        pdf_bytes = scan_exporter.create_pdf_bytes(export_data, current_user.email)
        
        # Отправляем PDF как ответ
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=scan_{scan_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        
        print(f"✅ PDF отправлен пользователю, размер: {len(pdf_bytes)} байт")
        return response
        
    except Exception as e:
        print(f"❌ Ошибка при экспорте в PDF: {str(e)}")
        return jsonify({"status": "error", "message": f"Помилка при створенні PDF: {str(e)}"}), 500
    
@app.route('/api/status', methods=['GET'])
@login_required
def api_status():
    return jsonify({
        "status": "authenticated",
        "user": current_user.to_dict()
    })

@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "Cosmetics Scanner API",
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/api/db-check')
def db_check():
    try:
        from sqlalchemy import text
        
        result = db.session.execute(text("SELECT version()"))
        postgres_version = result.fetchone()[0]
        
        scans = Scan.query.all()
        scans_with_ingredients = 0
        total_ingredients = 0
        
        for scan in scans:
            ingredients = scan.get_ingredients_list()
            if ingredients:
                scans_with_ingredients += 1
                total_ingredients += len(ingredients)
        
        return jsonify({
            "status": "connected",
            "database": {
                "type": "PostgreSQL",
                "version": postgres_version.split(',')[0],
                "name": "cosmetics_db"
            },
            "statistics": {
                "users": User.query.count(),
                "scans": len(scans),
                "scans_with_ingredients": scans_with_ingredients,
                "total_ingredients_found": total_ingredients,
                "average_ingredients_per_scan": round(total_ingredients / len(scans), 2) if scans else 0
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@app.route('/api/simple-check')
def simple_check():
    return jsonify({
        "service": "Cosmetics Scanner API",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "db_check": "/api/db-check",
            "register": "/api/register",
            "login": "/api/login",
            "analyze": "/api/analyze",
            "analyze_text": "/api/analyze_text",
            "ingredients": "/api/ingredients",
            "scans": "/api/scans",
            "export_pdf": "/api/scans/{id}/export/pdf",
            "export_multiple": "/api/scans/export-multiple/pdf"
        }
    })

@app.route('/api/test-checker', methods=['POST'])
def test_checker():
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            text = "Состав: Aqua, Sodium Laureth Sulfate, Parfum, Methylparaben, Formaldehyde"
        
        detected = check_ingredients(text)
        
        return jsonify({
            "status": "success",
            "text": text,
            "ingredients_found": len(detected),
            "ingredients": detected,
            "checker_info": {
                "total_ingredients_in_checker": len(ingredient_checker.ingredients),
                "common_fixes_count": len(ingredient_checker.common_fixes)
            }
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/debug-scans/<email>', methods=['GET'])
@login_required
def debug_scans(email):
    if current_user.role != 'admin':
        return jsonify({"status": "error", "message": "Требуются права администратора"}), 403
    
    try:
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({"status": "error", "message": f"Пользователь {email} не найден"}), 404
        
        scans = Scan.query.filter_by(user_id=user.id).order_by(Scan.created_at.desc()).all()
        
        scans_data = []
        for scan in scans:
            scan_dict = scan.to_dict()
            scan_dict['ingredients_detected_raw'] = scan.ingredients_detected
            scan_dict['ingredients_list_length'] = len(scan.get_ingredients_list())
            scans_data.append(scan_dict)
        
        return jsonify({
            "status": "success",
            "user": user.to_dict(),
            "scans_count": len(scans),
            "scans": scans_data
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/fix-all-scans', methods=['POST'])
@login_required
def fix_all_scans():
    if current_user.role != 'admin':
        return jsonify({"status": "error", "message": "Требуются права администратора"}), 403
    
    try:
        scans = Scan.query.all()
        fixed_count = 0
        
        print(f"\n🔧 Исправление всех сканов ({len(scans)} шт.)")
        
        for scan in scans:
            if scan.original_text:
                detected_ingredients = check_ingredients(scan.original_text)
                
                if detected_ingredients:
                    ingredients_for_json = []
                    for ing in detected_ingredients:
                        if isinstance(ing, dict):
                            ingredients_for_json.append({
                                'id': ing.get('id', 0),
                                'name': ing.get('name', 'Unknown'),
                                'risk_level': ing.get('risk_level', 'medium'),
                                'category': ing.get('category', ''),
                                'description': ing.get('description', '')
                            })
                    
                    scan.ingredients_detected = ingredients_for_json
                    
                    high_risk_count = sum(1 for ing in ingredients_for_json 
                                        if ing.get('risk_level') == 'high')
                    
                    if high_risk_count > 0:
                        scan.safety_status = 'danger'
                    elif len(ingredients_for_json) > 0:
                        scan.safety_status = 'warning'
                    else:
                        scan.safety_status = 'safe'
                    
                    fixed_count += 1
                    print(f"  ✅ Исправлен скан {scan.id}: {len(detected_ingredients)} ингредиентов")
                else:
                    scan.safety_status = 'safe'
                    scan.ingredients_detected = []
                    fixed_count += 1
                    print(f"  ℹ️  Исправлен скан {scan.id}: без ингредиентов")
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": f"Исправлено {fixed_count} сканирований",
            "fixed_count": fixed_count
        })
        
    except Exception as e:
        print(f"❌ Ошибка при исправлении сканов: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"status": "error", "message": "Електронна пошта та пароль обов'язкові"}), 400
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({"status": "error", "message": "Користувач з такою поштою вже існує"}), 400
        
        new_user = User(email=email)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            "status": "success", 
            "message": "Реєстрація успішна! Теперь ви можете увійти."
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
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            return jsonify({"status": "error", "message": "Невірна електронна пошта або пароль"}), 401
        
        user.last_login = datetime.utcnow()
        db.session.commit()
        
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def init_db():
    with app.app_context():
        print("🔄 Инициализация базы данных...")
        
        os.makedirs('uploads', exist_ok=True)
        os.makedirs('static', exist_ok=True)
        
        db.create_all()
        print("✅ Структура базы данных проверена")
        
        if User.query.count() == 0:
            admin = User(email="admin@cosmetics.com", role="admin")
            admin.set_password("admin123")
            db.session.add(admin)
            
            user = User(email="user@example.com", role="user")
            user.set_password("user123")
            db.session.add(user)
            
            db.session.commit()
            print("👤 Создан администратор: admin@cosmetics.com / admin123")
            print("👤 Создан пользователь: user@example.com / user123")
        
        users_count = User.query.count()
        scans_count = Scan.query.count()
        
        scans_with_ingredients = 0
        total_ingredients = 0
        
        scans = Scan.query.all()
        for scan in scans:
            ingredients = scan.get_ingredients_list()
            if ingredients:
                scans_with_ingredients += 1
                total_ingredients += len(ingredients)
        
        print(f"📊 Текущее состояние базы:")
        print(f"   👥 Пользователей: {users_count}")
        print(f"   🔍 Сканирований: {scans_count}")
        print(f"   📄 Сканов с ингредиентами: {scans_with_ingredients}")
        print(f"   🧪 Всего ингредиентов найдено: {total_ingredients}")
        
        if scans_count > 0:
            print(f"   📊 Среднее ингредиентов на скан: {round(total_ingredients / scans_count, 2)}")
        
        print("✅ Инициализация завершена")

if __name__ == '__main__':
    init_db()
    print("🚀 Запуск приложения...")
    print("🌐 Откройте: http://localhost:5000")
    app.run(debug=True, port=5000)