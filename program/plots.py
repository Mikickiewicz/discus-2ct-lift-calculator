import seaborn as sns
import numpy as np
import pandas as pd
import math
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.style as mplstyle

# Set seaborn style
sns.set_style("whitegrid")
sns.set_palette("husl")
mplstyle.use('fast')

class InteractivePlotCanvas(FigureCanvas):
    """Base class for interactive matplotlib plots"""

    def __init__(self, parent=None, width=8, height=6, dpi=100):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.figure)
        self.setParent(parent)

        # Enable navigation
        self.figure.canvas.toolbar_visible = True

    def clear_plot(self):
        self.figure.clear()
        self.draw()


class CLvsAoAPlot(InteractivePlotCanvas):
    """CL vs Angle of Attack plot showing stall characteristics"""

    def update_plot(self, models, performance, params):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Get stall AoA from model - use same logic as in cl_from_aoa
        _, _, delta_stall = models.flap_correction(params['flap_setting'])
        nominal_stall_aoa = models.stall_aoa + delta_stall
        stall_aoa = nominal_stall_aoa * 0.85  # Same as in model

        # Calculate reasonable AoA range - don't compute beyond useful range
        max_aoa_calc = nominal_stall_aoa + 0  # Calculate up to 3° past nominal stall
        aoa_range = np.linspace(-5, max_aoa_calc, 100)
        cl_data = [models.cl_from_aoa(aoa, params['flap_setting']) for aoa in aoa_range]

        # Plot with seaborn
        df = pd.DataFrame({'AoA': aoa_range, 'CL': cl_data})
        sns.lineplot(data=df, x='AoA', y='CL', ax=ax, linewidth=2.5, color='blue')
        
        # Find actual maximum CL from the plotted data
        max_cl_idx = np.argmax(cl_data)
        actual_stall_aoa = aoa_range[max_cl_idx]

        # Mark stall AoA and show stall speed
        bank_angle = params.get('bank_angle', 0.0)
        load_factor = 1.0 / math.cos(math.radians(bank_angle)) if bank_angle > 0 else 1.0
        weather_data = params.get('weather', {})
        stall_speed_ms = models.stall_speed(
            params.get('altitude', 0), params['flap_setting'],
            params.get('surface_temp', 288.15), params.get('relative_humidity', 50.0),
            load_factor, pressure_hpa=weather_data.get('pressure_hpa')
        )
        stall_speed_kmh = stall_speed_ms * 3.6
        
        ax.axvline(x=actual_stall_aoa, color='orange', linestyle='--', alpha=0.7, 
                  label=f'Stall AoA: {actual_stall_aoa:.1f}° (V_s: {stall_speed_kmh:.0f} km/h)')

        # Current point - use model directly (no duplicate logic)
        current_cl = models.cl_from_aoa(params['aoa'], params['flap_setting'])

        ax.scatter(params['aoa'], current_cl, color='red', s=120, zorder=5,
                  edgecolor='white', linewidth=2, label='Current State')

        # Best L/D point
        weather_data = params.get('weather', {})
        best_aoa, _, _ = performance.find_best_glide_ratio(
            params['flap_setting'], pressure_hpa=weather_data.get('pressure_hpa'))
        best_cl = models.cl_from_aoa(best_aoa, params['flap_setting'])
        ax.scatter(best_aoa, best_cl, color='green', s=120, zorder=5,
                  marker='*', edgecolor='white', linewidth=2, label='Best L/D')

        ax.set_xlabel('Angle of Attack [°]')
        ax.set_ylabel('Lift Coefficient CL')
        ax.set_title(f'CL vs AoA - {params["flap_setting"]} flaps')
        ax.grid(True, alpha=0.3)
        ax.legend()
        # Limit x-axis to reasonable range - cut off after deep stall
        max_aoa_display = min(20, nominal_stall_aoa + 3)  # Show max 3° past nominal stall
        ax.set_xlim(-5, max_aoa_display)

        self.figure.tight_layout()
        self.draw()


