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
import requests
from functools import lru_cache
import time
import traceback

frontend_folder = os.path.join(os.getcwd(), 'frontend')
static_css_folder = os.path.join(os.getcwd(), 'static')

app = Flask(__name__, template_folder=frontend_folder, static_folder=static_css_folder)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:AdminPostgres123!@localhost:5432/cosmetics_db'
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB максимум

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
    safety_message = db.Column(db.String(255))  # Новое поле: сообщение о безопасности
    contains_unknown = db.Column(db.Boolean, default=False)  # Новое поле: содержит неизвестные ингредиенты
    unknown_count = db.Column(db.Integer, default=0)  # Новое поле: количество неизвестных ингредиентов
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
        
        # Если поля не заполнены, рассчитываем заново (для старых записей)
        if not self.safety_message:
            safety_info = calculate_safety_status_with_message(ingredients_list)
            self.safety_status = safety_info['status']
            self.safety_message = safety_info['message']
            self.contains_unknown = safety_info['contains_unknown']
            self.unknown_count = safety_info['unknown_count']
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'input_type': self.input_type,
            'input_method': self.input_method,
            'original_text': self.original_text,
            'safety_status': self.safety_status,
            'safety_message': self.safety_message,
            'contains_unknown': self.contains_unknown,
            'unknown_count': self.unknown_count,
            'image_filename': self.image_filename,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'ingredients': ingredients_list,
            'ingredients_count': len(ingredients_list),
            'risk_statistics': self.get_risk_statistics()
        }
    
    def get_risk_statistics(self):
        """Получение статистики по рискам"""
        ingredients_list = self.get_ingredients_list()
        
        stats = {
            'total': len(ingredients_list),
            'high': 0,
            'medium': 0,
            'low': 0,
            'unknown': 0,
            'safe': 0
        }
        
        for ing in ingredients_list:
            risk_level = ing.get('risk_level', 'unknown')
            if risk_level in stats:
                stats[risk_level] += 1
        
        return stats

def calculate_safety_status_with_message(detected_ingredients):
    """Улучшенная функция расчета статуса безопасности с сообщением"""
    
    if not detected_ingredients:
        return {
            'status': 'safe',
            'message': 'Продукт безопасен',
            'contains_unknown': False,
            'unknown_count': 0
        }
    
    # Счетчики рисков
    risk_counts = {
        'high': 0,
        'medium': 0,
        'low': 0,
        'unknown': 0,
        'safe': 0
    }
    
    # Собираем статистику
    for ing in detected_ingredients:
        risk_level = ing.get('risk_level', 'unknown')
        if risk_level in risk_counts:
            risk_counts[risk_level] += 1
    
    total = len(detected_ingredients)
    unknown_percentage = (risk_counts['unknown'] / total * 100) if total > 0 else 0
    
    # Основная логика оценки
    
    # 1. Опасность - есть high-риск ингредиенты
    if risk_counts['high'] > 0:
        return {
            'status': 'danger',
            'message': 'Высокий риск, рекомендуется избегать',
            'contains_unknown': risk_counts['unknown'] > 0,
            'unknown_count': risk_counts['unknown']
        }
    
    # 2. Предупреждение - комбинация факторов
    warning_conditions = [
        risk_counts['medium'] >= 2,  # 2+ средних риска
        risk_counts['medium'] == 1 and risk_counts['unknown'] >= 2,  # 1 средний + 2+ неизвестных
        unknown_percentage > 50 and total <= 10,  # Больше половины неизвестно в небольшом составе
        risk_counts['unknown'] >= 3 and total <= 5,  # 3+ неизвестных в коротком составе
    ]
    
    if any(warning_conditions):
        return {
            'status': 'warning',
            'message': 'Умеренные риски, рассмотрите альтернативы',
            'contains_unknown': risk_counts['unknown'] > 0,
            'unknown_count': risk_counts['unknown']
        }
    
    # 3. Низкое предупреждение - умеренные условия
    low_warning_conditions = [
        risk_counts['medium'] == 1,  # 1 средний риск
        risk_counts['unknown'] == 2 and total <= 8,  # 2 неизвестных в небольшом составе
        unknown_percentage > 30 and unknown_percentage <= 50,  # 30-50% неизвестно
    ]
    
    if any(low_warning_conditions):
        return {
            'status': 'low_warning',
            'message': 'Незначительные риски, можно использовать',
            'contains_unknown': risk_counts['unknown'] > 0,
            'unknown_count': risk_counts['unknown']
        }
    
    # 4. Безопасно - только низкие риски или немного неизвестного
    safe_conditions = [
        risk_counts['low'] > 0 and risk_counts['unknown'] == 0,  # Только низкие риски
        risk_counts['unknown'] == 1 and total >= 10,  # 1 неизвестный среди многих ингредиентов
        unknown_percentage <= 20,  # Меньше 20% неизвестно
    ]
    
    if any(safe_conditions) or total == 0:
        return {
            'status': 'safe',
            'message': 'Продукт безопасен',
            'contains_unknown': risk_counts['unknown'] > 0,
            'unknown_count': risk_counts['unknown']
        }
    
    # 5. По умолчанию - безопасно с предупреждением о неизвестном
    return {
        'status': 'safe',
        'message': 'Продукт безопасен' + (' (содержит неизвестные ингредиенты)' if risk_counts['unknown'] > 0 else ''),
        'contains_unknown': risk_counts['unknown'] > 0,
        'unknown_count': risk_counts['unknown']
    }

