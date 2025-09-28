import os
from dotenv import load_dotenv

class Environment():
    load_dotenv()

    def __init__(self):
        self.weather_api_key = os.getenv("WEATHER_API_KEY")
