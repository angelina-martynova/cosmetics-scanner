# debug_tools.py - инструменты для отладки
from app import app, db, User, Scan
import json

def print_all_scans():
    """Вывести все сканы в базе"""
    with app.app_context():
        print("\n=== ВСЕ СКАНИРОВАНИЯ В БАЗЕ ===")
        scans = Scan.query.order_by(Scan.created_at.desc()).all()
        
        for scan in scans:
            user = User.query.get(scan.user_id) if scan.user_id else None
            print(f"\n--- Скан ID: {scan.id} ---")
            print(f"Пользователь: {user.email if user else 'Аноним'}")
            print(f"Дата: {scan.created_at}")
            print(f"Тип: {scan.input_type}, Метод: {scan.input_method}")
            print(f"Статус: {scan.safety_status}")
            
            # Ингредиенты
            ingredients = scan.get_ingredients_list()
            print(f"Найдено ингредиентов: {len(ingredients)}")
            
            for i, ing in enumerate(ingredients, 1):
                if isinstance(ing, dict):
                    print(f"  {i}. {ing.get('name', 'N/A')} (риск: {ing.get('risk_level', 'N/A')})")
                else:
                    print(f"  {i}. {ing}")
            
            # Сырые данные
            print(f"Сырые данные (ingredients_detected): {type(scan.ingredients_detected)}")
            if scan.ingredients_detected:
                print(f"  JSON: {json.dumps(scan.ingredients_detected, indent=2, ensure_ascii=False)}")
            
            if scan.original_text:
                print(f"\nТекст (первые 150 символов):")
                print(scan.original_text[:150] + "...")
        
        print(f"\nВсего сканов в базе: {len(scans)}")

def check_user_scans(email):
    """Проверить сканы конкретного пользователя"""
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"Пользователь {email} не найден")
            return
        
        print(f"\n=== СКАНЫ ПОЛЬЗОВАТЕЛЯ: {email} ===")
        scans = Scan.query.filter_by(user_id=user.id).order_by(Scan.created_at.desc()).all()
        
        for scan in scans:
            print(f"\n--- Скан ID: {scan.id} ---")
            print(f"Дата: {scan.created_at}")
            print(f"Тип: {scan.input_type}, Метод: {scan.input_method}")
            print(f"Статус: {scan.safety_status}")
            
            ingredients = scan.get_ingredients_list()
            print(f"Ингредиентов: {len(ingredients)}")
            
            for i, ing in enumerate(ingredients[:5], 1):  # Показываем первые 5
                if isinstance(ing, dict):
                    print(f"  {i}. {ing.get('name', 'N/A')}")
            
            if len(ingredients) > 5:
                print(f"  ... и еще {len(ingredients) - 5} ингредиентов")
        
        print(f"\nВсего сканов у пользователя: {len(scans)}")

def fix_all_scans():
    """Исправить все сканы в базе"""
    with app.app_context():
        from checker import IngredientChecker
        checker = IngredientChecker()
        
        scans = Scan.query.all()
        fixed_count = 0
        
        print(f"\n=== ИСПРАВЛЕНИЕ {len(scans)} СКАНОВ ===")
        
        for scan in scans:
            if not scan.ingredients_detected and scan.original_text:
                # Анализируем текст заново
                detected = checker.find_ingredients(scan.original_text)
                
                if detected:
                    # Преобразуем в правильный формат
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
                    
                    # Обновляем статус
                    high_risk_count = sum(1 for ing in ingredients_for_json 
                                        if ing.get('risk_level') == 'high')
                    if high_risk_count > 0:
                        scan.safety_status = 'danger'
                    elif len(ingredients_for_json) > 0:
                        scan.safety_status = 'warning'
                    else:
                        scan.safety_status = 'safe'
                    
                    fixed_count += 1
                    print(f"✅ Исправлен скан {scan.id}: добавлено {len(detected)} ингредиентов")
        
        if fixed_count > 0:
            db.session.commit()
            print(f"\n✅ Исправлено сканов: {fixed_count}")
        else:
            print("\nℹ️ Нечего исправлять")

def test_checker():
    """Тестирование IngredientChecker"""
    from checker import IngredientChecker
    checker = IngredientChecker()
    
    test_texts = [
        "Sodium Laureth Sulfate and Parfum",
        "Состав: Натрію лаурет сульфат та Ароматизатор",
        "Ingredients: Formaldehyde, Methylparaben",
        "Безопасный крем с глицерином и алое вера",
    ]
    
    print("\n=== ТЕСТИРОВАНИЕ INGREDIENT CHECKER ===")
    
    for i, text in enumerate(test_texts, 1):
        print(f"\nТест #{i}:")
        print(f"Текст: {text}")
        
        result = checker.find_ingredients(text)
        print(f"Найдено: {len(result)} ингредиентов")
        
        for ing in result:
            print(f"  - {ing['name']} ({ing['risk_level']})")

if __name__ == "__main__":
    print("🔧 ИНСТРУМЕНТЫ ДЛЯ ОТЛАДКИ")
    print("=" * 40)
    
    # Раскомментируйте нужную функцию:
    
    # 1. Показать все сканы
    print_all_scans()
    
    # 2. Проверить сканы пользователя
    # check_user_scans("user@example.com")
    
    # 3. Исправить все сканы
    # fix_all_scans()
    
    # 4. Тестирование checker
    # test_checker()