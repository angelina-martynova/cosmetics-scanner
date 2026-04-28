# app.py (v2 — підключення models.py)
"""
Головний файл Flask-додатку Cosmetics Scanner.

Покращення v2:
  1. Моделі імпортуються з models.py (розширений Ingredient, IngredientAlias, ScanIngredient)
  2. calculate_safety_status_with_message імпортується з models.py (єдина точка)
  3. create_scan() створює нормалізовані ScanIngredient-записи
  4. Новий ендпоінт /api/admin/verify — верифікація інгредієнтів адміном
  5. Новий ендпоінт /api/admin/aliases — CRUD для аліасів
  6. /api/ingredients тепер шукає і по аліасах
  7. /api/ingredients/<id> тепер повертає аліаси
  8. /api/test-checker повертає match_type та match_score
"""

from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for, make_response
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from datetime import datetime, timezone, timedelta
from ocr import extract_text
from checker import IngredientChecker, RAPIDFUZZ_AVAILABLE
from export import ScanExporter
from config import config
import os
import json
import traceback
import io
import zipfile

# ═══════════════════════════════════════════════════════════════════
# ІНІЦІАЛІЗАЦІЯ ДОДАТКУ
# ═══════════════════════════════════════════════════════════════════

frontend_folder = os.path.join(os.getcwd(), 'frontend')
static_css_folder = os.path.join(os.getcwd(), 'static')

app = Flask(__name__, template_folder=frontend_folder, static_folder=static_css_folder)
app.config.from_object(config.get('default'))

# Імпорт моделей з models.py та ініціалізація БД
from models import db, User, Ingredient, IngredientAlias, Scan, ScanIngredient, calculate_safety_status_with_message
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

scan_exporter = ScanExporter()

# Ініціалізація чекера
ingredient_checker = IngredientChecker(use_cache=True, fallback_to_local=True, auto_save_unknown=True)


# ═══════════════════════════════════════════════════════════════════
# ХЕЛПЕРИ
# ═══════════════════════════════════════════════════════════════════

def check_ingredients(text):
    """Аналіз тексту через IngredientChecker."""
    if not text:
        return []
    return ingredient_checker.find_ingredients(text)


def _normalize_detected_ingredients(detected_ingredients):
    """Приводить список знайдених інгредієнтів до JSON-сумісного формату."""
    normalized = []
    if not detected_ingredients:
        return normalized
    for ing in detected_ingredients:
        if isinstance(ing, dict):
            normalized.append({
                'id': ing.get('id', 0),
                'name': ing.get('name', 'Unknown'),
                'risk_level': ing.get('risk_level', 'unknown'),
                'category': ing.get('category', ''),
                'description': ing.get('description', ''),
                'description_en': ing.get('description_en', ''),
                'match_type': ing.get('match_type', ''),
                'match_score': ing.get('match_score'),
                'position': ing.get('position'),
                'source': ing.get('source', ''),
                'cas_number': ing.get('cas_number', ''),
                'ewg_score': ing.get('ewg_score'),
                'eu_max_concentration': ing.get('eu_max_concentration', ''),
                'is_banned_eu': ing.get('is_banned_eu', False),
            })
    return normalized


def create_scan(user_id, text, detected_ingredients, input_type='manual', input_method='text'):
    """
    Створює Scan + ScanIngredient записи.
    Зберігає JSON у ingredients_detected для зворотної сумісності
    та створює нормалізовані ScanIngredient записи.
    """
    safety_info = calculate_safety_status_with_message(detected_ingredients)
    ingredients_for_json = _normalize_detected_ingredients(detected_ingredients)

    scan = Scan(
        user_id=user_id,
        input_type=input_type,
        input_method=input_method,
        original_text=text,
        safety_status=safety_info['status'],
        safety_message=safety_info['message'],
        contains_unknown=safety_info['contains_unknown'],
        unknown_count=safety_info['unknown_count'],
        ingredients_detected=ingredients_for_json,
    )
    db.session.add(scan)
    db.session.flush()  # отримуємо scan.id

    # Створюємо нормалізовані зв'язки ScanIngredient
    for ing_data in detected_ingredients:
        if not isinstance(ing_data, dict):
            continue

        ingredient_id = ing_data.get('id')
        # Перевіряємо, що ingredient_id реально існує в БД
        if ingredient_id:
            exists = Ingredient.query.get(ingredient_id)
            if not exists:
                ingredient_id = None

        scan_ing = ScanIngredient(
            scan_id=scan.id,
            ingredient_id=ingredient_id if ingredient_id else None,
            raw_name=ing_data.get('name', ''),
            normalized_name=ing_data.get('name', ''),
            risk_level=ing_data.get('risk_level', 'unknown'),
            category=ing_data.get('category', ''),
            description=ing_data.get('description', ''),
            position=ing_data.get('position'),
            match_type=ing_data.get('match_type', ''),
            match_score=ing_data.get('match_score'),
            source=ing_data.get('source', ''),
        )
        db.session.add(scan_ing)

    db.session.commit()

    print(f"Створено сканування ID: {scan.id} | "
          f"{len(detected_ingredients)} інгредієнтів | "
          f"статус: {safety_info['status']}")

    return scan.id


