import os
import time
import requests
from prometheus_client import start_http_server, Gauge, Info

# ========= НАСТРОЙКИ =========
# возьми ключ на https://home.openweathermap.org/api_keys
API_KEY = os.getenv("OPENWEATHER_API_KEY", "6bea3a864d4087d591a70398c28feb07")
CITY = os.getenv("OPENWEATHER_CITY", "Astana")
COUNTRY = os.getenv("OPENWEATHER_COUNTRY", "KZ")  # не обязательно
UPDATE_INTERVAL = 20  # сек

# ========= МЕТРИКИ (10+ штук) =========
m_temp = Gauge("owm_temperature_celsius", "Current temperature from OpenWeather, C", ["city"])
m_feels = Gauge("owm_feels_like_celsius", "Feels like temperature, C", ["city"])
m_hum = Gauge("owm_humidity_percent", "Humidity, %", ["city"])
m_press = Gauge("owm_pressure_hpa", "Pressure, hPa", ["city"])
m_wind = Gauge("owm_wind_speed_ms", "Wind speed, m/s", ["city"])
m_clouds = Gauge("owm_clouds_percent", "Cloudiness, %", ["city"])
m_visibility = Gauge("owm_visibility_m", "Visibility, m", ["city"])
m_rain_1h = Gauge("owm_rain_1h_mm", "Rain volume for the last 1 hour, mm", ["city"])
m_snow_1h = Gauge("owm_snow_1h_mm", "Snow volume for the last 1 hour, mm", ["city"])
m_api_up = Gauge("owm_api_up", "Weather API status 1=up 0=down")
m_last_update = Gauge("owm_last_update_unixtime", "Last successful update timestamp")
info_exporter = Info("owm_exporter_info", "Info about this exporter")

info_exporter.info({
    "source": "openweather",
    "city": CITY,
    "author": "student"
})


def fetch_and_update():
    """забрать данные из OpenWeather и обновить метрики"""
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": f"{CITY},{COUNTRY}",
        "appid": API_KEY,
        "units": "metric"  # чтобы было в градусах C
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        city_label = CITY

        main = data.get("main", {})
        wind = data.get("wind", {})
        clouds = data.get("clouds", {})
        rain = data.get("rain", {})
        snow = data.get("snow", {})

        m_temp.labels(city=city_label).set(main.get("temp", 0))
        m_feels.labels(city=city_label).set(main.get("feels_like", 0))
        m_hum.labels(city=city_label).set(main.get("humidity", 0))
        m_press.labels(city=city_label).set(main.get("pressure", 0))
        m_wind.labels(city=city_label).set(wind.get("speed", 0))
        m_clouds.labels(city=city_label).set(clouds.get("all", 0))
        m_visibility.labels(city=city_label).set(data.get("visibility", 0))
        m_rain_1h.labels(city=city_label).set(rain.get("1h", 0))
        m_snow_1h.labels(city=city_label).set(snow.get("1h", 0))

        m_api_up.set(1)
        m_last_update.set(time.time())
    except Exception as e:
        # если API упал — показываем это
        m_api_up.set(0)


if __name__ == "__main__":
    # поднимаем HTTP-сервер на 8000
    start_http_server(8000)
    print("Custom exporter started on :8000")
    while True:
        fetch_and_update()
        time.sleep(UPDATE_INTERVAL)
