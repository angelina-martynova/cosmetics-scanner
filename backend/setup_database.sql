-- setup_database.sql (v2 — розширена схема)
-- Cosmetics Scanner — дипломний проект
--
-- Цей файл містить SQL команди для налаштування бази даних.
-- Запускати частинами в pgAdmin Query Tool.
--
-- Зміни відносно v1:
--   1. Таблиця ingredients розширена: inci_name, cas_number, ewg_score,
--      eu_max_concentration, eu_regulation_annex, is_banned_eu,
--      source_of_risk_assessment, verified, verified_at, verified_by,
--      description_en.
--   2. Нова таблиця ingredient_aliases — синоніми, переклади, OCR-виправлення.
--   3. Нова таблиця scan_ingredients — нормалізований зв'язок Scan ↔ Ingredient.
--   4. Індекси для пошуку та фільтрації.

-- ============================================
-- КРОК 1: Створення бази даних (виконувати як postgres)
-- ============================================
CREATE DATABASE cosmetics_db
    ENCODING 'UTF8'
    LC_COLLATE 'C'
    LC_CTYPE 'C'
    TEMPLATE template0;

COMMENT ON DATABASE cosmetics_db IS 'База даних для дипломного проекту Cosmetics Scanner v2';

-- ============================================
-- КРОК 2: Створення користувача додатка
-- ============================================
CREATE USER cosmetics_app WITH
    PASSWORD 'AppPassword123!'
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    LOGIN;

-- ============================================
-- КРОК 3: Підключитися до cosmetics_db в pgAdmin
-- Потім виконати наступні блоки:
-- ============================================

-- Надати права
GRANT ALL PRIVILEGES ON DATABASE cosmetics_db TO cosmetics_app;
GRANT ALL ON SCHEMA public TO cosmetics_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cosmetics_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cosmetics_app;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO cosmetics_app;

-- ============================================
-- КРОК 4: Створення таблиць
-- ============================================

-- ─── КОРИСТУВАЧІ ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(120) UNIQUE NOT NULL,
    password_hash   VARCHAR(255),
    role            VARCHAR(20) DEFAULT 'user',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login      TIMESTAMP
);

COMMENT ON TABLE users IS 'Користувачі системи (звичайні та адміністратори)';
COMMENT ON COLUMN users.role IS 'Роль: user або admin';

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);


-- ─── ІНГРЕДІЄНТИ (РОЗШИРЕНА) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS ingredients (
    id                          SERIAL PRIMARY KEY,

    -- Основні поля
    name                        VARCHAR(200) UNIQUE NOT NULL,
    risk_level                  VARCHAR(20) DEFAULT 'unknown',
    category                    VARCHAR(50),
    description                 TEXT,
    created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Нові поля v2
    inci_name                   VARCHAR(200),
    description_en              TEXT,
    cas_number                  VARCHAR(30),
    ewg_score                   INTEGER CHECK (ewg_score BETWEEN 1 AND 10),
    eu_max_concentration        VARCHAR(50),
    eu_regulation_annex         VARCHAR(20),
    is_banned_eu                BOOLEAN DEFAULT FALSE,
    source_of_risk_assessment   VARCHAR(100),
    verified                    BOOLEAN DEFAULT FALSE,
    verified_at                 TIMESTAMP,
    verified_by                 VARCHAR(100)
);