# ═══════════════════════════════════════════════════════════════════
# СТОРІНКИ
# ═══════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('index.html')

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


# ═══════════════════════════════════════════════════════════════════
# AUTH API
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        if not email or not password:
            return jsonify({"status": "error", "message": "Електронна пошта та пароль обов'язкові"}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({"status": "error", "message": "Користувач з такою поштою вже існує"}), 400
        new_user = User(email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"status": "success", "message": "Реєстрація успішна! Тепер ви можете увійти."})
    except Exception as e:
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
        user.last_login = datetime.now(timezone.utc)
        db.session.commit()
        login_user(user)
        return jsonify({"status": "success", "message": "Вхід успішний!", "user": user.to_dict()})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"status": "success", "message": "Вихід успішний"})

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/api/status', methods=['GET'])
@login_required
def api_status():
    return jsonify({"status": "authenticated", "user": current_user.to_dict()})


# ═══════════════════════════════════════════════════════════════════
# АНАЛІЗ (OCR / текст / файл)
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        file = request.files.get('image')
        if not file:
            return jsonify({"status": "error", "message": "Файл зображення не знайдено"}), 400

        input_method = request.form.get('input_method', 'camera')
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)

        if file_size > 10 * 1024 * 1024:
            return jsonify({"status": "error", "message": "Зображення занадто велике (макс. 10MB)"}), 400
        if file_size == 0:
            return jsonify({"status": "error", "message": "Файл порожній"}), 400

        text = extract_text(file)
        if not text or text.strip() == "":
            return jsonify({
                "status": "warning",
                "message": "Не вдалося розпізнати текст. Спробуйте інше зображення.",
                "text": "", "ingredients": [], "ingredients_count": 0
            })

        detected_ingredients = check_ingredients(text)

        scan_id = None
        if current_user.is_authenticated:
            scan_id = create_scan(current_user.id, text, detected_ingredients, 'camera', input_method)

        return jsonify({
            "status": "success",
            "text": text[:5000],
            "ingredients": detected_ingredients,
            "ingredients_count": len(detected_ingredients),
            "scan_id": scan_id,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Помилка: {str(e)}"}), 500


@app.route('/api/analyze_text', methods=['POST'])
def analyze_text():
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"status": "error", "message": "Текст не надано"}), 400
        text = data['text']
        detected_ingredients = check_ingredients(text)

        scan_id = None
        if current_user.is_authenticated:
            scan_id = create_scan(current_user.id, text, detected_ingredients, 'manual', 'text')

        return jsonify({
            "status": "success",
            "text": text,
            "ingredients": detected_ingredients,
            "ingredients_count": len(detected_ingredients),
            "scan_id": scan_id,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/upload_text_file', methods=['POST'])
def upload_text_file():
    try:
        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "Файл не завантажено"}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({"status": "error", "message": "Файл не вибрано"}), 400

        file_ext = os.path.splitext(file.filename)[1].lower()
        allowed = {'.txt', '.doc', '.docx', '.pdf'}
        if file_ext not in allowed:
            return jsonify({"status": "error", "message": f"Непідтримуваний формат: {file_ext}"}), 400

        file.seek(0)
        file_bytes = file.read()
        if len(file_bytes) > 5 * 1024 * 1024:
            return jsonify({"status": "error", "message": "Файл занадто великий (макс. 5MB)"}), 400
        if len(file_bytes) == 0:
            return jsonify({"status": "error", "message": "Файл порожній"}), 400

        text = ""
        if file_ext == '.txt':
            for enc in ['utf-8', 'cp1251', 'cp1252', 'iso-8859-1', 'windows-1251']:
                try:
                    text = file_bytes.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if not text:
                text = file_bytes.decode('utf-8', errors='ignore')
        elif file_ext in {'.doc', '.docx', '.pdf'}:
            text = f"[Файл {file.filename} — бінарний формат {file_ext.upper()}. Скопіюйте текст вручну.]"
        else:
            text = file_bytes.decode('utf-8', errors='ignore')

        detected_ingredients = check_ingredients(text)

        scan_id = None
        if current_user.is_authenticated:
            scan_id = create_scan(current_user.id, text, detected_ingredients, 'manual', 'device')

        return jsonify({
            "status": "success",
            "text": text[:10000],
            "ingredients": detected_ingredients,
            "ingredients_count": len(detected_ingredients),
            "scan_id": scan_id,
            "file_info": {"name": file.filename, "size": len(file_bytes), "extension": file_ext},
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# ІНГРЕДІЄНТИ API (з пошуком по аліасах)
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/ingredients', methods=['GET'])
def get_ingredients():
    try:
        risk_level = request.args.get('risk_level')
        search = request.args.get('search')
        category = request.args.get('category')
        verified_only = request.args.get('verified', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 100))

        query = Ingredient.query

        if risk_level:
            query = query.filter_by(risk_level=risk_level)
        if category:
            query = query.filter_by(category=category)
        if verified_only:
            query = query.filter_by(verified=True)

        if search:
            # Шукаємо і по назві інгредієнта, і по аліасах
            alias_ids = (db.session.query(IngredientAlias.ingredient_id)
                         .filter(IngredientAlias.alias_lower.ilike(f'%{search.lower()}%'))
                         .subquery())
            query = query.filter(
                db.or_(
                    Ingredient.name.ilike(f'%{search}%'),
                    Ingredient.inci_name.ilike(f'%{search}%'),
                    Ingredient.cas_number.ilike(f'%{search}%'),
                    Ingredient.id.in_(alias_ids),
                )
            )

        ingredients = query.order_by(Ingredient.name).limit(limit).all()
        return jsonify({
            "status": "success",
            "count": len(ingredients),
            "ingredients": [ing.to_dict() for ing in ingredients],
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/ingredients/<int:ingredient_id>', methods=['GET'])
def get_ingredient_detail(ingredient_id):
    """Детальна інформація про інгредієнт з аліасами."""
    try:
        ing = Ingredient.query.get(ingredient_id)
        if not ing:
            return jsonify({"status": "error", "message": "Інгредієнт не знайдено"}), 404
        return jsonify({
            "status": "success",
            "ingredient": ing.to_dict(include_aliases=True),
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/ingredients/enhanced', methods=['GET'])
def get_enhanced_ingredients():
    try:
        search = request.args.get('search')
        limit = int(request.args.get('limit', 50))
        include_external = request.args.get('external', 'false').lower() == 'true'

        query = Ingredient.query
        if search:
            alias_ids = (db.session.query(IngredientAlias.ingredient_id)
                         .filter(IngredientAlias.alias_lower.ilike(f'%{search.lower()}%'))
                         .subquery())
            query = query.filter(
                db.or_(
                    Ingredient.name.ilike(f'%{search}%'),
                    Ingredient.inci_name.ilike(f'%{search}%'),
                    Ingredient.id.in_(alias_ids),
                )
            )

        ingredients = query.order_by(Ingredient.name).limit(limit).all()
        result = [ing.to_dict() for ing in ingredients]

        if include_external and search:
            result.append({
                "id": "external_search",
                "name": f"Пошук '{search}' у зовнішніх джерелах",
                "risk_level": "info", "category": "external",
                "description": "Натисніть для пошуку в CosIng, Open Beauty Facts та PubChem",
                "source": "external_search",
            })

        return jsonify({
            "status": "success", "count": len(result),
            "ingredients": result,
            "sources": {"local": len(ingredients), "external": 1 if include_external and search else 0},
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# СКАНИ API
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/scans', methods=['GET'])
@login_required
def get_user_scans():
    try:
        scans = (Scan.query.filter_by(user_id=current_user.id)
                 .order_by(Scan.created_at.desc()).all())
        return jsonify({
            "status": "success",
            "scans": [s.to_dict() for s in scans],
            "total": len(scans),
            "user": current_user.email,
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
        return jsonify({"status": "success", "scan": scan.to_dict()})
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
        return jsonify({"status": "success", "message": "Сканування видалено"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/scans/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_scans():
    try:
        data = request.get_json()
        scan_ids = data.get('scan_ids', [])
        if not scan_ids:
            return jsonify({"status": "error", "message": "Не вказано сканувань"}), 400
        scans = Scan.query.filter(Scan.id.in_(scan_ids), Scan.user_id == current_user.id).all()
        for s in scans:
            db.session.delete(s)
        db.session.commit()
        return jsonify({"status": "success", "message": f"Видалено {len(scans)} сканувань"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# ЕКСПОРТ PDF / ZIP
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/scans/<int:scan_id>/export/pdf', methods=['GET'])
@login_required
def export_scan_to_pdf(scan_id):
    lang = request.args.get('lang', 'uk')
    try:
        scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first()
        if not scan:
            return jsonify({"status": "error", "message": "Сканування не знайдено"}), 404
        scan_data = scan.to_dict()
        export_data = {
            'id': scan_data['id'], 'created_at': scan_data['created_at'],
            'input_type': scan_data['input_type'], 'input_method': scan_data['input_method'],
            'safety_status': scan_data['safety_status'], 'safety_message': scan_data['safety_message'],
            'contains_unknown': scan_data['contains_unknown'], 'unknown_count': scan_data['unknown_count'],
            'original_text': scan_data['original_text'], 'ingredients_count': scan_data['ingredients_count'],
            'ingredients_detailed': scan.get_ingredients_list(), 'risk_statistics': scan_data['risk_statistics'],
        }
        pdf_bytes = scan_exporter.create_pdf_bytes(export_data, current_user.email, lang=lang)
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = (
            f'attachment; filename=scan_{scan_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
        return response
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/scans/export-multiple/zip', methods=['GET'])
@login_required
def export_multiple_scans_zip():
    lang = request.args.get('lang', 'uk')
    scan_ids_str = request.args.get('ids', '')
    if not scan_ids_str:
        return jsonify({"status": "error", "message": "Не вказано ідентифікатори"}), 400
    try:
        scan_ids = [int(s.strip()) for s in scan_ids_str.split(',') if s.strip().isdigit()]
    except ValueError:
        return jsonify({"status": "error", "message": "Невірний формат ids"}), 400
    if not scan_ids:
        return jsonify({"status": "error", "message": "Список порожній"}), 400

    scans = Scan.query.filter(Scan.id.in_(scan_ids), Scan.user_id == current_user.id).all()
    if not scans:
        return jsonify({"status": "error", "message": "Сканування не знайдено"}), 404

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for scan in scans:
            try:
                scan_data = scan.to_dict()
                export_data = {
                    'id': scan_data['id'], 'created_at': scan_data['created_at'],
                    'input_type': scan_data['input_type'], 'input_method': scan_data['input_method'],
                    'safety_status': scan_data['safety_status'], 'safety_message': scan_data['safety_message'],
                    'contains_unknown': scan_data['contains_unknown'], 'unknown_count': scan_data['unknown_count'],
                    'original_text': scan_data['original_text'],
                    'ingredients_count': scan_data['ingredients_count'],
                    'ingredients_detailed': scan.get_ingredients_list(),
                    'risk_statistics': scan_data['risk_statistics'],
                }
                pdf_bytes = scan_exporter.create_pdf_bytes(export_data, current_user.email, lang=lang)
                zf.writestr(f"scan_{scan.id}.pdf", pdf_bytes)
            except Exception as e:
                print(f"Помилка експорту скану {scan.id}: {e}")
    zip_buffer.seek(0)
    response = make_response(zip_buffer.read())
    response.headers['Content-Type'] = 'application/zip'
    response.headers['Content-Disposition'] = (
        f'attachment; filename=scans_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
    )
    return response


# ═══════════════════════════════════════════════════════════════════
# ЗОВНІШНІ ДЖЕРЕЛА
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/external/search', methods=['POST'])
def external_search():
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        if not name:
            return jsonify({"status": "error", "message": "Не вказано назву"}), 400
        result = ingredient_checker.search_ingredient(name)
        return jsonify({"status": "success", "ingredient": result, "source": result.get('source', 'unknown')})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/external/sources', methods=['GET'])
def get_external_sources():
    sources = [
        {"name": "Open Beauty Facts", "url": "https://world.openbeautyfacts.org/", "status": "available"},
        {"name": "PubChem", "url": "https://pubchem.ncbi.nlm.nih.gov/", "status": "available"},
        {"name": "ChEBI (EBI)", "url": "https://www.ebi.ac.uk/chebi/", "status": "available"},
    ]
    return jsonify({"status": "success", "sources": sources})


# ═══════════════════════════════════════════════════════════════════
# АДМІН: ВЕРИФІКАЦІЯ ІНГРЕДІЄНТІВ (НОВИЙ)
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/admin/unverified', methods=['GET'])
@login_required
def get_unverified_ingredients():
    """Список неверифікованих інгредієнтів (auto-saved)."""
    if current_user.role != 'admin':
        return jsonify({"status": "error", "message": "Потрібні права адміністратора"}), 403
    try:
        unverified = Ingredient.query.filter_by(verified=False).order_by(Ingredient.created_at.desc()).all()
        return jsonify({
            "status": "success",
            "count": len(unverified),
            "ingredients": [ing.to_dict(include_aliases=True) for ing in unverified],
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/admin/verify/<int:ingredient_id>', methods=['POST'])
@login_required
def verify_ingredient(ingredient_id):
    """Верифікація інгредієнта адміністратором."""
    if current_user.role != 'admin':
        return jsonify({"status": "error", "message": "Потрібні права адміністратора"}), 403
    try:
        ing = Ingredient.query.get(ingredient_id)
        if not ing:
            return jsonify({"status": "error", "message": "Інгредієнт не знайдено"}), 404

        data = request.get_json() or {}
        # Адмін може оновити поля при верифікації
        if 'risk_level' in data:
            ing.risk_level = data['risk_level']
        if 'category' in data:
            ing.category = data['category']
        if 'description' in data:
            ing.description = data['description']
        if 'description_en' in data:
            ing.description_en = data['description_en']
        if 'cas_number' in data:
            ing.cas_number = data['cas_number']
        if 'ewg_score' in data:
            ing.ewg_score = data['ewg_score']
        if 'eu_max_concentration' in data:
            ing.eu_max_concentration = data['eu_max_concentration']
        if 'eu_regulation_annex' in data:
            ing.eu_regulation_annex = data['eu_regulation_annex']
        if 'is_banned_eu' in data:
            ing.is_banned_eu = data['is_banned_eu']

        ing.verified = True
        ing.verified_at = datetime.now(timezone.utc)
        ing.verified_by = current_user.email
        ing.source_of_risk_assessment = data.get('source_of_risk_assessment', 'manual')

        db.session.commit()
        return jsonify({"status": "success", "message": f"Інгредієнт '{ing.name}' верифіковано", "ingredient": ing.to_dict()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/admin/verify/<int:ingredient_id>', methods=['DELETE'])
@login_required
def reject_ingredient(ingredient_id):
    """Видалення неверифікованого інгредієнта."""
    if current_user.role != 'admin':
        return jsonify({"status": "error", "message": "Потрібні права адміністратора"}), 403
    try:
        ing = Ingredient.query.get(ingredient_id)
        if not ing:
            return jsonify({"status": "error", "message": "Інгредієнт не знайдено"}), 404
        name = ing.name
        db.session.delete(ing)
        db.session.commit()
        return jsonify({"status": "success", "message": f"Інгредієнт '{name}' видалено"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# АДМІН: АЛІАСИ (НОВИЙ)
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/admin/aliases', methods=['GET'])
@login_required
def get_aliases():
    """Список аліасів (з пагінацією та фільтрацією)."""
    if current_user.role != 'admin':
        return jsonify({"status": "error", "message": "Потрібні права адміністратора"}), 403
    try:
        ingredient_id = request.args.get('ingredient_id', type=int)
        alias_type = request.args.get('type')
        limit = request.args.get('limit', 100, type=int)

        query = IngredientAlias.query
        if ingredient_id:
            query = query.filter_by(ingredient_id=ingredient_id)
        if alias_type:
            query = query.filter_by(alias_type=alias_type)

        aliases = query.order_by(IngredientAlias.alias).limit(limit).all()
        return jsonify({
            "status": "success",
            "count": len(aliases),
            "aliases": [{
                'id': a.id, 'alias': a.alias, 'alias_type': a.alias_type,
                'language': a.language, 'ingredient_id': a.ingredient_id,
                'ingredient_name': a.ingredient.name if a.ingredient else None,
            } for a in aliases],
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/admin/aliases', methods=['POST'])
@login_required
def add_alias():
    """Додавання нового аліаса."""
    if current_user.role != 'admin':
        return jsonify({"status": "error", "message": "Потрібні права адміністратора"}), 403
    try:
        data = request.get_json()
        ingredient_id = data.get('ingredient_id')
        alias_text = data.get('alias', '').strip()
        alias_type = data.get('alias_type', 'common')
        language = data.get('language')

        if not ingredient_id or not alias_text:
            return jsonify({"status": "error", "message": "ingredient_id та alias обов'язкові"}), 400

        ing = Ingredient.query.get(ingredient_id)
        if not ing:
            return jsonify({"status": "error", "message": "Інгредієнт не знайдено"}), 404

        existing = IngredientAlias.query.filter_by(alias_lower=alias_text.lower()).first()
        if existing:
            return jsonify({"status": "error", "message": f"Аліас '{alias_text}' вже існує"}), 400

        new_alias = IngredientAlias(
            ingredient_id=ingredient_id, alias=alias_text,
            alias_lower=alias_text.lower(), alias_type=alias_type, language=language,
        )
        db.session.add(new_alias)
        db.session.commit()
        return jsonify({"status": "success", "message": f"Аліас '{alias_text}' додано", "alias": new_alias.to_dict()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/admin/aliases/<int:alias_id>', methods=['DELETE'])
@login_required
def delete_alias(alias_id):
    """Видалення аліаса."""
    if current_user.role != 'admin':
        return jsonify({"status": "error", "message": "Потрібні права адміністратора"}), 403
    try:
        alias = IngredientAlias.query.get(alias_id)
        if not alias:
            return jsonify({"status": "error", "message": "Аліас не знайдено"}), 404
        db.session.delete(alias)
        db.session.commit()
        return jsonify({"status": "success", "message": "Аліас видалено"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# ТЕСТИ / ДІАГНОСТИКА
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "healthy", "service": "Cosmetics Scanner API v2",
        "timestamp": datetime.utcnow().isoformat(),
    })

@app.route('/api/simple-check')
def simple_check():
    return jsonify({
        "service": "Cosmetics Scanner API v2", "status": "running",
        "endpoints": {
            "health": "/api/health", "register": "/api/register",
            "login": "/api/login", "analyze": "/api/analyze",
            "analyze_text": "/api/analyze_text", "ingredients": "/api/ingredients",
            "scans": "/api/scans", "admin_unverified": "/api/admin/unverified",
            "admin_aliases": "/api/admin/aliases",
        },
    })

@app.route('/api/test-checker', methods=['POST'])
def test_checker():
    try:
        data = request.get_json()
        text = data.get('text', '') if data else ''
        if not text:
            text = "Состав: Aqua, Sodium Laureth Sulfate, Parfum, Methylparaben, Formaldehyde"
        detected = check_ingredients(text)
        return jsonify({
            "status": "success", "text": text,
            "ingredients_found": len(detected), "ingredients": detected,
            "checker_info": {
                "total_ingredients": len(ingredient_checker.local_ingredients),
                "total_aliases": len(ingredient_checker._alias_index),
                "ocr_fixes": len(ingredient_checker.ocr_fixes),
                "rapidfuzz": RAPIDFUZZ_AVAILABLE,
            },
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/test-safety-logic', methods=['POST'])
def test_safety_logic():
    try:
        data = request.get_json()
        ingredients = data.get('ingredients', []) if data else []
        if not ingredients:
            ingredients = [
                {'name': 'Aqua', 'risk_level': 'safe'},
                {'name': 'Glycerin', 'risk_level': 'low'},
                {'name': 'Unknown1', 'risk_level': 'unknown'},
                {'name': 'Unknown2', 'risk_level': 'unknown'},
            ]
        safety_info = calculate_safety_status_with_message(ingredients)
        stats = {k: sum(1 for i in ingredients if i.get('risk_level') == k)
                 for k in ['high', 'medium', 'low', 'unknown', 'safe']}
        stats['total'] = len(ingredients)
        return jsonify({
            "status": "success", "safety_info": safety_info, "statistics": stats,
            "unknown_percentage": (stats['unknown'] / stats['total'] * 100) if stats['total'] > 0 else 0,
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/db-check')
def db_check():
    try:
        from sqlalchemy import text, func
        total_ingredients = Ingredient.query.count()
        total_aliases = IngredientAlias.query.count()
        total_scans = Scan.query.count()
        verified = Ingredient.query.filter_by(verified=True).count()
        unverified = Ingredient.query.filter_by(verified=False).count()

        return jsonify({
            "status": "connected",
            "statistics": {
                "users": User.query.count(),
                "ingredients": total_ingredients,
                "ingredients_verified": verified,
                "ingredients_unverified": unverified,
                "aliases": total_aliases,
                "scans": total_scans,
            },
            "timestamp": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Адмін-ендпоінти для діагностики (збережені з v1)
@app.route('/api/debug-scans/<email>', methods=['GET'])
@login_required
def debug_scans(email):
    if current_user.role != 'admin':
        return jsonify({"status": "error", "message": "Потрібні права адміністратора"}), 403
    try:
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({"status": "error", "message": f"Користувача {email} не знайдено"}), 404
        scans = Scan.query.filter_by(user_id=user.id).order_by(Scan.created_at.desc()).all()
        return jsonify({
            "status": "success", "user": user.to_dict(),
            "scans_count": len(scans),
            "scans": [s.to_dict() for s in scans],
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/fix-all-scans', methods=['POST'])
@login_required
def fix_all_scans():
    if current_user.role != 'admin':
        return jsonify({"status": "error", "message": "Потрібні права адміністратора"}), 403
    try:
        scans = Scan.query.all()
        fixed = 0
        for scan in scans:
            if scan.original_text:
                detected = check_ingredients(scan.original_text)
                scan.ingredients_detected = _normalize_detected_ingredients(detected)
                safety_info = calculate_safety_status_with_message(detected)
                scan.safety_status = safety_info['status']
                scan.safety_message = safety_info['message']
                scan.contains_unknown = safety_info['contains_unknown']
                scan.unknown_count = safety_info['unknown_count']
                fixed += 1
        db.session.commit()
        return jsonify({"status": "success", "message": f"Виправлено {fixed} сканувань"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Кеш зовнішніх джерел
@app.route('/api/external/cache/stats', methods=['GET'])
@login_required
def get_cache_stats():
    if current_user.role != 'admin':
        return jsonify({"status": "error", "message": "Потрібні права адміністратора"}), 403
    try:
        import sqlite3
        cache_file = 'data_cache/external_cache.db'
        if not os.path.exists(cache_file):
            return jsonify({"status": "success", "cache_exists": False})
        conn = sqlite3.connect(cache_file)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ingredients_cache")
        total = cur.fetchone()[0]
        cur.execute("SELECT source, COUNT(*) FROM ingredients_cache GROUP BY source")
        sources = dict(cur.fetchall())
        conn.close()
        return jsonify({"status": "success", "cache_exists": True, "total": total, "sources": sources})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/external/cache/clear', methods=['POST'])
@login_required
def clear_cache():
    if current_user.role != 'admin':
        return jsonify({"status": "error", "message": "Потрібні права адміністратора"}), 403
    try:
        import sqlite3
        cache_file = 'data_cache/external_cache.db'
        if os.path.exists(cache_file):
            conn = sqlite3.connect(cache_file)
            conn.execute("DELETE FROM ingredients_cache")
            conn.commit()
            conn.close()
        return jsonify({"status": "success", "message": "Кеш очищено"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# ІНІЦІАЛІЗАЦІЯ ТА ЗАПУСК
# ═══════════════════════════════════════════════════════════════════

def init_db():
    with app.app_context():
        print("Ініціалізація бази даних v2...")
        os.makedirs('uploads', exist_ok=True)
        os.makedirs('static', exist_ok=True)
        os.makedirs('data_cache', exist_ok=True)

        db.create_all()
        print("Структура БД перевірена (включно з ingredient_aliases, scan_ingredients)")

        if User.query.count() == 0:
            admin = User(email="admin@cosmetics.com", role="admin")
            admin.set_password("admin123")
            db.session.add(admin)
            user = User(email="user@example.com", role="user")
            user.set_password("user123")
            db.session.add(user)
            db.session.commit()
            print("Створено тестових користувачів")

        print(f"Стан БД: {User.query.count()} користувачів, "
              f"{Ingredient.query.count()} інгредієнтів, "
              f"{IngredientAlias.query.count()} аліасів, "
              f"{Scan.query.count()} сканувань")
        print("Ініціалізація завершена")


if __name__ == '__main__':
    init_db()
    print("Запуск Cosmetics Scanner v2...")
    print("http://localhost:5000")
    app.run(debug=True, port=5000, threaded=True)