class SpeedPolarPlot(InteractivePlotCanvas):
    """Speed Polar: Sink Rate vs Speed (classic glider polar)"""

    def update_plot(self, models, performance, params):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Generate speed range based on aircraft characteristics
        # Lower speeds for heavier aircraft (higher stall speed)
        weight = models.aircraft.total_mass * 9.80665
        wing_area = models.aircraft.wing.area_m2
        wing_loading = weight / wing_area
        
        # Bank angle affects performance
        bank_angle = params.get('bank_angle', 0.0)
        load_factor = 1.0 / math.cos(math.radians(bank_angle)) if bank_angle > 0 else 1.0
        
        # Get proper air density first
        altitude = min(params.get('altitude', 0), 8000)  # Cap at practical ceiling
        surface_temp = params.get('surface_temp', 288.15)
        relative_humidity = params.get('relative_humidity', 50.0)
        weather_data = params.get('weather', {})
        from models import Atmosphere
        pressure_pa = weather_data.get('pressure_hpa') * 100 if weather_data.get('pressure_hpa') else None
        rho = Atmosphere.air_density(altitude, surface_temp, relative_humidity, 
                                   pressure_override=pressure_pa)
        
        # Dynamic speed range based on wing loading and aircraft limits
        # Stall speed calculation (more accurate)
        cl_max = 1.4  # Typical max CL for gliders
        stall_speed_ms = math.sqrt(2 * weight * load_factor / (rho * wing_area * cl_max))
        min_speed = stall_speed_ms * 1.2  # 20% above stall for safety
        
        # VNE for Discus-2cT is 280 km/h = 77.8 m/s
        vne_ms = 280 / 3.6  # Convert km/h to m/s
        max_speed = min(vne_ms * 0.95, 75)  # 95% of VNE for safety
        
        # Ensure reasonable range
        if max_speed <= min_speed:
            max_speed = min_speed + 30
        
        speeds_ms = np.linspace(min_speed, max_speed, 120)  # More points for smoother curve
        speeds_kmh = speeds_ms * 3.6
        sink_rates = []

        for speed in speeds_ms:
            # More accurate polar calculation using actual aerodynamics
            try:
                # Calculate required CL for this speed (rho already calculated above)
                cl_required = weight * load_factor / (0.5 * rho * speed**2 * wing_area)
                
                # Realistic CL range check - more restrictive
                if cl_required > 0.1 and cl_required < 1.6 and rho > 0.2:  # Sanity checks
                    cd = models.cd_from_cl(cl_required, params['flap_setting'])
                    if cd > 0.005 and cd < 0.5:  # Reasonable CD range
                        ld_ratio = cl_required / cd
                        sink_rate = speed / ld_ratio
                        
                        # Add effects for extreme speeds
                        if speed < min_speed + 3:  # Near stall - higher sink
                            speed_factor = (min_speed + 3) / speed
                            sink_rate *= speed_factor ** 0.3
                        elif speed > max_speed * 0.8:  # High speed - compressibility effects
                            high_speed_factor = 1.0 + 0.1 * ((speed - max_speed * 0.8) / (max_speed * 0.2))
                            sink_rate *= high_speed_factor
                        
                        sink_rates.append(min(sink_rate, 15))  # Cap at 15 m/s
                    else:
                        # Invalid CD - use approximation
                        sink_rates.append(min(12.0, speed * 0.2))
                else:
                    # Outside flyable envelope
                    if cl_required >= 1.6:  # Too slow - near stall
                        sink_rates.append(15.0)
                    else:  # Too fast or invalid conditions
                        sink_rates.append(min(20.0, speed * 0.4))
            except:
                # Fallback calculation
                ld_ratio = models.lift_to_drag_ratio(2.0, params['flap_setting'])  # Assume 2° AOA
                sink_rate = speed / max(ld_ratio, 1)
                sink_rates.append(min(sink_rate, 15))

        # Create DataFrame
        df = pd.DataFrame({
            'Speed [km/h]': speeds_kmh,
            'Sink Rate [m/s]': sink_rates
        })

        # Plot speed polar
        sns.lineplot(data=df, x='Speed [km/h]', y='Sink Rate [m/s]',
                    ax=ax, linewidth=3, color='blue')

        # Current point
        current_speed_kmh = params['airspeed'] * 3.6
        weather_data = params.get('weather', {})
        current_perf = performance.performance_at_speed(
            params['airspeed'], params['altitude'], params['flap_setting'],
            params.get('surface_temp', 288.15), params.get('relative_humidity', 50.0),
            params.get('bank_angle', 0.0), pressure_hpa=weather_data.get('pressure_hpa')
        )
        if current_perf:
            current_sink = current_perf.get('sink_rate', 1)
        else:
            current_ld = models.lift_to_drag_ratio(params['aoa'], params['flap_setting'])
            current_sink = params['airspeed'] / max(current_ld, 1)

        ax.scatter(current_speed_kmh, current_sink, color='red', s=150,
                  zorder=5, edgecolor='white', linewidth=2, label='Current')

        # Best glide speed point
        weather_data = params.get('weather', {})
        best_speed, best_ld = performance.best_glide_speed(
            params['altitude'], params['flap_setting'],
            params.get('surface_temp', 288.15), params.get('relative_humidity', 50.0),
            pressure_hpa=weather_data.get('pressure_hpa')
        )
        best_sink = best_speed / best_ld
        ax.scatter(best_speed * 3.6, best_sink, color='green', s=150,
                  marker='*', zorder=5, edgecolor='white', linewidth=2,
                  label=f'Best Glide ({best_speed*3.6:.0f} km/h)')

        # Minimum sink speed (approximation)
        min_sink_idx = np.argmin(sink_rates)
        min_sink_speed = speeds_kmh[min_sink_idx]
        min_sink_rate = sink_rates[min_sink_idx]
        ax.scatter(min_sink_speed, min_sink_rate, color='purple', s=150,
                  marker='D', zorder=5, edgecolor='white', linewidth=2,
                  label=f'Min Sink ({min_sink_speed:.0f} km/h)')

        ax.set_xlabel('Speed [km/h]')
        ax.set_ylabel('Sink Rate [m/s]')
        ax.set_title(f'Speed Polar - {params["flap_setting"]} flaps')
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_ylim(0, max(max(sink_rates), 5))

        # Invert Y axis (lower sink rates at top, as in aviation)
        ax.invert_yaxis()

        self.figure.tight_layout()
        self.draw()


