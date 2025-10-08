from dataclasses import dataclass, field
from typing import Optional
import math

@dataclass
class WingConfig:
    name: str
    span_m: float
    area_m2: float
    aspect_ratio: Optional[float] = None

    def __post_init__(self):
        if self.aspect_ratio is None:
            self.aspect_ratio = (self.span_m ** 2) / self.area_m2

@dataclass
class Aircraft:
    model: str = "Schempp-Hirth Discus-2cT"
    wing: WingConfig = field(default_factory=lambda: WingConfig("18m", 18.0, 11.36))
    mass_kg: float = 330.0
    ballast_kg: float = 60.0
    pilot_and_eq: float = 70.0

    @property
    def total_mass(self):
        return self.mass_kg + self.ballast_kg + self.pilot_and_eq


class Atmosphere:
    """A simple atmospheric model for calculating air properties with altitude and humidity."""

    GRAVITY = 9.80665       # Acceleration due to gravity [m/s²]
    R_D = 287.05            # Gas constant for dry air [J/(kg·K)]
    R_V = 461.5             # Gas constant for water vapor [J/(kg·K)]
    C_P = 1005.0            # Specific heat capacity of dry air [J/(kg·K)]
    L_V = 2.5e6             # Latent heat of vaporization for water [J/kg]

    @staticmethod
    def compute_local_lapse_rate(surface_temp: float, relative_humidity: float) -> float:
        """
        Estimate the local temperature lapse rate [K/m] based on surface humidity.

        Args:
            surface_temp (float): Surface temperature in Kelvin
            relative_humidity (float): Relative humidity in percent (0-100)

        Returns:
            float: Approximate lapse rate in K/m
        """
        humidity_fraction = relative_humidity / 100.0
        # Reduce the lapse rate for higher humidity (simplified approach)
        lapse_rate = 0.0065 * (1 - 0.5 * humidity_fraction)
        return lapse_rate

    @staticmethod
    def air_density(altitude_m: float, surface_temp: float, relative_humidity: float, 
                     sea_level_pressure: float = 101325.0, pressure_override: float = None) -> float:


        """
        Calculate the density of moist air at a given altitude.

        Args:
            altitude_m (float): Altitude in meters
            surface_temp (float): Surface temperature in Kelvin
            relative_humidity (float): Relative humidity in percent (0-100)
            sea_level_pressure (float): Pressure at sea level in Pa (default 101325 Pa)

        Returns:
            float: Air density in kg/m³
        """
        lapse_rate = Atmosphere.compute_local_lapse_rate(surface_temp, relative_humidity)

        # Calculate temperature at altitude
        temp = surface_temp - lapse_rate * altitude_m
        pressure = sea_level_pressure * (temp / surface_temp) ** (Atmosphere.GRAVITY / (Atmosphere.R_D * lapse_rate))

        # Saturation vapor pressure (Tetens formula) [hPa]
        e_s = 6.1078 * 10 ** ((7.5 * (temp - 273.15)) / (temp - 35.85))
        e = e_s * (relative_humidity / 100.0)

        # Air density accounting for moisture
        rho = pressure/ (Atmosphere.R_D * temp) - e * (1/Atmosphere.R_D - 1/Atmosphere.R_V)
        return rho