COMMENT ON TABLE ingredients IS 'Косметичні інгредієнти з регуляторними даними';
COMMENT ON COLUMN ingredients.inci_name IS 'Канонічна INCI-назва (International Nomenclature of Cosmetic Ingredients)';
COMMENT ON COLUMN ingredients.cas_number IS 'CAS Registry Number (Chemical Abstracts Service)';
COMMENT ON COLUMN ingredients.ewg_score IS 'EWG Skin Deep Score: 1 (безпечно) — 10 (високий ризик)';
COMMENT ON COLUMN ingredients.eu_max_concentration IS 'Максимальна допустима концентрація за EU Regulation 1223/2009';
COMMENT ON COLUMN ingredients.eu_regulation_annex IS 'Додаток EU Reg.: II (заборонено), III-VI (обмеження)';
COMMENT ON COLUMN ingredients.is_banned_eu IS 'TRUE якщо інгредієнт заборонений в ЄС (Annex II)';
COMMENT ON COLUMN ingredients.source_of_risk_assessment IS 'Джерело оцінки: CosIng, SCCS, EWG, manual, heuristic';
COMMENT ON COLUMN ingredients.verified IS 'TRUE якщо перевірено адміністратором';

CREATE INDEX IF NOT EXISTS idx_ingredients_name ON ingredients (name);
CREATE INDEX IF NOT EXISTS idx_ingredients_inci_name ON ingredients (inci_name);
CREATE INDEX IF NOT EXISTS idx_ingredients_cas_number ON ingredients (cas_number);
CREATE INDEX IF NOT EXISTS idx_ingredients_risk_level ON ingredients (risk_level);
CREATE INDEX IF NOT EXISTS idx_ingredients_category ON ingredients (category);
CREATE INDEX IF NOT EXISTS idx_ingredients_verified ON ingredients (verified);
CREATE INDEX IF NOT EXISTS idx_ingredients_is_banned ON ingredients (is_banned_eu);
CREATE INDEX IF NOT EXISTS idx_ingredients_name_lower ON ingredients (LOWER(name));


-- ─── СИНОНІМИ ІНГРЕДІЄНТІВ (НОВА ТАБЛИЦЯ) ──────────────────────
CREATE TABLE IF NOT EXISTS ingredient_aliases (
    id              SERIAL PRIMARY KEY,
    ingredient_id   INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,

    alias           VARCHAR(200) NOT NULL,
    alias_lower     VARCHAR(200) NOT NULL,

    alias_type      VARCHAR(30) DEFAULT 'common',
    -- Типи: inci, translation, ocr_fix, abbreviation, trade_name, e_code, common

    language        VARCHAR(5),
    -- ISO 639-1: uk, ru, en, fr, de тощо (NULL якщо не мовний)

    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_alias_lower UNIQUE (alias_lower)
);

COMMENT ON TABLE ingredient_aliases IS 'Синоніми інгредієнтів: INCI-варіанти, переклади, OCR-помилки, скорочення';
COMMENT ON COLUMN ingredient_aliases.alias_type IS 'inci | translation | ocr_fix | abbreviation | trade_name | e_code | common';
COMMENT ON COLUMN ingredient_aliases.language IS 'ISO 639-1 код мови (uk, ru, en, fr, de)';

CREATE INDEX IF NOT EXISTS idx_aliases_ingredient_id ON ingredient_aliases (ingredient_id);
CREATE INDEX IF NOT EXISTS idx_aliases_alias_lower ON ingredient_aliases (alias_lower);
CREATE INDEX IF NOT EXISTS idx_aliases_type ON ingredient_aliases (alias_type);
CREATE INDEX IF NOT EXISTS idx_aliases_language ON ingredient_aliases (language);


-- ─── СКАНУВАННЯ ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scans (
    id                      SERIAL PRIMARY KEY,
    user_id                 INTEGER REFERENCES users(id) ON DELETE SET NULL,
    input_type              VARCHAR(50),
    input_method            VARCHAR(50),
    original_text           TEXT,
    safety_status           VARCHAR(20) DEFAULT 'safe',
    safety_message          VARCHAR(255),
    contains_unknown        BOOLEAN DEFAULT FALSE,
    unknown_count           INTEGER DEFAULT 0,
    image_filename          VARCHAR(255),
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- JSON-поле для зворотної сумісності
    ingredients_detected    JSONB
);

