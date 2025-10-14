import os
from dotenv import load_dotenv

class Environment:

    def __init__(self):
        load_dotenv(dotenv_path="../assets/.env")
        self.weather_api_key = os.getenv("WEATHER_API_KEY")
