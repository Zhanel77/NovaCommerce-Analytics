# Aurora Music Analytics

***Коротко о проекте: аналитика плейлистов Spotify: артисты, альбомы, треки, предпочтения по годам/жанрам, «рецепт хита».***

***Как запускать:***

- docker compose up -d (PostgreSQL)

- psql -h localhost -U postgres -d spotifydb -f schema.sql

- python load_mpd.py (загрузка JSON→БД)

- python main.py (SQL-запросы → вывод/CSV)

- Инструменты: PostgreSQL, Python (pandas, SQLAlchemy), Apache Superset.
