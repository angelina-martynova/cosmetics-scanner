# backend/init_db.py
import sys
import os

print("=" * 60)
print("ІНІЦІАЛІЗАЦІЯ БАЗИ ДАНИХ COSMETICS SCANNER")
print("=" * 60)

try:
    # Імпортуємо app з поточної папки
    from app import app, db, User
    from sqlalchemy import text
    
    with app.app_context():
        # 1. Створюємо таблиці
        print("\nСтворення таблиць...")
        db.create_all()
        print("Таблиці створено")
        
        # 2. Перевіряємо PostgreSQL
        print("\nПеревірка підключення до PostgreSQL...")
        try:
            result = db.session.execute(text("SELECT version()"))
            postgres_version = result.fetchone()[0]
            print(f"PostgreSQL: {postgres_version}")
        except Exception as e:
            print(f"Помилка PostgreSQL: {e}")
            print("\nМожливі причини:")
            print("1. PostgreSQL не запущено")
            print("2. Неправильний пароль в app.py")
            print("3. Базу cosmetics_db не створено")
            sys.exit(1)
        
        # 3. Створюємо тестових користувачів
        print("\nСтворення тестових користувачів...")
        
        # Список користувачів для створення
        test_users = [
            {"email": "admin@cosmetics.com", "password": "admin123", "role": "admin"},
            {"email": "user@example.com", "password": "user123", "role": "user"},
        ]
        
        created_count = 0
        for user_data in test_users:
            existing = User.query.filter_by(email=user_data["email"]).first()
            if not existing:
                new_user = User(
                    email=user_data["email"],
                    role=user_data["role"]
                )
                new_user.set_password(user_data["password"])
                db.session.add(new_user)
                created_count += 1
                print(f"Створено: {user_data['email']}")
            else:
                print(f"Вже існує: {user_data['email']}")
        
        if created_count > 0:
            db.session.commit()
            print(f"\nЗбережено {created_count} нових користувачів")
        
        # 4. Статистика
        print("\nСтатистика бази даних:")
        users_count = User.query.count()
        print(f"Користувачів: {users_count}")
        
        # Перевіряємо таблиці
        result = db.session.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        tables_count = result.fetchone()[0]
        print(f"Таблиць: {tables_count}")
        
        print("\n" + "=" * 60)
        print("БАЗА ДАНИХ ГОТОВА ДО РОБОТИ!")
        print("=" * 60)
        
        print("\nТЕСТОВІ ОБЛІКОВІ ЗАПИСИ:")
        print("   Email: admin@cosmetics.com")
        print("   Пароль: admin123")
        print("\n   Email: user@example.com")
        print("   Пароль: user123")
        
        print("\nЗапустіть програму:")
        print("   python app.py")
        print("\nВідкрийте в браузері: http://localhost:5000")
        
except ImportError as e:
    print(f"Помилка імпорту: {e}")
    print("\nПереконайтеся, що:")
    print("1. Ви знаходитесь в папці backend")
    print("2. Файл app.py існує в поточній папці")
    print("3. Встановлені всі залежності: pip install -r requirements.txt")
    
except Exception as e:
    print(f"Неочікувана помилка: {e}")
    import traceback
    traceback.print_exc()