class PolarPlot(InteractivePlotCanvas):
    """Drag polar plot"""

    def update_plot(self, models, performance, params):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Generate CL range
        cl_range = np.linspace(0.2, 1.8, 50)
        cd_data = [models.cd_from_cl(cl, params['flap_setting']) for cl in cl_range]

        # Create DataFrame
        df = pd.DataFrame({'CL': cl_range, 'CD': cd_data})

        # Plot polar
        sns.lineplot(data=df, x='CD', y='CL', ax=ax, linewidth=2.5)

        # Current point
        current_cl = models.cl_from_aoa(params['aoa'], params['flap_setting'])
        current_cd = models.cd_from_cl(current_cl, params['flap_setting'])
        ax.scatter(current_cd, current_cl, color='red', s=100, zorder=5, label='Current')

        # Best L/D point
        weather_data = params.get('weather', {})
        best_aoa, best_ld, best_cl = performance.find_best_glide_ratio(
            params['flap_setting'], pressure_hpa=weather_data.get('pressure_hpa'))
        best_cd = models.cd_from_cl(best_cl, params['flap_setting'])
        ax.scatter(best_cd, best_cl, color='green', s=100, zorder=5,
                  marker='*', label=f'Best L/D: {best_ld:.1f}')

        ax.set_xlabel('Drag Coefficient CD')
        ax.set_ylabel('Lift Coefficient CL')
        ax.set_title(f'Drag Polar - {params["flap_setting"]} flaps')
        ax.grid(True, alpha=0.3)
        ax.legend()

        self.figure.tight_layout()
        self.draw()


