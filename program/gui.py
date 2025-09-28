from PySide6.QtWidgets import (QWidget, QApplication, QMainWindow, QPushButton,
                               QHBoxLayout, QVBoxLayout, QGroupBox, QGridLayout,
                               QLabel, QComboBox, QDoubleSpinBox, QSplitter, QTabWidget,
                               QSlider)
from PySide6.QtCore import Qt, QTimer
import sys
from models import Aircraft, LiftModel, WingConfig
from performance import PerformanceCalculator
from plots import create_plot_canvas


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

        # Initial plot update after the event loop starts
        QTimer.singleShot(0, self.update_plots)


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
        return {
            'airspeed': self.airspeed_spin.value(),
            'altitude': self.altitude_spin.value(),
            'aoa': self.aoa_spin.value(),
            'bank_angle': self.bank_spin.value(),
            'flap_setting': self.flap_combo.currentText(),
            'wing_config': self.wing_combo.currentText(),
            'surface_temp': 288.15,
            'relative_humidity': 50.0
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


def init_gui():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app, window


if __name__ == "__main__":
    app, window = init_gui()
    app.exec()

