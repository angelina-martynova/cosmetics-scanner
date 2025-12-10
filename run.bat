@echo off
echo ========================================
echo  COSMETICS SCANNER - ЗАПУСК
echo ========================================
echo.

:: Переходим в папку backend
cd /d "%~dp0backend"

echo 1. Проверка зависимостей...
pip install -r ../requirements.txt > nul 2>&1
if %errorlevel% equ 0 (
    echo Зависимости установлены
) else (
    echo Ошибка установки зависимостей
)

echo.
echo 2. Инициализация базы данных...
python -c "
try:
    from app import app, db, User
    with app.app_context():
        db.create_all()
        print('Таблицы созданы')
        if User.query.count() == 0:
            admin = User(email='admin@cosmetics.com', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('Тестовый пользователь создан')
except Exception as e:
    print(f'Ошибка: {e}')
    import traceback
    traceback.print_exc()
"

echo.
echo 3. Запуск приложения...
echo.
echo ОТКРОЙТЕ В БРАУЗЕРЕ: http://localhost:5000
echo ТЕСТОВЫЕ ДАННЫЕ:
echo     Email: admin@cosmetics.com
echo     Пароль: admin123
echo.
echo ========================================
python app.py

pause