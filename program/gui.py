from PySide6.QtWidgets import (QWidget, QApplication, QMainWindow, QPushButton,
                               QHBoxLayout, QVBoxLayout, QGroupBox, QGridLayout,
                               QLabel, QComboBox, QDoubleSpinBox, QSplitter, QTabWidget,
                               QSlider, QCompleter, QLineEdit)
from PySide6.QtCore import Qt, QTimer
import sys
from models import Aircraft, LiftModel, WingConfig
from performance import PerformanceCalculator
from plots import create_plot_canvas
from weather import Weather

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        # Initialize models
        self.aircraft_configs = {
            "15m": Aircraft(wing=WingConfig("15m", 15.0, 10.18)),
            "18m": Aircraft(wing=WingConfig("18m", 18.0, 11.36))
        }
        self.current_aircraft = self.aircraft_configs["18m"]
        self.lift_model = LiftModel(self.current_aircraft)
        self.performance = PerformanceCalculator(self.current_aircraft, self.lift_model)

        # Weather data storage
        self.current_weather = None
        self.last_weather_city = None
        
        # Setup UI
        self.setupUi()
        self.create_control_panel(self.splitter)
        self.create_visualization_panel(self.splitter)

        # Connect signals
        self.connect_signals()

        # Debounce timer for parameter changes
        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.update_plots)
        
        # Weather update timer (5 minutes)
        self.weather_timer = QTimer(self)
        self.weather_timer.timeout.connect(self.update_weather_data)
        self.weather_timer.start(300000)  # 5 minutes in milliseconds

        # Initial weather and plot update after the event loop starts
        QTimer.singleShot(0, self.initial_weather_update)
        QTimer.singleShot(100, self.update_plots)


    def setupUi(self):

        self.setWindowTitle("Discus-2cT Lift Calculator - Advanced Aerodynamics Analysis")
        self.setGeometry(300, 300, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QHBoxLayout(central_widget)

        self.splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.splitter)

    def create_control_panel(self, parent):

        control_widget = QWidget(parent)
        layout = QVBoxLayout(control_widget)

        weather_group = QGroupBox("Weather")
        weather_layout = QGridLayout(weather_group)

        weather_layout.addWidget(QLabel("City:"), 0, 0)
        self.city_combo = QComboBox()
        self.city_combo.setEditable(True)

        initial_cities = [
            "Delft", "Warsaw", "Berlin", "London", "Paris",
            "Madrid", "Rome", "Oslo", "New York", "Tokyo"
        ]
        self.city_combo.addItems(initial_cities)
        completer = QCompleter(initial_cities)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.city_combo.setCompleter(completer)
        self.city_combo.currentTextChanged.connect(self.on_city_changed)
        weather_layout.addWidget(self.city_combo, 0, 1)

        # Weather display widgets
        weather_layout.addWidget(QLabel("Temperature:"), 1, 0)
        self.temp_label = QLabel("--°C")
        weather_layout.addWidget(self.temp_label, 1, 1)

        weather_layout.addWidget(QLabel("Humidity:"), 2, 0)
        self.humidity_label = QLabel("--%")
        weather_layout.addWidget(self.humidity_label, 2, 1)

        weather_layout.addWidget(QLabel("Wind Speed:"), 3, 0)
        self.wind_speed_label = QLabel("-- m/s")
        weather_layout.addWidget(self.wind_speed_label, 3, 1)

        weather_layout.addWidget(QLabel("Wind Direction:"), 4, 0)
        self.wind_dir_label = QLabel("--°")
        weather_layout.addWidget(self.wind_dir_label, 4, 1)
        
        weather_layout.addWidget(QLabel("Last Update:"), 5, 0)
        self.last_update_label = QLabel("Never")
        weather_layout.addWidget(self.last_update_label, 5, 1)
        layout.addWidget(weather_group)


        # Flight parameters group
        flight_group = QGroupBox("Flight Parameters")
        flight_layout = QGridLayout(flight_group)

        # Wing configuration
        flight_layout.addWidget(QLabel("Wing Config:"), 0, 0)
        self.wing_combo = QComboBox()
        self.wing_combo.addItems(['15m', '18m'])
        self.wing_combo.currentTextChanged.connect(self.on_wing_changed)
        flight_layout.addWidget(self.wing_combo, 0, 1)

        # Airspeed
        flight_layout.addWidget(QLabel("Airspeed (m/s):"), 1, 0)
        self.airspeed_spin = QDoubleSpinBox()
        self.airspeed_spin.setRange(15, 78)  # Up to VNE (280 km/h = 77.8 m/s)
        self.airspeed_spin.setValue(25.0)
        self.airspeed_spin.setSingleStep(0.5)
        flight_layout.addWidget(self.airspeed_spin, 1, 1)

        # Altitude
        flight_layout.addWidget(QLabel("Altitude (m):"), 2, 0)
        self.altitude_spin = QDoubleSpinBox()
        self.altitude_spin.setRange(0, 8000)  # Practical glider ceiling
        self.altitude_spin.setValue(500)
        self.altitude_spin.setSingleStep(50)
        flight_layout.addWidget(self.altitude_spin, 2, 1)

        # Angle of attack
        flight_layout.addWidget(QLabel("AoA (deg):"), 3, 0)
        self.aoa_spin = QDoubleSpinBox()
        self.aoa_spin.setRange(-5, 15)
        self.aoa_spin.setValue(3.0)
        self.aoa_spin.setSingleStep(0.1)
        flight_layout.addWidget(self.aoa_spin, 3, 1)

        #Bank Angle
        flight_layout.addWidget(QLabel("Bank Angle (deg):"), 4, 0)
        self.bank_spin = QDoubleSpinBox()
        self.bank_spin.setRange(0, 60)
        self.bank_spin.setValue(0.0)
        flight_layout.addWidget(self.bank_spin, 4, 1)

        layout.addWidget(flight_group)



        # Aircraft config group
        sailplane_group = QGroupBox("Aircraft Configuration")
        sailplane_layout = QGridLayout(sailplane_group)

        # Mass
        sailplane_layout.addWidget(QLabel("Aircraft Mass (kg):"), 0, 0)
        self.mass_spin = QDoubleSpinBox()
        self.mass_spin.setRange(300, 565)
        self.mass_spin.setValue(330)
        sailplane_layout.addWidget(self.mass_spin, 0, 1)

        # Ballast
        sailplane_layout.addWidget(QLabel("Ballast (kg):"), 1, 0)
        self.ballast_spin = QDoubleSpinBox()
        self.ballast_spin.setRange(0, 100)
        self.ballast_spin.setValue(0)
        sailplane_layout.addWidget(self.ballast_spin, 1, 1)


        # Pilots and equipment weight
        sailplane_layout.addWidget(QLabel("Pilots and equipment weight (kg):"), 2, 0)
        self.additonal_weight_spin = QDoubleSpinBox()
        self.additonal_weight_spin.setRange(0, 130)
        self.additonal_weight_spin.setValue(70)
        sailplane_layout.addWidget(self.additonal_weight_spin, 2, 1)

        # Flap setting
        sailplane_layout.addWidget(QLabel("Flap Setting:"), 3, 0)
        self.flap_combo = QComboBox()
        self.flap_combo.addItems(['clean', '+1', '+2', 'L', 'S'])
        sailplane_layout.addWidget(self.flap_combo, 3, 1)

        layout.addWidget(sailplane_group)

        parent.addWidget(control_widget)

    def create_visualization_panel(self, parent):
        viz_widget = QWidget(parent)
        viz_layout = QVBoxLayout(viz_widget)

        self.tabs = QTabWidget()

        # 1. CL vs AoA tab
        cl_tab = QWidget()
        cl_layout = QVBoxLayout(cl_tab)
        self.cl_plot = create_plot_canvas('cl_aoa', cl_tab)
        cl_layout.addWidget(self.cl_plot)
        self.tabs.addTab(cl_tab, "CL vs AoA")

        # 2. Speed Polar tab
        ld_tab = QWidget()
        ld_layout = QVBoxLayout(ld_tab)
        self.ld_plot = create_plot_canvas('speed_polar', ld_tab)
        ld_layout.addWidget(self.ld_plot)
        self.tabs.addTab(ld_tab, "Speed Polar")

        # 3. Polar CD vs CL tab with flap slider
        polar_tab = QWidget()
        polar_layout = QVBoxLayout(polar_tab)

        # Flap slider controls
        self.flap_options = ['clean', '+1', '+2', 'L', 'S']
        self.polar_flap_slider = QSlider(Qt.Horizontal)
        self.polar_flap_slider.setMinimum(0)
        self.polar_flap_slider.setMaximum(len(self.flap_options) - 1)
        self.polar_flap_slider.setTickInterval(1)
        self.polar_flap_slider.setTickPosition(QSlider.TicksBelow)
        self.polar_flap_slider.setValue(0)

        self.polar_flap_label = QLabel(f"Flaps: {self.flap_options[0]}")

        slider_row = QHBoxLayout()
        slider_row.addWidget(QLabel("Flaps"))
        slider_row.addWidget(self.polar_flap_slider)
        slider_row.addWidget(self.polar_flap_label)

        polar_layout.addLayout(slider_row)

        self.polar_plot = create_plot_canvas('polar', polar_tab)
        polar_layout.addWidget(self.polar_plot)
        self.tabs.addTab(polar_tab, "Polar")

        # 4. Performance Summary tab
        perf_tab = QWidget()
        perf_layout = QVBoxLayout(perf_tab)
        self.summary_plot = create_plot_canvas('summary', perf_tab)
        perf_layout.addWidget(self.summary_plot)
        self.tabs.addTab(perf_tab, "Performance Summary")

        viz_layout.addWidget(self.tabs)
        parent.addWidget(viz_widget)

    def connect_signals(self):
        """Connect all GUI signals to update methods"""
        # Wing configuration
        self.wing_combo.currentTextChanged.connect(self.on_wing_changed)

        # Flight parameters
        self.airspeed_spin.valueChanged.connect(self.on_parameters_changed)
        self.altitude_spin.valueChanged.connect(self.on_parameters_changed)
        self.aoa_spin.valueChanged.connect(self.on_parameters_changed)
        self.bank_spin.valueChanged.connect(self.on_parameters_changed)

        # Aircraft configuration
        self.mass_spin.valueChanged.connect(self.on_parameters_changed)
        self.ballast_spin.valueChanged.connect(self.on_parameters_changed)
        self.additonal_weight_spin.valueChanged.connect(self.on_parameters_changed)
        self.flap_combo.currentTextChanged.connect(self.on_parameters_changed)

        # Polar tab flap slider
        self.polar_flap_slider.valueChanged.connect(self.on_polar_flap_slider_changed)

    def on_parameters_changed(self):
        """Handle parameter changes with debouncing"""
        self.update_timer.start(250)  # 250ms debounce to avoid UI jank

    def on_wing_changed(self):
        """Handle wing configuration change"""
        wing_config = self.wing_combo.currentText()
        self.current_aircraft = self.aircraft_configs[wing_config]
        self.update_aircraft_config()
        self.on_parameters_changed()

    def on_polar_flap_slider_changed(self, value: int):
        """Map slider index to flap setting and update global flap combo"""
        if 0 <= value < len(self.flap_options):
            self.polar_flap_label.setText(f"Flaps: {self.flap_options[value]}")
            # This triggers on_parameters_changed via signal
            self.flap_combo.setCurrentIndex(value)

    def update_aircraft_config(self):
        """Update aircraft with current GUI values"""
        self.current_aircraft.mass_kg = self.mass_spin.value()
        self.current_aircraft.ballast_kg = self.ballast_spin.value()
        self.current_aircraft.pilot_and_eq = self.additonal_weight_spin.value()

        # Recreate models
        self.lift_model = LiftModel(self.current_aircraft)
        self.performance = PerformanceCalculator(self.current_aircraft, self.lift_model)

    def get_current_parameters(self):
        """Get current parameters from GUI"""
        weather_data = self.get_weather_data()
        return {
            'airspeed': self.airspeed_spin.value(),
            'altitude': self.altitude_spin.value(),
            'aoa': self.aoa_spin.value(),
            'bank_angle': self.bank_spin.value(),
            'flap_setting': self.flap_combo.currentText(),
            'wing_config': self.wing_combo.currentText(),
            'surface_temp': weather_data['temperature_k'],
            'relative_humidity': weather_data['humidity_percent'],
            'city': self.city_combo.currentText(),
            'weather': weather_data
        }

    def update_plots(self):
        """Plot update method (non-async for simplicity and stability)"""
        try:
            # Update aircraft config first
            self.update_aircraft_config()

            # Get current parameters
            params = self.get_current_parameters()

            # Update plots
            self.cl_plot.update_plot(self.lift_model, self.performance, params)
            self.ld_plot.update_plot(self.lift_model, self.performance, params)
            self.polar_plot.update_plot(self.lift_model, self.performance, params)
            self.summary_plot.update_plot(self.lift_model, self.performance, params)

        except Exception as e:
            print(f"Plot update error: {e}")
    
    def on_city_changed(self):
        """Handle city change - update weather immediately"""
        current_city = self.city_combo.currentText()
        if current_city and current_city != self.last_weather_city:
            self.update_weather_data()
    
    def initial_weather_update(self):
        """Initial weather update on startup"""
        self.update_weather_data()
    
    def update_weather_data(self):
        """Update weather data from API"""
        try:
            city = self.city_combo.currentText()
            if not city:
                return
            
            # Get weather data
            weather = Weather(city)
            self.current_weather = weather
            self.last_weather_city = city
            
            # Update GUI labels
            temp_celsius = weather.temperature() - 273.15  # Convert from Kelvin
            self.temp_label.setText(f"{temp_celsius:.1f}°C")
            self.humidity_label.setText(f"{weather.humidity()}%")
            self.wind_speed_label.setText(f"{weather.wind_speed():.1f} m/s")
            self.wind_dir_label.setText(f"{weather.wind_direction():.0f}°")
            
            # Update timestamp
            from datetime import datetime
            now = datetime.now()
            self.last_update_label.setText(now.strftime("%H:%M:%S"))
            self.update_plots()
            print(f"Weather updated for {city}: {temp_celsius:.1f}°C, {weather.humidity()}%, {weather.wind_speed():.1f}m/s")
            
        except Exception as e:
            print(f"Weather update error: {e}")
            # Set default values on error
            self.temp_label.setText("15.0°C")
            self.humidity_label.setText("60%")
            self.wind_speed_label.setText("0.0 m/s")
            self.wind_dir_label.setText("0°")
            self.last_update_label.setText("Error")
    
    def get_weather_data(self):
        """Get current weather data for use by models"""
        if self.current_weather is None:
            # Return default values if no weather data
            return {
                'temperature_k': 288.15,  # 15°C
                'humidity_percent': 60.0,
                'wind_speed_mps': 0.0,
                'wind_direction_deg': 0.0,
                'pressure_hpa': 1013.25
            }
        
        try:
            return {
                'temperature_k': self.current_weather.temperature(),
                'humidity_percent': self.current_weather.humidity(),
                'wind_speed_mps': self.current_weather.wind_speed(),
                'wind_direction_deg': self.current_weather.wind_direction(),
                'pressure_hpa': self.current_weather.pressure()
            }
        except:
            # Fallback to defaults
            return {
                'temperature_k': 288.15,
                'humidity_percent': 60.0,
                'wind_speed_mps': 0.0,
                'wind_direction_deg': 0.0,
                'pressure_hpa': 1013.25
            }


def init_gui():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app, window


if __name__ == "__main__":
    app, window = init_gui()
    app.exec()

