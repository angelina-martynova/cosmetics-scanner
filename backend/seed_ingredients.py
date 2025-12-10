# seed_ingredients.py - исправленная версия для наполнения базы данных
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Ingredient, Scan
from datetime import datetime
import random
import json

def seed_ingredients():
    """Наполнение базы данных тестовыми данными"""
    
    with app.app_context():
        print("🌱 Наполнение базы данных тестовыми данными...")
        print("=" * 60)
        
        # 1. Очистка старых данных
        print("\n🗑️ Очистка старых данных...")
        Scan.query.delete()
        Ingredient.query.delete()
        db.session.commit()
        print("✅ Старые данные удалены")
        
        # 2. Добавление ингредиентов из checker.py
        print("\n🧪 Добавление ингредиентов из checker.py...")
        from checker import IngredientChecker
        checker = IngredientChecker()
        
        ingredients_added = 0
        for ingredient_data in checker.ingredients:
            # Проверяем, существует ли уже
            existing = Ingredient.query.filter_by(name=ingredient_data['name']).first()
            if not existing:
                # Преобразуем в формат для базы данных
                ingredient = Ingredient(
                    name=ingredient_data['name'],
                    risk_level=ingredient_data['risk_level'],
                    category=ingredient_data['category'],
                    description=ingredient_data['description']
                )
                db.session.add(ingredient)
                ingredients_added += 1
                print(f"  + {ingredient_data['name']} ({ingredient_data['risk_level']})")
        
        db.session.commit()
        print(f"✅ Добавлено ингредиентов: {ingredients_added}")
        
        # 3. Тестовый пользователь
        print("\n👤 Создание тестового пользователя...")
        test_user = User.query.filter_by(email="user@example.com").first()
        if not test_user:
            test_user = User(email="user@example.com", role="user")
            test_user.set_password("user123")
            db.session.add(test_user)
            db.session.commit()
            print("✅ Создан тестовый пользователь: user@example.com / user123")
        else:
            print("ℹ️ Пользователь уже существует")
        
        # 4. Администратор
        admin_user = User.query.filter_by(email="admin@cosmetics.com").first()
        if not admin_user:
            admin_user = User(email="admin@cosmetics.com", role="admin")
            admin_user.set_password("admin123")
            db.session.add(admin_user)
            print("✅ Создан администратор: admin@cosmetics.com / admin123")
        
        db.session.commit()
        
        # 5. Тестовые сканирования
        print("\n🔍 Создание тестовых сканирований...")
        
        test_scans = [
            {
                "text": "Состав: Aqua, Sodium Laureth Sulfate, Cocamidopropyl Betaine, Parfum, Methylparaben, Citric Acid, Glycerin",
                "title": "Шампунь с сульфатами",
                "expected": ["Sodium Laureth Sulfate", "Parfum", "Methylparaben"]
            },
            {
                "text": "Ingredients: Water, Formaldehyde, Glycerin, Alcohol Denat, Fragrance, Mineral Oil",
                "title": "Лосьон с формальдегидом",
                "expected": ["Formaldehyde", "Parfum", "Alcohol Denat", "Mineral Oil"]
            },
            {
                "text": "INCI: Methylisothiazolinone, Tetrasodium EDTA, PEG-4, Sodium Lauryl Sulfate, Silicone",
                "title": "Гель для душа с консервантами",
                "expected": ["Methylisothiazolinone", "Tetrasodium EDTA", "PEG-4", "Sodium Laureth Sulfate", "Silicone"]
            },
            {
                "text": "Состав: Вода, Натрію лаурет сульфат, Формальдегід, Ароматизатор, Консервант, Гліцерин",
                "title": "Украинский состав",
                "expected": ["Sodium Laureth Sulfate", "Formaldehyde", "Parfum", "Methylparaben"]
            },
            {
                "text": "Ingredients: Aqua, Oxybenzone, Propylene Glycol, Triclosan, Parfum",
                "title": "Солнцезащитный крем",
                "expected": ["Oxybenzone", "Propylene Glycol", "Triclosan", "Parfum"]
            },
            {
                "text": "Состав: Вода, Алое Вера, Гіалуронова кислота, Вітамін Е, Ромашка",
                "title": "Натуральный крем",
                "expected": []  # Безопасный состав
            }
        ]
        
        scans_created = 0
        for i, test_data in enumerate(test_scans):
            # Находим ингредиенты в тексте
            detected = checker.find_ingredients(test_data["text"])
            
            # Преобразуем в JSON формат
            ingredients_for_json = []
            for ing in detected:
                if isinstance(ing, dict):
                    ingredients_for_json.append({
                        'id': ing.get('id', 0),
                        'name': ing.get('name', ''),
                        'risk_level': ing.get('risk_level', 'medium'),
                        'category': ing.get('category', ''),
                        'description': ing.get('description', ''),
                        'aliases': ing.get('aliases', [])
                    })
            
            # Определяем статус безопасности
            safety_status = 'safe'
            if ingredients_for_json:
                high_risk_count = sum(1 for ing in ingredients_for_json 
                                    if ing.get('risk_level') == 'high')
                if high_risk_count > 0:
                    safety_status = 'danger'
                else:
                    safety_status = 'warning'
            
            # Создаем скан
            scan = Scan(
                user_id=test_user.id,
                input_type=random.choice(['manual', 'camera']),
                input_method=random.choice(['text', 'device']),
                original_text=test_data["text"],
                safety_status=safety_status,
                ingredients_detected=ingredients_for_json,
                created_at=datetime.utcnow()
            )
            db.session.add(scan)
            scans_created += 1
            
            print(f"  📄 Создан скан #{i+1}: {test_data['title']}")
            print(f"    Найдено: {len(detected)} ингредиентов")
            print(f"    Статус: {safety_status}")
        
        db.session.commit()
        print(f"\n✅ Создано тестовых сканирований: {scans_created}")
        
        # 6. Статистика
        print("\n📊 ФИНАЛЬНАЯ СТАТИСТИКА БАЗЫ:")
        print(f"   👥 Пользователей: {User.query.count()}")
        print(f"   🧪 Ингредиентов: {Ingredient.query.count()}")
        print(f"   🔍 Сканирований: {Scan.query.count()}")
        
        # Подсчет ингредиентов в сканах
        total_ingredients = 0
        scans = Scan.query.all()
        for scan in scans:
            ingredients = scan.get_ingredients_list()
            total_ingredients += len(ingredients) if ingredients else 0
        
        print(f"   📝 Всего ингредиентов в сканах: {total_ingredients}")
        
        # Распределение по статусам
        safe_scans = Scan.query.filter_by(safety_status='safe').count()
        warning_scans = Scan.query.filter_by(safety_status='warning').count()
        danger_scans = Scan.query.filter_by(safety_status='danger').count()
        
        print(f"   🟢 Безопасные сканы: {safe_scans}")
        print(f"   🟡 Предупреждения: {warning_scans}")
        print(f"   🔴 Опасные: {danger_scans}")
        
        print("\n" + "=" * 60)
        print("🎉 БАЗА ДАННЫХ ГОТОВА К РАБОТЕ!")
        print("=" * 60)
        
        print("\n🔧 ДЛЯ ТЕСТИРОВАНИЯ:")
        print("   1. Запустите: python app.py")
        print("   2. Откройте: http://localhost:5000")
        print("   3. Войдите как: user@example.com / user123")
        print("   4. Проверьте историю сканирований в разделе 'Scans'")
        
        print("\n📱 ТЕСТОВЫЕ ДАННЫЕ:")
        print("   Логин: user@example.com")
        print("   Пароль: user123")
        print("\n   Логин (админ): admin@cosmetics.com")
        print("   Пароль: admin123")
        
        print("\n⚠️  Для очистки базы данных:")
        print("   python -c \"from app import app, db; with app.app_context(): db.drop_all(); db.create_all()\"")
        
        return True

if __name__ == "__main__":
    seed_ingredients()