ingredient_checker = IngredientChecker(use_cache=True, fallback_to_local=True)

def check_ingredients(text):
    if not text:
        return []
    return ingredient_checker.find_ingredients(text)

def create_scan(user_id, text, detected_ingredients, input_type='manual', input_method='text'):
    """Создание скана с улучшенной логикой оценки безопасности"""
    
    # Рассчитываем статус безопасности
    safety_info = calculate_safety_status_with_message(detected_ingredients)
    
    # Подготавливаем данные ингредиентов для JSON
    ingredients_for_json = []
    if detected_ingredients:
        for ing in detected_ingredients:
            if isinstance(ing, dict):
                ingredients_for_json.append({
                    'id': ing.get('id', 0),
                    'name': ing.get('name', 'Unknown'),
                    'risk_level': ing.get('risk_level', 'unknown'),
                    'category': ing.get('category', ''),
                    'description': ing.get('description', '')
                })
    
    # Создаем запись скана
    image_filename = None
    
    scan = Scan(
        user_id=user_id,
        input_type=input_type,
        input_method=input_method,
        original_text=text,
        safety_status=safety_info['status'],
        safety_message=safety_info['message'],
        contains_unknown=safety_info['contains_unknown'],
        unknown_count=safety_info['unknown_count'],
        image_filename=image_filename,
        ingredients_detected=ingredients_for_json
    )
    
    db.session.add(scan)
    db.session.commit()
    
    print(f"✅ Создан скан ID: {scan.id}")
    print(f"   Статус: {safety_info['status']}")
    print(f"   Сообщение: {safety_info['message']}")
    print(f"   Ингредиентов: {len(detected_ingredients)}")
    print(f"   Неизвестных: {safety_info['unknown_count']}")
    
    return scan.id

