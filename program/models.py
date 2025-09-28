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
    def air_density(altitude_m: float, surface_temp: float, relative_humidity: float, sea_level_pressure: float = 101325.0) -> float:
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

        # Troposphere approximation (below 11 km)
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
                 cd0: float = 0.0059, k: float = 0.023):
        """
        Args:
            aircraft: instance of the Aircraft class (should include mass and wing params)
            cl0: lift coefficient at zero AoA
            a0_per_rad: theoretical slope of the CL curve for a thin airfoil (~2π/rad)
            e: wing efficiency factor (1 = ideal, typical glider 0.7–0.9)
            cd0: zero-lift drag coefficient (profile drag)
            k: induced drag factor
        """
        self.aircraft = aircraft
        self.cl0 = cl0
        self.a0 = a0_per_rad
        self.e = e
        self.cd0 = cd0
        self.k = k

    def finite_wing_lift_slope(self) -> float:
        """
        Computes the lift curve slope for a finite wing, including tip effects.
        """
        AR = self.aircraft.wing.aspect_ratio
        return self.a0 / (1.0 + self.a0 / (math.pi * AR * self.e))

    def flap_correction(self, flap_setting: str) -> tuple[float, float]:
        """
        Returns (ΔCL, ΔCD) corrections for different flap settings.
        Values are approximate, based on typical sailplane tables.
        """
        flap_corrections = {
            'clean': (0.0, 0.0),
            '+1': (0.12, 0.0025),
            '+2': (0.25, 0.008),
            'L': (0.4, 0.025),
            'S': (-0.05, 0.003)
        }
        return flap_corrections.get(flap_setting, (0.0, 0.0))

    #cl after claps change
    def cl_from_aoa(self, aoa_deg: float, flap_setting: str = 'clean') -> float:
        delta_cl, _ = self.flap_correction(flap_setting)
        base_cl = self.cl0 + self.finite_wing_lift_slope() * math.radians(aoa_deg)
        return base_cl + delta_cl
    #cd after claps change
    def cd_from_cl(self, cl: float, flap_setting: str = 'clean') -> float:
        _, delta_cd = self.flap_correction(flap_setting)
        return self.cd0 + self.k * cl ** 2 + delta_cd



    def lift_required_for_level_flight(self, bank_angle_deg: float = 0.0) -> float:
        weight = self.aircraft.total_mass * Atmosphere.GRAVITY
        load_factor = 1.0 / math.cos(math.radians(bank_angle_deg))
        return weight * load_factor



    def lift(self, true_airspeed: float, altitude: float, aoa_deg: float,
             surface_temp: float = 288.15, relative_humidity: float = 50.0,
             flap_setting: str = 'clean', bank_angle_deg: float = 0.0) -> float:
        rho = Atmosphere.air_density(altitude, surface_temp, relative_humidity)
        CL = self.cl_from_aoa(aoa_deg, flap_setting)
        wing_area = self.aircraft.wing.area_m2
        return 0.5 * rho * true_airspeed ** 2 * wing_area * CL

    def drag(self, true_airspeed: float, altitude: float, aoa_deg: float,
             surface_temp: float = 288.15, relative_humidity: float = 50.0,
             flap_setting: str = 'clean') -> float:
        rho = Atmosphere.air_density(altitude, surface_temp, relative_humidity)
        CL = self.cl_from_aoa(aoa_deg, flap_setting)
        CD = self.cd_from_cl(CL, flap_setting)
        wing_area = self.aircraft.wing.area_m2
        return 0.5 * rho * true_airspeed ** 2 * wing_area * CD

    def lift_to_drag_ratio(self, aoa_deg: float, flap_setting: str = 'clean') -> float:
        CL = self.cl_from_aoa(aoa_deg, flap_setting)
        CD = self.cd_from_cl(CL, flap_setting)
        return CL / CD if CD > 0 else 0.0



if __name__ == "__main__":
    # Basic test of the models
    aircraft = Aircraft()
    model = LiftModel(aircraft)

    print(f"\n=== Basic Model Test ===")
    print(f"Aircraft: {aircraft.model}")
    print(f"Wing: {aircraft.wing.span_m}m span, {aircraft.wing.area_m2:.2f} m²")
    print(f"Total mass: {aircraft.total_mass} kg")
    print(f"Weight: {aircraft.total_mass * Atmosphere.GRAVITY:.0f} N")
    
    # Test basic lift and drag calculations
    airspeed = 40.0  # m/s
    altitude = 1000.0  # m
    aoa = 4.0  # degrees
    
    lift = model.lift(airspeed, altitude, aoa)
    drag = model.drag(airspeed, altitude, aoa)
    ld_ratio = model.lift_to_drag_ratio(aoa)
    
    print(f"\nAt {airspeed} m/s, {altitude}m altitude, AoA={aoa}°:")
    print(f"Lift: {lift:.0f} N")
    print(f"Drag: {drag:.0f} N")
    print(f"L/D ratio: {ld_ratio:.1f}")
    
    # Test flap effects
    print(f"\n=== Flap Effects Test ===")
    for flap in ['clean', '+1', '+2', 'L', 'S']:
        cl = model.cl_from_aoa(aoa, flap)
        cd = model.cd_from_cl(cl, flap)
        ld = cl / cd if cd > 0 else 0
        print(f"Flap {flap:>5}: CL={cl:.3f}, CD={cd:.4f}, L/D={ld:.1f}")


