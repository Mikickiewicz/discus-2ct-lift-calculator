import requests
from environment import Environment


class Weather:
    def __init__(self, city):
        self.env = Environment()
        self.weather_data = None
        self.city = city
        self.api_connection(self.city)


    def api_connection(self ,city):
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"appid": self.env.weather_api_key,
                  "q": f"{city}",
                  }

        resp = requests.get(url=url , params=params)
        resp.raise_for_status()
        self.weather_data = resp.json()


    def humidity(self):
        return self.weather_data["main"]["humidity"]


    def temperature(self):
        return self.weather_data["main"]["temp"]


    def wind(self):
        return self.weather_data["wind"]["speed"]


    def wind_direction(self):
        return self.weather_data["wind"]["deg"]


    def wind_speed(self):
        return self.weather_data["wind"]["speed"]
    
    def pressure(self):
        """Return pressure in hPa"""
        return self.weather_data["main"]["pressure"]