@app.route('/api/upload_text_file', methods=['POST'])
def upload_text_file():
    """Загрузка и обработка текстового файла"""
    try:
        print(f"\n📁 API upload_text_file вызван")
        
        if 'file' not in request.files:
            print("❌ Файл не найден в запросе")
            return jsonify({"status": "error", "message": "Файл не загружен"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            print("❌ Пустое имя файла")
            return jsonify({"status": "error", "message": "Файл не выбран"}), 400
        
        print(f"📄 Получен файл: {file.filename}")
        print(f"📊 Content-Type: {file.content_type}")
        
        # Сохраняем оригинальное имя для расширения
        original_filename = file.filename
        file_ext = os.path.splitext(original_filename)[1].lower() if '.' in original_filename else ''
        
        # Проверка расширения
        allowed_extensions = {'.txt', '.doc', '.docx', '.pdf'}
        if file_ext not in allowed_extensions:
            print(f"❌ Неподдерживаемое расширение: {file_ext}")
            return jsonify({"status": "error", "message": f"Неподдерживаемый формат файла: {file_ext}. Поддерживаются: {', '.join(allowed_extensions)}"}), 400
        
        # ВАЖНО: Читаем файл ОДИН РАЗ в память
        file.seek(0)
        file_bytes = file.read()
        file_size = len(file_bytes)
        
        print(f"📏 Размер файла: {file_size} байт")
        
        # Проверка размера (макс 5MB)
        if file_size > 5 * 1024 * 1024:
            print(f"❌ Файл слишком большой: {file_size} байт")
            return jsonify({"status": "error", "message": "Файл слишком большой. Максимальный размер: 5MB"}), 400
        
        if file_size == 0:
            print("❌ Файл пустой")
            return jsonify({"status": "error", "message": "Файл пустой"}), 400
        
        # Декодируем содержимое файла
        text = ""
        
        if file_ext == '.txt':
            # Пробуем разные кодировки для .txt файлов
            encodings = ['utf-8', 'cp1251', 'cp1252', 'iso-8859-1', 'windows-1251']
            for encoding in encodings:
                try:
                    text = file_bytes.decode(encoding)
                    print(f"✅ Успешно декодирован как {encoding}")
                    break
                except UnicodeDecodeError:
                    continue
            
            if not text:
                # Если все кодировки не подошли, используем игнорирование ошибок
                text = file_bytes.decode('utf-8', errors='ignore')
                print("⚠️ Файл декодирован с игнорированием ошибок")
        
        elif file_ext in {'.doc', '.docx', '.pdf'}:
            # Для бинарных форматов возвращаем сообщение
            text = f"[Файл {original_filename} - это бинарный формат {file_ext.upper()}. Для анализа скопируйте текст вручную или конвертируйте в TXT.]"
            print(f"ℹ️ Получен бинарный файл: {file_ext}")
        else:
            # Для остальных пробуем декодировать
            try:
                text = file_bytes.decode('utf-8')
            except UnicodeDecodeError:
                text = file_bytes.decode('utf-8', errors='ignore')
        
        print(f"📝 Извлечено текста: {len(text)} символов")
        if text and len(text) > 100:
            print(f"📄 Начало текста: {text[:100]}...")
        
        # Проверяем ингредиенты
        detected_ingredients = check_ingredients(text)
        
        print(f"🔍 Найдено ингредиентов: {len(detected_ingredients)}")
        
        # Создаем запись в базе данных
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
            "text": text[:10000],  # Ограничиваем для ответа
            "ingredients": detected_ingredients,
            "ingredients_count": len(detected_ingredients),
            "scan_id": scan_id,
            "file_info": {
                "name": original_filename,
                "size": file_size,
                "extension": file_ext
            }
        })
        
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА в upload_text_file:")
        traceback.print_exc()
        return jsonify({
            "status": "error", 
            "message": f"Внутренняя ошибка сервера: {str(e)}"
        }), 500

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
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500
  
@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        file = request.files.get('image')
        if not file:
            print("❌ Изображение не предоставлено")
            return jsonify({"status": "error", "message": "Файл изображения не найден"}), 400

        input_method = request.form.get('input_method', 'camera')
        
        print(f"\n📸 Начало обработки изображения (метод: {input_method})")
        print(f"📄 Имя файла: {file.filename}")
        
        # Проверка размера файла
        file.seek(0, 2)  # Перейти в конец
        file_size = file.tell()  # Получить размер
        file.seek(0)  # Вернуться в начало
        
        print(f"📏 Размер изображения: {file_size} байт")
        
        # Ограничение размера (макс 10MB)
        MAX_IMAGE_SIZE = 10 * 1024 * 1024
        if file_size > MAX_IMAGE_SIZE:
            print(f"❌ Изображение слишком большое: {file_size} байт")
            return jsonify({
                "status": "error", 
                "message": f"Изображение слишком большое. Максимальный размер: {MAX_IMAGE_SIZE//1024//1024}MB"
            }), 400
        
        if file_size == 0:
            print("❌ Изображение пустое")
            return jsonify({"status": "error", "message": "Файл изображения пустой"}), 400
        
        # Извлекаем текст с помощью OCR
        text = extract_text(file)
        
        if not text or text.strip() == "":
            print("⚠️ OCR не распознал текст")
            return jsonify({
                "status": "warning",
                "message": "Не удалось распознать текст на изображении. Попробуйте другое изображение или убедитесь, что текст четкий.",
                "text": "",
                "ingredients": [],
                "ingredients_count": 0
            })
        
        print(f"✅ OCR распознал {len(text)} символов")
        print(f"📝 Текст из OCR: {text[:150]}...")
        
        # Проверяем ингредиенты
        detected_ingredients = check_ingredients(text)
        
        print(f"🔍 Найдено ингредиентов: {len(detected_ingredients)}")
        
        # Создаем запись в базе данных
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
            "text": text[:5000],  # Ограничиваем длину ответа
            "ingredients": detected_ingredients,
            "ingredients_count": len(detected_ingredients),
            "scan_id": scan_id
        })
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА в analyze:")
        traceback.print_exc()
        return jsonify({
            "status": "error", 
            "message": f"Ошибка обработки изображения: {str(e)}"
        }), 500

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
            'safety_message': scan_data['safety_message'],
            'contains_unknown': scan_data['contains_unknown'],
            'unknown_count': scan_data['unknown_count'],
            'original_text': scan_data['original_text'],
            'ingredients_count': scan_data['ingredients_count'],
            'ingredients_detailed': ingredients_list,
            'risk_statistics': scan_data['risk_statistics']
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
                "total_ingredients_in_checker": len(ingredient_checker.local_ingredients),
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
                                'risk_level': ing.get('risk_level', 'unknown'),
                                'category': ing.get('category', ''),
                                'description': ing.get('description', '')
                            })
                    
                    scan.ingredients_detected = ingredients_for_json
                    
                    # Обновляем информацию о безопасности
                    safety_info = calculate_safety_status_with_message(detected_ingredients)
                    scan.safety_status = safety_info['status']
                    scan.safety_message = safety_info['message']
                    scan.contains_unknown = safety_info['contains_unknown']
                    scan.unknown_count = safety_info['unknown_count']
                    
                    fixed_count += 1
                    print(f"  ✅ Исправлен скан {scan.id}: {len(detected_ingredients)} ингредиентов, статус: {safety_info['status']}")
                else:
                    safety_info = calculate_safety_status_with_message([])
                    scan.safety_status = safety_info['status']
                    scan.safety_message = safety_info['message']
                    scan.contains_unknown = False
                    scan.unknown_count = 0
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