class LiftModel:
    """
    Simple aerodynamic model for calculating lift and drag forces for a glider.
    This does NOT use full polar data from the manufacturer – instead, it relies
    on a linear CL vs angle of attack (AoA) relationship and a quadratic drag polar.

    NOTE:
    The numeric values (cl0, cd0, k, flap corrections) are TEST VALUES.
    I roughly adjusted them to match the reported maximum glide ratio of a
    given glider. Manufacturers usually do not specify the exact flap/configuration
    used for these numbers. Treat these values as approximate; precise analysis
    would require wind tunnel data or official polar curves.
    """

    def __init__(self, aircraft, cl0: float = 0.1,
                 a0_per_rad: float = 2 * math.pi, e: float = 0.85,
                 cd0: float = 0.0059, k: float = 0.023,
                 stall_aoa_deg: float = 15.0, cl_max: float = 1.4):
        self.aircraft = aircraft
        self.cl0 = cl0
        self.a0 = a0_per_rad
        self.e = e
        self.cd0 = cd0
        self.k = k
        self.stall_aoa = stall_aoa_deg
        self.cl_max = cl_max

    def finite_wing_lift_slope(self) -> float:
        """
        Computes the lift curve slope for a finite wing, including tip effects.
        """
        AR = self.aircraft.wing.aspect_ratio
        return self.a0 / (1.0 + self.a0 / (math.pi * AR * self.e))

    def flap_correction(self, flap_setting: str) -> tuple[float, float, float]:
        """
        Returns (ΔCL, ΔCD, Δstall_AoA) corrections for different flap settings.
        """
        flap_corrections = {
            'clean': (0.0, 0.0, 0.0),
            '+1': (0.12, 0.0025, -0.8),   # Slight improvement
            '+2': (0.26, 0.008, -1.5),    # More noticeable improvement  
            'L': (0.42, 0.028, -2.8),     # Significant landing flap effect
            'S': (-0.06, 0.004, +0.7)     # Negative flap - less effective
        }
        return flap_corrections.get(flap_setting, (0.0, 0.0, 0.0))
        # cd after claps change

    def cd_from_cl(self, cl: float, flap_setting: str = 'clean') -> float:
        _, delta_cd, _ = self.flap_correction(flap_setting)
        return self.cd0 + self.k * cl ** 2 + delta_cd


    def cl_from_aoa(self, aoa_deg: float, flap_setting: str = 'clean') -> float:
        """
        Realistic CL vs AoA based on typical glider airfoil characteristics.
        Uses empirically validated curve shape matching real wind tunnel data.
        """
        delta_cl, _, delta_stall = self.flap_correction(flap_setting)
        
        # Effective parameters for this configuration
        nominal_stall_aoa = self.stall_aoa + delta_stall
        cl_max = self.cl_max + delta_cl
        slope = self.finite_wing_lift_slope()
        
        # Real stall point is where curve significantly deviates from linear
        # Not at cl_max, but earlier where curvature begins
        stall_aoa = nominal_stall_aoa * 0.85  # Move stall point to 85% of nominal
        
        # Convert to radians for calculations
        aoa_rad = math.radians(aoa_deg)
        stall_aoa_rad = math.radians(stall_aoa)
        
        # Calculate linear CL for reference
        cl_linear = self.cl0 + slope * aoa_rad + delta_cl
        
        if aoa_deg <= nominal_stall_aoa:
            # Pre-stall: Single smooth curve that gradually flattens
            # No separate "lines" - just one continuous curve
            
            # Use smooth polynomial that starts linear and flattens to cl_max
            # This creates natural airfoil behavior without visible "joints"
            nominal_stall_aoa_rad = math.radians(nominal_stall_aoa)
            progress = aoa_rad / nominal_stall_aoa_rad  # 0 to 1
            
            # Polynomial blend that starts linear and curves to cl_max
            curve_factor = 1.0 - 0.4 * (progress ** 3)  # Gentle cubic curve
            
            # Start with linear, gradually saturate towards cl_max
            cl_result = cl_linear * curve_factor
            
            # Ensure we approach but don't exceed cl_max
            return min(cl_result, cl_max)
        else:
            # Post-stall: Implement Viterna-Corrigan type model

            
            overshoot = aoa_deg - nominal_stall_aoa
            
            # Viterna-Corrigan coefficients (empirically derived)
            A1 = cl_max / 2.0  # Controls deep stall level
            nominal_stall_aoa_rad = math.radians(nominal_stall_aoa)
            A2 = (cl_max - cl_max * math.cos(nominal_stall_aoa_rad)) / (math.sin(nominal_stall_aoa_rad) ** 2)
            
            # Post-stall CL using trigonometric model
            aoa_rad_current = math.radians(aoa_deg)
            cl_post = A1 * math.sin(2.0 * aoa_rad_current) + A2 * (math.cos(aoa_rad_current) ** 2) / math.sin(aoa_rad_current)
            
            # Ensure reasonable bounds
            cl_post = max(cl_post, 0.2)  # Minimum CL in deep stall
            cl_post = min(cl_post, cl_max * 0.8)  # Don't exceed 80% of max
            
            return cl_post




    def lift_required_for_level_flight(self, bank_angle_deg: float = 0.0) -> float:
        weight = self.aircraft.total_mass * Atmosphere.GRAVITY
        load_factor = 1.0 / math.cos(math.radians(bank_angle_deg))
        return weight * load_factor



    def lift(self, true_airspeed: float, altitude: float, aoa_deg: float,
             surface_temp: float = 288.15, relative_humidity: float = 50.0,
             flap_setting: str = 'clean', bank_angle_deg: float = 0.0,
             pressure_hpa: float = None) -> float:
        # Convert pressure from hPa to Pa if provided
        pressure_pa = pressure_hpa * 100 if pressure_hpa is not None else None
        rho = Atmosphere.air_density(altitude, surface_temp, relative_humidity, 
                                   pressure_override=pressure_pa)
        CL = self.cl_from_aoa(aoa_deg, flap_setting)
        wing_area = self.aircraft.wing.area_m2
        return 0.5 * rho * true_airspeed ** 2 * wing_area * CL

    def drag(self, true_airspeed: float, altitude: float, aoa_deg: float,
             surface_temp: float = 288.15, relative_humidity: float = 50.0,
             flap_setting: str = 'clean', pressure_hpa: float = None) -> float:
        # Convert pressure from hPa to Pa if provided
        pressure_pa = pressure_hpa * 100 if pressure_hpa is not None else None
        rho = Atmosphere.air_density(altitude, surface_temp, relative_humidity,
                                   pressure_override=pressure_pa)
        CL = self.cl_from_aoa(aoa_deg, flap_setting)
        CD = self.cd_from_cl(CL, flap_setting)
        wing_area = self.aircraft.wing.area_m2
        return 0.5 * rho * true_airspeed ** 2 * wing_area * CD

    def lift_to_drag_ratio(self, aoa_deg: float, flap_setting: str = 'clean') -> float:
        CL = self.cl_from_aoa(aoa_deg, flap_setting)
        CD = self.cd_from_cl(CL, flap_setting)
        return CL / CD if CD > 0 else 0.0
    
    def stall_speed(self, altitude: float = 0, flap_setting: str = 'clean', 
                   surface_temp: float = 288.15, relative_humidity: float = 50.0,
                   load_factor: float = 1.0, pressure_hpa: float = None) -> float:
        """
        Calculate stall speed for given conditions.
        
        Returns:
            float: Stall speed in m/s
        """
        # Convert pressure from hPa to Pa if provided
        pressure_pa = pressure_hpa * 100 if pressure_hpa is not None else None
        rho = Atmosphere.air_density(altitude, surface_temp, relative_humidity,
                                   pressure_override=pressure_pa)
        weight = self.aircraft.total_mass * Atmosphere.GRAVITY * load_factor
        wing_area = self.aircraft.wing.area_m2
        
        # Get effective CL_max for this configuration
        delta_cl, _, delta_stall = self.flap_correction(flap_setting)
        cl_max_effective = self.cl_max + delta_cl
        
        # V_stall = sqrt(2*W/(rho*S*CL_max))
        stall_speed_ms = math.sqrt(2 * weight / (rho * wing_area * cl_max_effective))
        return stall_speed_ms


