# models.py (timezone‑aware fix)
"""
Розширені моделі бази даних для Cosmetics Scanner.

Покращення:
  1. Модель Ingredient розширена: cas_number, inci_name, ewg_score,
     eu_max_concentration, eu_regulation_annex, is_banned_eu,
     source_of_risk_assessment, verified, description_en.
  2. Нова таблиця IngredientAlias — зберігає синоніми, OCR-виправлення,
     переклади (укр/рус/фр), INCI-альтернативні назви для кожного інгредієнта.
  3. Нова таблиця ScanIngredient — нормалізований зв'язок між Scan та Ingredient
     (замість зберігання JSON у полі ingredients_detected).
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


# ═══════════════════════════════════════════════════════════════════
# КОРИСТУВАЧ
# ═══════════════════════════════════════════════════════════════════
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)

    scans = db.relationship('Scan', backref='user', lazy=True,
                            cascade="all, delete-orphan")

    # --- helpers (пароль) залишаються без змін, імпортуються з werkzeug ---
    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
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


# ═══════════════════════════════════════════════════════════════════
# ІНГРЕДІЄНТ (розширена модель)
# ═══════════════════════════════════════════════════════════════════
class Ingredient(db.Model):
    __tablename__ = 'ingredients'

    id = db.Column(db.Integer, primary_key=True)

    # --- Основні поля (було) ---
    name = db.Column(db.String(200), unique=True, nullable=False, index=True)
    risk_level = db.Column(db.String(20), default='unknown')
    category = db.Column(db.String(50))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # --- НОВІ ПОЛЯ ---
    # Канонічна INCI-назва (може відрізнятися від name)
    inci_name = db.Column(db.String(200), index=True)

    # Опис англійською (для двомовності)
    description_en = db.Column(db.Text)

    # CAS Registry Number (наприклад '56-81-5' для гліцерину)
    cas_number = db.Column(db.String(30), index=True)

    # EWG Skin Deep Score (1-10, де 1 = безпечно, 10 = високий ризик)
    ewg_score = db.Column(db.Integer)

    # Регуляторні дані ЄС (Regulation EC 1223/2009)
    eu_max_concentration = db.Column(db.String(50))       # напр. "0.4%"
    eu_regulation_annex = db.Column(db.String(20))        # напр. "II", "III", "IV", "V", "VI"
    is_banned_eu = db.Column(db.Boolean, default=False)   # Annex II = заборонено

    # Звідки взято оцінку ризику
    source_of_risk_assessment = db.Column(db.String(100)) # "CosIng", "EWG", "SCCS", "manual", "heuristic"

    # Верифікація (для авто-збережених інгредієнтів)
    verified = db.Column(db.Boolean, default=False)
    verified_at = db.Column(db.DateTime)
    verified_by = db.Column(db.String(100))  # email адміна

    # Зв'язки
    aliases = db.relationship('IngredientAlias', backref='ingredient',
                              lazy='dynamic', cascade="all, delete-orphan")
    scan_links = db.relationship('ScanIngredient', backref='ingredient',
                                 lazy='dynamic', cascade="all, delete-orphan")

    def to_dict(self, include_aliases=False):
        result = {
            'id': self.id,
            'name': self.name,
            'inci_name': self.inci_name or self.name,
            'risk_level': self.risk_level,
            'category': self.category,
            'description': self.description,
            'description_en': self.description_en,
            'cas_number': self.cas_number,
            'ewg_score': self.ewg_score,
            'eu_max_concentration': self.eu_max_concentration,
            'eu_regulation_annex': self.eu_regulation_annex,
            'is_banned_eu': self.is_banned_eu,
            'source_of_risk_assessment': self.source_of_risk_assessment,
            'verified': self.verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_aliases:
            result['aliases'] = [a.to_dict() for a in self.aliases.all()]
        return result


# ═══════════════════════════════════════════════════════════════════
# СИНОНІМИ ІНГРЕДІЄНТІВ (НОВА ТАБЛИЦЯ)
# ═══════════════════════════════════════════════════════════════════
class IngredientAlias(db.Model):
    """
    Зберігає всі варіанти назв одного інгредієнта:
    - INCI-синоніми (Glycerol → Glycerin)
    - Переклади (гліцерин → Glycerin)
    - OCR-помилки (glycerln → Glycerin)
    - Скорочення (SLS → Sodium Lauryl Sulfate)
    - Торгові назви, E-коди (E422 → Glycerin)

    alias_type допомагає розрізняти тип синоніму:
      'inci'        — офіційний INCI-синонім
      'translation'  — переклад (uk, ru, fr, de тощо)
      'ocr_fix'      — відоме OCR-спотворення
      'abbreviation' — скорочення (SLS, BHA, PEG-...)
      'trade_name'   — торгова назва
      'e_code'       — E-код (харчова/косметична маркіровка)
      'common'       — побутова назва
    """
    __tablename__ = 'ingredient_aliases'

    id = db.Column(db.Integer, primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'),
                              nullable=False, index=True)

    alias = db.Column(db.String(200), nullable=False, index=True)
    alias_lower = db.Column(db.String(200), nullable=False, index=True)  # для пошуку

    alias_type = db.Column(db.String(30), default='common')
    # 'inci', 'translation', 'ocr_fix', 'abbreviation', 'trade_name', 'e_code', 'common'

    language = db.Column(db.String(5))  # 'uk', 'ru', 'en', 'fr', 'de' тощо (для перекладів)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Унікальність: один і той самий alias не може вказувати на різні інгредієнти
    __table_args__ = (
        db.UniqueConstraint('alias_lower', name='uq_alias_lower'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'alias': self.alias,
            'alias_type': self.alias_type,
            'language': self.language,
        }


# ═══════════════════════════════════════════════════════════════════
# СКАНУВАННЯ
# ═══════════════════════════════════════════════════════════════════
class Scan(db.Model):
    __tablename__ = 'scans'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    input_type = db.Column(db.String(50))
    input_method = db.Column(db.String(50))
    original_text = db.Column(db.Text)
    safety_status = db.Column(db.String(20), default='safe')
    safety_message = db.Column(db.String(255))
    contains_unknown = db.Column(db.Boolean, default=False)
    unknown_count = db.Column(db.Integer, default=0)
    image_filename = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # JSON-поле зберігається для зворотної сумісності
    ingredients_detected = db.Column(db.JSON)

    # Нормалізований зв'язок (нова таблиця)
    ingredient_links = db.relationship('ScanIngredient', backref='scan',
                                        lazy='dynamic', cascade="all, delete-orphan")

    def get_ingredients_list(self):
        """Повертає список інгредієнтів (зворотна сумісність з JSON-полем)."""
        # Спочатку пробуємо нормалізований зв'язок
        links = self.ingredient_links.all()
        if links:
            return [link.to_dict() for link in links]

        # Fallback: старе JSON-поле
        if not self.ingredients_detected:
            return []
        try:
            if isinstance(self.ingredients_detected, str):
                import json
                ingredients = json.loads(self.ingredients_detected)
            else:
                ingredients = self.ingredients_detected
            return ingredients if isinstance(ingredients, list) else []
        except (ValueError, TypeError):
            return []

    def get_risk_statistics(self):
        ingredients_list = self.get_ingredients_list()
        stats = {'total': len(ingredients_list),
                 'high': 0, 'medium': 0, 'low': 0, 'unknown': 0, 'safe': 0}
        for ing in ingredients_list:
            risk = ing.get('risk_level', 'unknown')
            if risk in stats:
                stats[risk] += 1
        return stats

    def to_dict(self):
        ingredients_list = self.get_ingredients_list()

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
            'risk_statistics': self.get_risk_statistics(),
        }


# ═══════════════════════════════════════════════════════════════════
# ЗВ'ЯЗОК СКАНУВАННЯ ↔ ІНГРЕДІЄНТ (НОВА ТАБЛИЦЯ)
# ═══════════════════════════════════════════════════════════════════
class ScanIngredient(db.Model):
    """
    Нормалізований зв'язок: один рядок = один інгредієнт у конкретному скані.
    Зберігає позицію інгредієнта у списку та джерело знаходження.
    """
    __tablename__ = 'scan_ingredients'

    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(db.Integer, db.ForeignKey('scans.id'),
                        nullable=False, index=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'),
                              nullable=True, index=True)

    # Назва як її розпізнано (до нормалізації)
    raw_name = db.Column(db.String(200))

    # Назва після нормалізації (якщо ingredient_id = None, тобто не знайдено в БД)
    normalized_name = db.Column(db.String(200))

    # Рівень ризику (кешується тут, щоб не робити JOIN при кожному відображенні)
    risk_level = db.Column(db.String(20), default='unknown')
    category = db.Column(db.String(50))
    description = db.Column(db.Text)

    # Позиція у списку складу (1 = перший, найвища концентрація)
    position = db.Column(db.Integer)

    # Як знайдено: 'exact', 'alias', 'fuzzy', 'external', 'heuristic', 'not_found'
    match_type = db.Column(db.String(30))

    # Оцінка збігу (для fuzzy: 0-100)
    match_score = db.Column(db.Float)

    # Джерело: 'database', 'openbeautyfacts', 'pubchem', 'chebi', 'ewg', 'heuristic'
    source = db.Column(db.String(50))

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'name': self.normalized_name or self.raw_name,
            'raw_name': self.raw_name,
            'risk_level': self.risk_level,
            'category': self.category,
            'description': self.description,
            'position': self.position,
            'match_type': self.match_type,
            'match_score': self.match_score,
            'source': self.source,
            'ingredient_id': self.ingredient_id,
        }


# ═══════════════════════════════════════════════════════════════════
# ФУНКЦІЯ ОЦІНКИ БЕЗПЕКИ (перенесена з app.py)
# ═══════════════════════════════════════════════════════════════════
def calculate_safety_status_with_message(detected_ingredients):
    """
    Обчислює зведений статус безпеки продукту та текстове повідомлення
    на основі списку знайдених інгредієнтів і їх рівнів ризику.
    """
    if not detected_ingredients:
        return {
            'status': 'safe',
            'message': 'Продукт безпечний',
            'contains_unknown': False,
            'unknown_count': 0
        }

    risk_counts = {'high': 0, 'medium': 0, 'low': 0, 'unknown': 0, 'safe': 0}

    for ing in detected_ingredients:
        risk_level = ing.get('risk_level', 'unknown')
        if risk_level in risk_counts:
            risk_counts[risk_level] += 1

    total = len(detected_ingredients)
    unknown_percentage = (risk_counts['unknown'] / total * 100) if total > 0 else 0

    # DANGER: є хоча б один інгредієнт високого ризику
    if risk_counts['high'] > 0:
        return {
            'status': 'danger',
            'message': 'Високий ризик, рекомендовано уникати',
            'contains_unknown': risk_counts['unknown'] > 0,
            'unknown_count': risk_counts['unknown']
        }

    # WARNING: кілька помірних або багато невідомих
    warning_conditions = [
        risk_counts['medium'] >= 2,
        risk_counts['medium'] == 1 and risk_counts['unknown'] >= 2,
        unknown_percentage > 50 and total <= 10,
        risk_counts['unknown'] >= 3 and total <= 5,
    ]
    if any(warning_conditions):
        return {
            'status': 'warning',
            'message': 'Помірні ризики, розгляньте альтернативи',
            'contains_unknown': risk_counts['unknown'] > 0,
            'unknown_count': risk_counts['unknown']
        }

    # LOW WARNING: один помірний або трохи невідомих
    low_warning_conditions = [
        risk_counts['medium'] == 1,
        risk_counts['unknown'] == 2 and total <= 8,
        unknown_percentage > 30 and unknown_percentage <= 50,
    ]
    if any(low_warning_conditions):
        return {
            'status': 'low_warning',
            'message': 'Незначні ризики, можна використовувати',
            'contains_unknown': risk_counts['unknown'] > 0,
            'unknown_count': risk_counts['unknown']
        }

    # SAFE
    return {
        'status': 'safe',
        'message': 'Продукт безпечний',
        'contains_unknown': risk_counts['unknown'] > 0,
        'unknown_count': risk_counts['unknown']
    }