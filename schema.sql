-- schema.sql — PostgreSQL DDL для Million Playlist Dataset (MPD)
-- Запуск: psql -U postgres -d spotifydb -f schema.sql

BEGIN;

-- Схема
CREATE SCHEMA IF NOT EXISTS spotify;
SET search_path TO spotify;

-- 1) Артисты
CREATE TABLE IF NOT EXISTS artists (
  id           BIGSERIAL PRIMARY KEY,
  spotify_id   TEXT UNIQUE NOT NULL,          -- '7EK1bQADBoqbYXnT4Cqv9w'
  name         TEXT NOT NULL,
  created_at   TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS artists_name_ci_idx ON artists (LOWER(name));

-- 2) Альбомы
CREATE TABLE IF NOT EXISTS albums (
  id            BIGSERIAL PRIMARY KEY,
  spotify_id    TEXT UNIQUE,                  -- '6wh2lqPzAaH4TTh5rF0iiv'
  artist_id     BIGINT NOT NULL REFERENCES artists(id) ON DELETE RESTRICT,
  name          TEXT NOT NULL,
  created_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS albums_artist_idx   ON albums (artist_id);
CREATE INDEX IF NOT EXISTS albums_name_ci_idx  ON albums (LOWER(name));

-- 3) Треки
CREATE TABLE IF NOT EXISTS tracks (
  id            BIGSERIAL PRIMARY KEY,
  spotify_id    TEXT UNIQUE,                  -- '1h17NceCJxOIrx8BUKfBNe'
  album_id      BIGINT REFERENCES albums(id) ON DELETE SET NULL,
  name          TEXT NOT NULL,
  duration_ms   INTEGER NOT NULL CHECK (duration_ms > 0),
  created_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS tracks_album_idx    ON tracks (album_id);
CREATE INDEX IF NOT EXISTS tracks_name_ci_idx  ON tracks (LOWER(name));

-- M2M: трек ↔ артист (фиты/дуэты)
CREATE TABLE IF NOT EXISTS track_artists (
  track_id   BIGINT NOT NULL REFERENCES tracks(id)  ON DELETE CASCADE,
  artist_id  BIGINT NOT NULL REFERENCES artists(id) ON DELETE RESTRICT,
  ord        SMALLINT,                              -- порядок в кредите (0 = главный)
  PRIMARY KEY (track_id, artist_id)
);
CREATE INDEX IF NOT EXISTS track_artists_artist_idx ON track_artists (artist_id);

-- 4) Плейлисты
CREATE TABLE IF NOT EXISTS playlists (
  id              BIGSERIAL PRIMARY KEY,
  pid             BIGINT UNIQUE NOT NULL,           -- MPD playlist id (напр. 837000)
  name            TEXT,
  collaborative   BOOLEAN,
  modified_at     TIMESTAMPTZ,                      -- TO_TIMESTAMP(unix_seconds)
  num_tracks      INTEGER,
  num_albums      INTEGER,
  num_followers   INTEGER,
  created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS playlists_name_ci_idx ON playlists (LOWER(name));

-- 5) Состав плейлистов (позиции)
CREATE TABLE IF NOT EXISTS playlist_tracks (
  playlist_id   BIGINT  NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
  position      INTEGER NOT NULL CHECK (position >= 0),   -- порядок внутри плейлиста
  track_id      BIGINT  NOT NULL REFERENCES tracks(id) ON DELETE RESTRICT,
  added_at      TIMESTAMPTZ,
  PRIMARY KEY (playlist_id, position)
);
CREATE INDEX IF NOT EXISTS playlist_tracks_track_idx ON playlist_tracks (track_id);

COMMIT;
