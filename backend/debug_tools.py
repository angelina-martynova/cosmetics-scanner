# debug_tools.py - інструменти для налагодження
from app import app, db, User, Scan
import json

def print_all_scans():
    """Вивести всі сканування в базі"""
    with app.app_context():
        print("\n=== ВСІ СКАНУВАННЯ В БАЗІ ===")
        scans = Scan.query.order_by(Scan.created_at.desc()).all()
        
        for scan in scans:
            user = User.query.get(scan.user_id) if scan.user_id else None
            print(f"\n--- Сканування ID: {scan.id} ---")
            print(f"Користувач: {user.email if user else 'Анонім'}")
            print(f"Дата: {scan.created_at}")
            print(f"Тип: {scan.input_type}, Метод: {scan.input_method}")
            print(f"Статус: {scan.safety_status}")
            
            # Інгредієнти
            ingredients = scan.get_ingredients_list()
            print(f"Знайдено інгредієнтів: {len(ingredients)}")
            
            for i, ing in enumerate(ingredients, 1):
                if isinstance(ing, dict):
                    print(f"  {i}. {ing.get('name', 'N/A')} (ризик: {ing.get('risk_level', 'N/A')})")
                else:
                    print(f"  {i}. {ing}")
            
            # Сирі дані
            print(f"Сирі дані (ingredients_detected): {type(scan.ingredients_detected)}")
            if scan.ingredients_detected:
                print(f"  JSON: {json.dumps(scan.ingredients_detected, indent=2, ensure_ascii=False)}")
            
            if scan.original_text:
                print(f"\nТекст (перші 150 символів):")
                print(scan.original_text[:150] + "...")
        
        print(f"\nВсього сканувань в базі: {len(scans)}")

def check_user_scans(email):
    """Перевірити сканування конкретного користувача"""
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"Користувача {email} не знайдено")
            return
        
        print(f"\n=== СКАНУВАННЯ КОРИСТУВАЧА: {email} ===")
        scans = Scan.query.filter_by(user_id=user.id).order_by(Scan.created_at.desc()).all()
        
        for scan in scans:
            print(f"\n--- Сканування ID: {scan.id} ---")
            print(f"Дата: {scan.created_at}")
            print(f"Тип: {scan.input_type}, Метод: {scan.input_method}")
            print(f"Статус: {scan.safety_status}")
            
            ingredients = scan.get_ingredients_list()
            print(f"Інгредієнтів: {len(ingredients)}")
            
            for i, ing in enumerate(ingredients[:5], 1):  # Показуємо перші 5
                if isinstance(ing, dict):
                    print(f"  {i}. {ing.get('name', 'N/A')}")
            
            if len(ingredients) > 5:
                print(f"  ... і ще {len(ingredients) - 5} інгредієнтів")
        
        print(f"\nВсього сканувань у користувача: {len(scans)}")

def fix_all_scans():
    """Виправити всі сканування в базі"""
    with app.app_context():
        from checker import IngredientChecker
        checker = IngredientChecker()
        
        scans = Scan.query.all()
        fixed_count = 0
        
        print(f"\n=== ВИПРАВЛЕННЯ {len(scans)} СКАНУВАНЬ ===")
        
        for scan in scans:
            if not scan.ingredients_detected and scan.original_text:
                # Аналізуємо текст заново
                detected = checker.find_ingredients(scan.original_text)
                
                if detected:
                    # Перетворюємо у правильний формат
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
                    
                    scan.ingredients_detected = ingredients_for_json
                    
                    # Оновлюємо статус
                    high_risk_count = sum(1 for ing in ingredients_for_json 
                                        if ing.get('risk_level') == 'high')
                    if high_risk_count > 0:
                        scan.safety_status = 'danger'
                    elif len(ingredients_for_json) > 0:
                        scan.safety_status = 'warning'
                    else:
                        scan.safety_status = 'safe'
                    
                    fixed_count += 1
                    print(f"Виправлено сканування {scan.id}: додано {len(detected)} інгредієнтів")
        
        if fixed_count > 0:
            db.session.commit()
            print(f"\nВиправлено сканувань: {fixed_count}")
        else:
            print("\nНема що виправляти")

def test_checker():
    """Тестування IngredientChecker"""
    from checker import IngredientChecker
    checker = IngredientChecker()
    
    test_texts = [
        "Sodium Laureth Sulfate and Parfum",
        "Состав: Натрію лаурет сульфат та Ароматизатор",
        "Ingredients: Formaldehyde, Methylparaben",
        "Безопасный крем с глицерином и алое вера",
    ]
    
    print("\n=== ТЕСТУВАННЯ INGREDIENT CHECKER ===")
    
    for i, text in enumerate(test_texts, 1):
        print(f"\nТест #{i}:")
        print(f"Текст: {text}")
        
        result = checker.find_ingredients(text)
        print(f"Знайдено: {len(result)} інгредієнтів")
        
        for ing in result:
            print(f"  - {ing['name']} ({ing['risk_level']})")

if __name__ == "__main__":
    print("ІНСТРУМЕНТИ ДЛЯ НАЛАГОДЖЕННЯ")
    print("=" * 40)
    
    # Розкоментуйте потрібну функцію:
    
    # 1. Показати всі сканування
    print_all_scans()
    
    # 2. Перевірити сканування користувача
    # check_user_scans("user@example.com")
    
    # 3. Виправити всі сканування
    # fix_all_scans()
    
    # 4. Тестування checker
    # test_checker()