@app.route('/api/external/search', methods=['POST'])
def external_search():
    """Поиск ингредиента во внешних источниках"""
    try:
        data = request.get_json()
        ingredient_name = data.get('name', '').strip()
        
        if not ingredient_name:
            return jsonify({"status": "error", "message": "Не указано название ингредиента"}), 400
        
        # Используем обновленный checker
        ingredient_data = ingredient_checker.search_ingredient(ingredient_name)
        
        return jsonify({
            "status": "success",
            "ingredient": ingredient_data,
            "source": ingredient_data.get('source', 'unknown')
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/external/sources', methods=['GET'])
def get_external_sources():
    """Получение списка доступных внешних источников"""
    sources = [
        {
            "name": "CosIng (EC)",
            "description": "База данных косметических ингредиентов Европейской комиссии",
            "url": "https://ec.europa.eu/growth/tools-databases/cosing/",
            "status": "available",
            "rate_limit": "Требуется регистрация"
        },
        {
            "name": "Open Food Facts",
            "description": "Открытая база данных пищевых продуктов и ингредиентов",
            "url": "https://world.openfoodfacts.org/",
            "status": "available",
            "rate_limit": "30 запросов/минута"
        },
        {
            "name": "PubChem",
            "description": "База химических соединений NIH",
            "url": "https://pubchem.ncbi.nlm.nih.gov/",
            "status": "available",
            "rate_limit": "5 запросов/секунда"
        }
    ]
    
    return jsonify({
        "status": "success",
        "sources": sources,
        "cache_info": {
            "cache_dir": "data_cache",
            "cache_enabled": True
        }
    })


@app.route('/api/external/cache/stats', methods=['GET'])
@login_required
def get_cache_stats():
    """Статистика кэша внешних источников"""
    try:
        if current_user.role != 'admin':
            return jsonify({"status": "error", "message": "Требуются права администратора"}), 403
        
        import sqlite3
        import os
        
        cache_file = 'data_cache/external_cache.db'
        
        if not os.path.exists(cache_file):
            return jsonify({
                "status": "success",
                "cache_exists": False,
                "message": "Кэш не инициализирован"
            })
        
        conn = sqlite3.connect(cache_file)
        cursor = conn.cursor()
        
        # Получаем статистику
        cursor.execute("SELECT COUNT(*) FROM ingredients_cache")
        total_items = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ingredients_cache WHERE last_updated > datetime('now', '-1 day')")
        recent_items = cursor.fetchone()[0]
        
        cursor.execute("SELECT source, COUNT(*) FROM ingredients_cache GROUP BY source")
        sources_stats = cursor.fetchall()
        
        cursor.execute("SELECT name, last_updated FROM ingredients_cache ORDER BY last_updated DESC LIMIT 5")
        recent_entries = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            "status": "success",
            "cache_exists": True,
            "statistics": {
                "total_items": total_items,
                "recent_items": recent_items,
                "sources": dict(sources_stats),
                "recent_entries": [
                    {"name": name, "last_updated": last_updated}
                    for name, last_updated in recent_entries
                ]
            }
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/external/cache/clear', methods=['POST'])
@login_required
def clear_cache():
    """Очистка кэша внешних источников"""
    try:
        if current_user.role != 'admin':
            return jsonify({"status": "error", "message": "Требуются права администратора"}), 403
        
        import sqlite3
        import os
        
        cache_file = 'data_cache/external_cache.db'
        
        if os.path.exists(cache_file):
            conn = sqlite3.connect(cache_file)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ingredients_cache")
            conn.commit()
            conn.close()
            
            return jsonify({
                "status": "success",
                "message": "Кэш очищен"
            })
        else:
            return jsonify({
                "status": "success",
                "message": "Кэш не существует"
            })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/ingredients/enhanced', methods=['GET'])
def get_enhanced_ingredients():
    """Получение ингредиентов с возможностью расширения из внешних источников"""
    try:
        search = request.args.get('search')
        limit = int(request.args.get('limit', 50))
        include_external = request.args.get('external', 'false').lower() == 'true'
        
        # Начинаем с локальной базы
        query = Ingredient.query
        
        if search:
            query = query.filter(Ingredient.name.ilike(f'%{search}%'))
        
        local_ingredients = query.order_by(Ingredient.name).limit(limit).all()
        result = [ing.to_dict() for ing in local_ingredients]
        
        # Если нужно и во внешних источниках
        if include_external and search:
            # Здесь можно добавить поиск во внешних источниках
            # Для демо просто добавляем сообщение
            result.append({
                "id": "external_search",
                "name": f"Поиск '{search}' во внешних источниках",
                "risk_level": "info",
                "category": "external",
                "description": "Нажмите для поиска в CosIng, Open Food Facts и PubChem",
                "source": "external_search"
            })
        
        return jsonify({
            "status": "success",
            "count": len(result),
            "ingredients": result,
            "sources": {
                "local": len(local_ingredients),
                "external": 1 if include_external and search else 0
            }
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/test-safety-logic', methods=['POST'])
def test_safety_logic():
    """Тестирование новой логики оценки безопасности"""
    try:
        data = request.get_json()
        ingredients = data.get('ingredients', [])
        
        if not ingredients:
            # Тестовые данные
            ingredients = [
                {'name': 'Aqua', 'risk_level': 'safe'},
                {'name': 'Glycerin', 'risk_level': 'low'},
                {'name': 'Unknown1', 'risk_level': 'unknown'},
                {'name': 'Unknown2', 'risk_level': 'unknown'},
            ]
        
        # Применяем новую логику
        safety_info = calculate_safety_status_with_message(ingredients)
        
        # Анализируем статистику
        stats = {
            'total': len(ingredients),
            'high': sum(1 for i in ingredients if i.get('risk_level') == 'high'),
            'medium': sum(1 for i in ingredients if i.get('risk_level') == 'medium'),
            'low': sum(1 for i in ingredients if i.get('risk_level') == 'low'),
            'unknown': sum(1 for i in ingredients if i.get('risk_level') == 'unknown'),
            'safe': sum(1 for i in ingredients if i.get('risk_level') == 'safe'),
        }
        
        return jsonify({
            "status": "success",
            "safety_info": safety_info,
            "statistics": stats,
            "unknown_percentage": (stats['unknown'] / stats['total'] * 100) if stats['total'] > 0 else 0,
            "logic_explanation": {
                "safe": "Продукт безопасен",
                "low_warning": "Незначительные риски, можно использовать",
                "warning": "Умеренные риски, рассмотрите альтернативы",
                "danger": "Высокий риск, рекомендуется избегать"
            }
        })
        
    except Exception as e:
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
        print(f"❌ Ошибка регистрации: {str(e)}")
        traceback.print_exc()
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
        print(f"❌ Ошибка входа: {str(e)}")
        traceback.print_exc()
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
        os.makedirs('data_cache', exist_ok=True)
        
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
    print("💾 Кэш внешних источников включен")
    print("🔧 Режим отладки включен")
    print("🛡️ Новая система оценки безопасности активирована")
    
    app.run(debug=True, port=5000, threaded=True)