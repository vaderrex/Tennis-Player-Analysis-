CREATE TABLE IF NOT EXISTS categories (
    category_id VARCHAR(64) PRIMARY KEY,
    category_name VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS competitions (
    competition_id VARCHAR(64) PRIMARY KEY,
    competition_name VARCHAR(255) NOT NULL,
    parent_id VARCHAR(64),
    type VARCHAR(80),
    gender VARCHAR(40),
    category_id VARCHAR(64) NOT NULL,
    CONSTRAINT fk_competitions_parent
        FOREIGN KEY (parent_id) REFERENCES competitions (competition_id),
    CONSTRAINT fk_competitions_category
        FOREIGN KEY (category_id) REFERENCES categories (category_id)
);

CREATE TABLE IF NOT EXISTS complexes (
    complex_id VARCHAR(64) PRIMARY KEY,
    complex_name VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS venues (
    venue_id VARCHAR(64) PRIMARY KEY,
    venue_name VARCHAR(255) NOT NULL,
    city_name VARCHAR(255),
    country_name VARCHAR(255),
    country_code VARCHAR(16),
    timezone VARCHAR(128),
    complex_id VARCHAR(64) NOT NULL,
    CONSTRAINT fk_venues_complex
        FOREIGN KEY (complex_id) REFERENCES complexes (complex_id)
);

CREATE TABLE IF NOT EXISTS competitors (
    competitor_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(255),
    country_code VARCHAR(16),
    abbreviation VARCHAR(64)
);

CREATE TABLE IF NOT EXISTS competitor_rankings (
    rank_id INTEGER AUTO_INCREMENT PRIMARY KEY,
    rank INTEGER NOT NULL,
    movement INTEGER,
    points INTEGER,
    competitions_played INTEGER,
    competitor_id VARCHAR(64) NOT NULL,
    CONSTRAINT uq_competitor_rankings_competitor UNIQUE (competitor_id),
    CONSTRAINT fk_rankings_competitor
        FOREIGN KEY (competitor_id) REFERENCES competitors (competitor_id)
);
