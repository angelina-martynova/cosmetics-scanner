-- setup_database.sql
-- Цей файл містить SQL команди для налаштування бази даних
-- Запускати частинами в pgAdmin Query Tool

-- ============================================
-- КРОК 1: Створення бази даних (виконувати як postgres)
-- ============================================
CREATE DATABASE cosmetics_db
    ENCODING 'UTF8'
    LC_COLLATE 'C'
    LC_CTYPE 'C'
    TEMPLATE template0;

COMMENT ON DATABASE cosmetics_db IS 'База даних для дипломного проекту Cosmetics Scanner';

-- ============================================
-- КРОК 2: Створення користувача додатка (необов'язково)
-- ============================================
CREATE USER cosmetics_app WITH 
    PASSWORD 'AppPassword123!'
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    LOGIN;

-- ============================================
-- КРОК 3: Підключитися до cosmetics_db вручну в pgAdmin
-- Потім виконати наступний блок:
-- ============================================

-- Надати права на базу даних
GRANT ALL PRIVILEGES ON DATABASE cosmetics_db TO cosmetics_app;

-- Надати права на схему public
GRANT ALL ON SCHEMA public TO cosmetics_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cosmetics_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cosmetics_app;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO cosmetics_app;

-- ============================================
-- КРОК 4: Альтернативно - простий варіант для диплома
-- (якщо хочете використовувати користувача postgres)
-- ============================================
-- Нічого не робити, користувач postgres вже має всі права