COMMENT ON TABLE scans IS 'Результати сканувань косметичних продуктів';
COMMENT ON COLUMN scans.safety_status IS 'safe | low_warning | warning | danger';
COMMENT ON COLUMN scans.ingredients_detected IS 'JSON — для зворотної сумісності з v1';

CREATE INDEX IF NOT EXISTS idx_scans_user_id ON scans (user_id);
CREATE INDEX IF NOT EXISTS idx_scans_created_at ON scans (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scans_safety_status ON scans (safety_status);


-- ─── ЗВ'ЯЗОК СКАН ↔ ІНГРЕДІЄНТ (НОВА ТАБЛИЦЯ) ─────────────────
CREATE TABLE IF NOT EXISTS scan_ingredients (
    id              SERIAL PRIMARY KEY,
    scan_id         INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    ingredient_id   INTEGER REFERENCES ingredients(id) ON DELETE SET NULL,

    -- Назва як розпізнано OCR (до нормалізації)
    raw_name        VARCHAR(200),

    -- Назва після нормалізації
    normalized_name VARCHAR(200),

    -- Кешовані дані (щоб не робити JOIN при відображенні)
    risk_level      VARCHAR(20) DEFAULT 'unknown',
    category        VARCHAR(50),
    description     TEXT,

    -- Позиція в списку складу (1 = найвища концентрація)
    position        INTEGER,

    -- Тип збігу: exact, alias, fuzzy, substring, external, heuristic, not_found
    match_type      VARCHAR(30),

    -- Оцінка збігу для fuzzy (0-100)
    match_score     REAL,

    -- Джерело: database, openbeautyfacts, pubchem, chebi, heuristic
    source          VARCHAR(50),

    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE scan_ingredients IS 'Нормалізований зв''язок: один рядок = один інгредієнт у скані';
COMMENT ON COLUMN scan_ingredients.position IS 'Позиція у складі (1 = перший = найбільша концентрація)';
COMMENT ON COLUMN scan_ingredients.match_type IS 'exact | alias | fuzzy | substring | external | heuristic | not_found';
COMMENT ON COLUMN scan_ingredients.source IS 'database | openbeautyfacts | pubchem | chebi | heuristic';

CREATE INDEX IF NOT EXISTS idx_scan_ingredients_scan_id ON scan_ingredients (scan_id);
CREATE INDEX IF NOT EXISTS idx_scan_ingredients_ingredient_id ON scan_ingredients (ingredient_id);
CREATE INDEX IF NOT EXISTS idx_scan_ingredients_risk_level ON scan_ingredients (risk_level);
CREATE INDEX IF NOT EXISTS idx_scan_ingredients_match_type ON scan_ingredients (match_type);


-- ============================================
-- КРОК 5: Корисні VIEW (для звітів та аналітики)
-- ============================================

-- Статистика інгредієнтів за рівнем ризику
CREATE OR REPLACE VIEW v_ingredient_risk_stats AS
SELECT
    risk_level,
    COUNT(*) AS total,
    SUM(CASE WHEN verified THEN 1 ELSE 0 END) AS verified_count,
    SUM(CASE WHEN is_banned_eu THEN 1 ELSE 0 END) AS banned_eu_count
FROM ingredients
GROUP BY risk_level
ORDER BY
    CASE risk_level
        WHEN 'high' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'low' THEN 3
        WHEN 'safe' THEN 4
        ELSE 5
    END;

COMMENT ON VIEW v_ingredient_risk_stats IS 'Статистика інгредієнтів за рівнем ризику';


-- Топ інгредієнтів за частотою зустрічання у сканах
CREATE OR REPLACE VIEW v_top_ingredients AS
SELECT
    COALESCE(si.normalized_name, si.raw_name) AS ingredient_name,
    i.risk_level,
    i.category,
    i.verified,
    COUNT(*) AS scan_count
FROM scan_ingredients si
LEFT JOIN ingredients i ON si.ingredient_id = i.id
GROUP BY COALESCE(si.normalized_name, si.raw_name), i.risk_level, i.category, i.verified
ORDER BY scan_count DESC
LIMIT 50;

COMMENT ON VIEW v_top_ingredients IS 'Топ-50 найчастіших інгредієнтів у сканах';


-- Ефективність розпізнавання (скільки exact vs fuzzy vs not_found)
CREATE OR REPLACE VIEW v_match_type_stats AS
SELECT
    match_type,
    COUNT(*) AS total,
    ROUND(COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER (), 0), 1) AS percentage
FROM scan_ingredients
WHERE match_type IS NOT NULL
GROUP BY match_type
ORDER BY total DESC;

COMMENT ON VIEW v_match_type_stats IS 'Статистика типів збігу (exact, fuzzy, heuristic тощо)';


-- Неверифіковані інгредієнти (для адмін-панелі)
CREATE OR REPLACE VIEW v_unverified_ingredients AS
SELECT
    i.id,
    i.name,
    i.risk_level,
    i.category,
    i.source_of_risk_assessment AS source,
    i.created_at,
    COUNT(si.id) AS times_found_in_scans
FROM ingredients i
LEFT JOIN scan_ingredients si ON si.ingredient_id = i.id
WHERE i.verified = FALSE
GROUP BY i.id, i.name, i.risk_level, i.category, i.source_of_risk_assessment, i.created_at
ORDER BY times_found_in_scans DESC, i.created_at DESC;

COMMENT ON VIEW v_unverified_ingredients IS 'Неверифіковані інгредієнти з кількістю зустрічань';


-- Заборонені в ЄС інгредієнти, знайдені у сканах
CREATE OR REPLACE VIEW v_banned_in_scans AS
SELECT
    i.name,
    i.cas_number,
    i.eu_regulation_annex,
    s.id AS scan_id,
    s.user_id,
    s.created_at AS scan_date
FROM scan_ingredients si
JOIN ingredients i ON si.ingredient_id = i.id
JOIN scans s ON si.scan_id = s.id
WHERE i.is_banned_eu = TRUE
ORDER BY s.created_at DESC;

COMMENT ON VIEW v_banned_in_scans IS 'Випадки виявлення заборонених в ЄС інгредієнтів';


-- ============================================
-- КРОК 6: Права для cosmetics_app на нові об'єкти
-- ============================================
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cosmetics_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cosmetics_app;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO cosmetics_app;


-- ============================================
-- КРОК 7: Міграція існуючої БД (якщо оновлюєте з v1)
-- Виконувати тільки якщо таблиці вже існують!
-- ============================================

-- Додати нові колонки до ingredients (якщо таблиця вже існує)
-- ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS inci_name VARCHAR(200);
-- ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS description_en TEXT;
-- ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS cas_number VARCHAR(30);
-- ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS ewg_score INTEGER;
-- ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS eu_max_concentration VARCHAR(50);
-- ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS eu_regulation_annex VARCHAR(20);
-- ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS is_banned_eu BOOLEAN DEFAULT FALSE;
-- ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS source_of_risk_assessment VARCHAR(100);
-- ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS verified BOOLEAN DEFAULT FALSE;
-- ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP;
-- ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS verified_by VARCHAR(100);
--
-- CREATE INDEX IF NOT EXISTS idx_ingredients_inci_name ON ingredients (inci_name);
-- CREATE INDEX IF NOT EXISTS idx_ingredients_cas_number ON ingredients (cas_number);
-- CREATE INDEX IF NOT EXISTS idx_ingredients_verified ON ingredients (verified);
-- CREATE INDEX IF NOT EXISTS idx_ingredients_is_banned ON ingredients (is_banned_eu);
--
-- -- Позначити існуючі інгредієнти як верифіковані
-- UPDATE ingredients SET verified = TRUE, verified_at = NOW(), verified_by = 'migration_v2'
-- WHERE verified IS NULL OR verified = FALSE;
