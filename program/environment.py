import os
from dotenv import load_dotenv

class Environment:

    def __init__(self):
        load_dotenv(dotenv_path="/home/Mikickiewicz/Pycharm_projects_linux/PythonProject/Discus_2cT_Lift_Calculator_ver01/assets/.env")
        self.weather_api_key = os.getenv("WEATHER_API_KEY")
