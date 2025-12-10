# backend/init_db.py
import sys
import os

print("=" * 60)
print("ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ COSMETICS SCANNER")
print("=" * 60)

try:
    # Импортируем app из текущей папки
    from app import app, db, User
    from sqlalchemy import text
    
    with app.app_context():
        # 1. Создаем таблицы
        print("\nСоздание таблиц...")
        db.create_all()
        print("Таблицы созданы")
        
        # 2. Проверяем PostgreSQL
        print("\nПроверка подключения к PostgreSQL...")
        try:
            result = db.session.execute(text("SELECT version()"))
            postgres_version = result.fetchone()[0]
            print(f"PostgreSQL: {postgres_version}")
        except Exception as e:
            print(f"Ошибка PostgreSQL: {e}")
            print("\nВозможные причины:")
            print("1. PostgreSQL не запущен")
            print("2. Неправильный пароль в app.py")
            print("3. База cosmetics_db не создана")
            sys.exit(1)
        
        # 3. Создаем тестовых пользователей
        print("\nСоздание тестовых пользователей...")
        
        # Список пользователей для создания
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
                print(f"Создан: {user_data['email']}")
            else:
                print(f"Уже существует: {user_data['email']}")
        
        if created_count > 0:
            db.session.commit()
            print(f"\nСохранено {created_count} новых пользователей")
        
        # 4. Статистика
        print("\nСтатистика базы данных:")
        users_count = User.query.count()
        print(f"Пользователей: {users_count}")
        
        # Проверяем таблицы
        result = db.session.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        tables_count = result.fetchone()[0]
        print(f"Таблиц: {tables_count}")
        
        print("\n" + "=" * 60)
        print("БАЗА ДАННЫХ ГОТОВА К РАБОТЕ!")
        print("=" * 60)
        
        print("\nТЕСТОВЫЕ УЧЕТНЫЕ ЗАПИСИ:")
        print("   Email: admin@cosmetics.com")
        print("   Пароль: admin123")
        print("\n   Email: user@example.com")
        print("   Пароль: user123")
        
        print("\nЗапустите приложение:")
        print("   python app.py")
        print("\nОткройте в браузере: http://localhost:5000")
        
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("\nУбедитесь, что:")
    print("1. Вы находитесь в папке backend")
    print("2. Файл app.py существует в текущей папке")
    print("3. Установлены все зависимости: pip install -r requirements.txt")
    
except Exception as e:
    print(f"Неожиданная ошибка: {e}")
    import traceback
    traceback.print_exc()