class PerformanceSummaryPlot(InteractivePlotCanvas):
    """Performance summary with multiple subplots"""

    def update_plot(self, models, performance, params):
        self.figure.clear()

        # Create subplots
        gs = self.figure.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

        # 1. Flap comparison
        ax1 = self.figure.add_subplot(gs[0, 0])
        flap_data = []
        flaps = ['clean', '+1', '+2', 'L', 'S']

        weather_data = params.get('weather', {})
        for flap in flaps:
            _, best_ld, _ = performance.find_best_glide_ratio(
                flap, pressure_hpa=weather_data.get('pressure_hpa'))
            best_speed, _ = performance.best_glide_speed(
                params['altitude'], flap, 
                params.get('surface_temp', 288.15), params.get('relative_humidity', 50.0),
                pressure_hpa=weather_data.get('pressure_hpa'))
            flap_data.append({
                'Flap': flap,
                'Best L/D': best_ld,
                'Best Speed [km/h]': best_speed * 3.6
            })

        df_flaps = pd.DataFrame(flap_data)
        sns.barplot(data=df_flaps, x='Flap', y='Best L/D', ax=ax1)
        ax1.set_title('L/D by Flap Setting')
        ax1.grid(True, alpha=0.3)

        # 2. Mass effect
        ax2 = self.figure.add_subplot(gs[0, 1])
        ballast_range = [0, 20, 40, 60, 80, 100]
        mass_data = []
        original_ballast = models.aircraft.ballast_kg
        original_pilot_eq = models.aircraft.pilot_and_eq

        weather_data = params.get('weather', {})
        for ballast in ballast_range:
            # Temporarily change ballast but keep other params
            models.aircraft.ballast_kg = ballast
            wing_loading = models.aircraft.total_mass * 9.80665 / models.aircraft.wing.area_m2
            _, best_ld, _ = performance.find_best_glide_ratio(
                pressure_hpa=weather_data.get('pressure_hpa'))
            best_speed, _ = performance.best_glide_speed(
                pressure_hpa=weather_data.get('pressure_hpa'))
            mass_data.append({
                'Ballast [kg]': ballast,
                'Wing Loading [N/m²]': wing_loading,
                'L/D': best_ld,
                'Speed [km/h]': best_speed * 3.6
            })

        # Restore original values
        models.aircraft.ballast_kg = original_ballast
        models.aircraft.pilot_and_eq = original_pilot_eq

        df_mass = pd.DataFrame(mass_data)
        sns.scatterplot(data=df_mass, x='Wing Loading [N/m²]', y='L/D',
                       size='Ballast [kg]', ax=ax2)
        ax2.set_title('L/D vs Wing Loading')
        ax2.grid(True, alpha=0.3)

        # 3. Current performance table
        ax3 = self.figure.add_subplot(gs[1, :])
        ax3.axis('off')

        # Calculate current performance
        bank_angle = params.get('bank_angle', 0.0)
        surface_temp = params.get('surface_temp', 288.15)
        relative_humidity = params.get('relative_humidity', 50.0)
        weather_data = params.get('weather', {})
        
        lift = models.lift(
            params['airspeed'], params['altitude'], params['aoa'],
            surface_temp, relative_humidity, params['flap_setting'], bank_angle,
            pressure_hpa=weather_data.get('pressure_hpa')
        )
        drag = models.drag(
            params['airspeed'], params['altitude'], params['aoa'],
            surface_temp, relative_humidity, params['flap_setting'],
            pressure_hpa=weather_data.get('pressure_hpa')
        )
        cl = models.cl_from_aoa(params['aoa'], params['flap_setting'])
        cd = models.cd_from_cl(cl, params['flap_setting'])
        weight = models.aircraft.total_mass * 9.80665

        # Calculate additional parameters
        wing_loading = weight/models.aircraft.wing.area_m2
        load_factor = 1.0 / math.cos(math.radians(bank_angle)) if bank_angle > 0 else 1.0
        
        perf_text = f"""
        Current Flight Performance:
        
        Speed: {params['airspeed']:.1f} m/s ({params['airspeed']*3.6:.0f} km/h)
        Altitude: {params['altitude']:.0f} m
        Angle of Attack: {params['aoa']:.1f}°
        Bank Angle: {bank_angle:.1f}°
        Flap Setting: {params['flap_setting']}
        
        Aircraft Mass: {models.aircraft.total_mass:.0f} kg
        Lift: {lift:.0f} N
        Weight: {weight:.0f} N
        Load Factor: {load_factor:.2f}
        Lift/Weight: {lift/weight:.3f}
        
        L/D Ratio: {cl/cd:.1f}
        Sink Rate: {params['airspeed']/(cl/cd):.2f} m/s
        
        Wing Loading: {wing_loading:.1f} N/m²
        Effective WL: {wing_loading*load_factor:.1f} N/m²
        """

        ax3.text(0.1, 0.9, perf_text, transform=ax3.transAxes,
                fontsize=10, verticalalignment='top', fontfamily='monospace')

        self.draw()


def create_plot_canvas(plot_type, parent=None):
    """Factory function to create plot canvases"""
    plot_classes = {
        'cl_aoa': CLvsAoAPlot,
        'speed_polar': SpeedPolarPlot,
        'polar': PolarPlot,
        'summary': PerformanceSummaryPlot
    }

    return plot_classes.get(plot_type, InteractivePlotCanvas)(parent)
