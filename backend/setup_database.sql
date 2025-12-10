-- setup_database.sql
-- Этот файл содержит SQL команды для настройки базы данных
-- Запускать по частям в pgAdmin Query Tool

-- ============================================
-- ШАГ 1: Создание базы данных (выполнять как postgres)
-- ============================================
CREATE DATABASE cosmetics_db
    ENCODING 'UTF8'
    LC_COLLATE 'C'
    LC_CTYPE 'C'
    TEMPLATE template0;

COMMENT ON DATABASE cosmetics_db IS 'База данных для дипломного проекта Cosmetics Scanner';

-- ============================================
-- ШАГ 2: Создание пользователя приложения (опционально)
-- ============================================
CREATE USER cosmetics_app WITH 
    PASSWORD 'AppPassword123!'
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    LOGIN;

-- ============================================
-- ШАГ 3: Подключиться к cosmetics_db вручную в pgAdmin
-- Затем выполнить следующий блок:
-- ============================================

-- Дать права на базу данных
GRANT ALL PRIVILEGES ON DATABASE cosmetics_db TO cosmetics_app;

-- Дать права на схему public
GRANT ALL ON SCHEMA public TO cosmetics_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cosmetics_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cosmetics_app;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO cosmetics_app;

-- ============================================
-- ШАГ 4: Альтернативно - простой вариант для диплома
-- (если хотите использовать пользователя postgres)
-- ============================================
-- Ничего не делать, пользователь postgres уже имеет все права