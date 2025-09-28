import math
from typing import Dict, List, Tuple, Optional
from models import Aircraft, LiftModel, Atmosphere


class PerformanceCalculator:
    """
    Advanced performance calculations for glider analysis.
    Uses basic models from models.py to perform comprehensive performance analysis.
    """
    
    def __init__(self, aircraft: Aircraft, lift_model: LiftModel):
        self.aircraft = aircraft
        self.lift_model = lift_model

    def find_best_glide_ratio(self, flap_setting: str = 'clean',
                              aoa_range: tuple = (-2, 12), step: float = 0.1,
                              altitude: float = 1000.0,
                              surface_temp: float = 288.15,
                              relative_humidity: float = 50.0,
                              bank_angle_deg: float = 0.0) -> tuple[float, float, float]:
        """
        Find optimal AoA for best L/D, accounting for mass, altitude, atmosphere, bank.
        Returns: (best_aoa, best_LD_ratio, CL_at_best)
        """
        best_ld = 0.0
        best_aoa = 0.0
        best_cl = 0.0

        rho = Atmosphere.air_density(altitude, surface_temp, relative_humidity)
        wing_area = self.aircraft.wing.area_m2
        lift_required = self.lift_model.lift_required_for_level_flight(bank_angle_deg=bank_angle_deg)

        aoa = aoa_range[0]
        while aoa <= aoa_range[1]:
            CL = self.lift_model.cl_from_aoa(aoa, flap_setting)
            if CL > 0:
                # prędkość wymagana do utrzymania poziomego lotu przy tym CL
                V = math.sqrt(2 * lift_required / (rho * wing_area * CL))
                # obliczamy faktyczny L/D przy tej prędkości
                CD = self.lift_model.cd_from_cl(CL, flap_setting)
                drag = 0.5 * rho * V ** 2 * wing_area * CD
                ld_ratio = lift_required / drag
            else:
                ld_ratio = 0.0

            if ld_ratio > best_ld:
                best_ld = ld_ratio
                best_aoa = aoa
                best_cl = CL

            aoa += step

        return best_aoa, best_ld, best_cl

    def best_glide_speed(self, altitude: float = 0, flap_setting: str = 'clean',
                        surface_temp: float = 288.15, relative_humidity: float = 50.0) -> Tuple[float, float]:
        """
        Calculate optimal glide speed (best L/D).
        
        Args:
            altitude (float): flight altitude [m]
            flap_setting (str): flap configuration
            surface_temp (float): surface temperature [K]
            relative_humidity (float): relative humidity [%]
            
        Returns:
            tuple: (optimal_speed_ms, best_LD_ratio)
        """
        best_aoa, best_ld, best_cl = self.find_best_glide_ratio(flap_setting)
        
        # Calculate air density
        rho = Atmosphere.air_density(altitude, surface_temp, relative_humidity)
        
        # Calculate speed for given CL: V = sqrt(2*W/(rho*S*CL))
        weight = self.aircraft.total_mass * Atmosphere.GRAVITY
        wing_area = self.aircraft.wing.area_m2
        optimal_speed = math.sqrt(2 * weight / (rho * wing_area * best_cl))
        
        return optimal_speed, best_ld
    
    def speed_to_fly(self, sink_rate_air_mass: float, altitude: float = 0, 
                    surface_temp: float = 288.15, relative_humidity: float = 50.0) -> float:
        """
        Calculate speed to fly in given air mass (MacCready theory).
        
        Args:
            sink_rate_air_mass (float): air mass sink rate [m/s] (+ sinking, - rising)
            altitude (float): altitude [m]
            surface_temp, relative_humidity: atmospheric conditions
            
        Returns:
            float: speed to fly [m/s]
        """
        # Find optimal glide speed
        optimal_speed, best_ld = self.best_glide_speed(altitude, 'clean', surface_temp, relative_humidity)
        
        # MacCready speed-to-fly (simplified version)
        if sink_rate_air_mass <= 0:  # Rising or neutral
            return optimal_speed * 0.9  # Fly slower
        else:  # Sinking
            speed_factor = 1.0 + (sink_rate_air_mass / 2.0)  # Increase speed when sinking
            return optimal_speed * min(speed_factor, 1.5)  # Max 1.5x optimal
    
    def performance_at_speed(self, speed_ms: float, altitude: float = 0, 
                           flap_setting: str = 'clean', surface_temp: float = 288.15, 
                           relative_humidity: float = 50.0, bank_angle_deg: float = 0.0) -> Dict[str, float]:
        """
        Calculate performance parameters at given speed.
        
        Returns:
            Dict containing: aoa, lift, drag, ld_ratio, sink_rate, cl, cd
        """
        # Calculate required CL for level flight (with bank angle)
        rho = Atmosphere.air_density(altitude, surface_temp, relative_humidity)
        weight = self.aircraft.total_mass * Atmosphere.GRAVITY
        wing_area = self.aircraft.wing.area_m2
        
        # Account for bank angle (load factor)
        load_factor = 1.0 / math.cos(math.radians(bank_angle_deg)) if bank_angle_deg > 0 else 1.0
        required_lift = weight * load_factor
        required_cl = required_lift / (0.5 * rho * speed_ms**2 * wing_area)
        
        # Find AoA for this CL (approximation)
        required_aoa = None
        for test_aoa in range(-5, 20):
            if abs(self.lift_model.cl_from_aoa(test_aoa, flap_setting) - required_cl) < 0.01:
                required_aoa = test_aoa
                break
        
        if required_aoa is None:
            return {}
        
        # Calculate parameters
        lift = self.lift_model.lift(speed_ms, altitude, required_aoa, surface_temp, relative_humidity, flap_setting)
        drag = self.lift_model.drag(speed_ms, altitude, required_aoa, surface_temp, relative_humidity, flap_setting)
        ld_ratio = self.lift_model.lift_to_drag_ratio(required_aoa, flap_setting)
        sink_rate = speed_ms / ld_ratio if ld_ratio > 0 else float('inf')
        cl = self.lift_model.cl_from_aoa(required_aoa, flap_setting)
        cd = self.lift_model.cd_from_cl(cl, flap_setting)
        
        return {
            'aoa': required_aoa,
            'lift': lift,
            'drag': drag,
            'ld_ratio': ld_ratio,
            'sink_rate': sink_rate,
            'cl': cl,
            'cd': cd,
            'speed_ms': speed_ms,
            'speed_kmh': speed_ms * 3.6
        }


