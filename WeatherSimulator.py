import numpy as np
import matplotlib.pyplot as plt

# small adjustments for each environment type
# these values make the same input feel different in coast, mountain, plain, or urban settings
location_effects = {
    "coast": {"wind_delta": 5, "temp_delta": -2, "cape_factor": 0.9, "color": "#7fc7ff", "label": "Coastal"},
    "mountains": {"wind_delta": 2, "temp_delta": -4, "cape_factor": 0.8, "color": "#9b7c4f", "label": "Mountain"},
    "plains": {"wind_delta": 0, "temp_delta": 0, "cape_factor": 1.0, "color": "#c9e294", "label": "Plains"},
    "urban": {"wind_delta": -2, "temp_delta": 3, "cape_factor": 1.1, "color": "#d3d3d3", "label": "Urban"},
}

# how we label the chance of severe weather
# values below 0.3 are low, below 0.6 are moderate, below 1.0 are high, anything else is extreme
severe_thresholds = {
    "low": 0.3,
    "medium": 0.6,
    "high": 1.0,
}


def simulate_parcel_2d(cape, surface_temp, wind_speed=10):
    # estimate the path of a small blob of air as it rises and moves sideways
    g = 9.81
    max_velocity = np.sqrt(2 * max(cape, 0.0))

    height = 0.0
    vertical_velocity = 0.0
    x = 0.0
    dt = 1.0

    xs = []
    ys = []

    for _ in range(200):
        # use a simple rule to add upward motion based on temperature
        acceleration = g * (surface_temp / 300)
        vertical_velocity += acceleration * dt
        vertical_velocity = min(vertical_velocity, max_velocity)

        height += vertical_velocity * dt
        x += wind_speed * dt

        xs.append(x)
        ys.append(height)

        if height > 10000:
            break

    return np.array(xs), np.array(ys)


def compute_severe_chance(cape, surface_temp, wind_speed, location_name):
    # turn the weather inputs into a single chance number between 0 and 1
    location = location_effects.get(location_name, location_effects["plains"])
    base_score = (cape / 3000) + ((surface_temp - 15) / 15) + (wind_speed / 20)
    location_bonus = { #weighting based on location type, some places are more prone to severe weather
        "coast": 0.05,
        "mountains": -0.05,
        "plains": 0.0,
        "urban": 0.08,
    }.get(location_name, 0.0)

    chance = np.clip(0.05 + base_score * 0.2 + location_bonus, 0.0, 1.0)
    return chance


def compute_risk_components(cape, surface_temp, wind_speed, location_name):
    # estimate how likely each type of severe weather is, using the same input values
    location = location_effects.get(location_name, location_effects["plains"])
    storm_base = np.clip( # a base storminess score that feeds into each risk type, influenced by all factors
        0.3 * (cape / 2500)
        + 0.25 * ((surface_temp - 15) / 20)
        + 0.45 * (wind_speed / 25),
        0.0,
        1.0,
    )
    location_mod = { # weighting based on location type, some places are more prone to severe weather
        "coast": 0.05,
        "mountains": -0.05,
        "plains": 0.0,
        "urban": 0.08,
    }.get(location_name, 0.0)

    tornado = np.clip(storm_base * (0.7 + 0.15 * (wind_speed / 25)) + location_mod * 0.3, 0.0, 1.0)
    hail = np.clip(storm_base * (0.8 + 0.15 * (cape / 3000)) + location_mod * 0.2, 0.0, 1.0)
    damaging_wind = np.clip(storm_base * (0.75 + 0.2 * (wind_speed / 25)) + location_mod * 0.25, 0.0, 1.0)
    flash_flood = np.clip(storm_base * (0.5 + 0.25 * ((surface_temp - 15) / 20)) + location_mod * 0.2, 0.0, 1.0)

    return {
        "Tornado": tornado,
        "Hail": hail,
        "Damaging wind": damaging_wind,
        "Flash flood": flash_flood,
    }


def severity_label(chance):
    # pick a simple word for the chance number we computed
    if chance < severe_thresholds["low"]:
        return "Low"
    if chance < severe_thresholds["medium"]:
        return "Moderate"
    if chance < severe_thresholds["high"]:
        return "High"
    return "Extreme"

print("")
print("==============================================")
print("welcome to the weather simulator!")
print("you can enter cape, surface temperature and wind speed to see a parcel trajectory and severe weather chance.")
print("location choices: coast, mountains, plains, urban")
print("==============================================")
print("")

# ask the user for values and use defaults when the input is not valid
try:
    cape = float(input("enter cape, the amount of potential energy available (jules/kg) [default 2000]: ") or 2000) 
    surface_temp = float(input("enter surface temperature (°c) [default 30]: ") or 30)
    wind_speed = float(input("enter horizontal wind speed (meters/s) [default 10]: ") or 10)
    location_name = input("choose a location type (coast, mountains, plains, urban): ").strip().lower() or "plains"
except ValueError:
    print("invalid input detected. using default conditions.")
    cape = 2000
    surface_temp = 30
    wind_speed = 10
    location_name = "plains"

# if the typed location is not recognized, use plains as a safe fallback
if location_name not in location_effects:
    print(f"unknown location '{location_name}'. defaulting to plains.")
    location_name = "plains"

location = location_effects[location_name]
adjusted_cape = cape * location["cape_factor"]
adjusted_temp = surface_temp + location["temp_delta"]
adjusted_wind = wind_speed + location["wind_delta"]

# convert units for display only
surface_temp_f = surface_temp * 9.0 / 5.0 + 32.0
wind_speed_ft = wind_speed * 3.28084

chance = compute_severe_chance(adjusted_cape, adjusted_temp, adjusted_wind, location_name)
risk_components = compute_risk_components(adjusted_cape, adjusted_temp, adjusted_wind, location_name)
severity = severity_label(chance)

def skew_x(temp, pressure, skew_factor=40):
    # move temperatures so the plot looks like a skew-t weather chart
    return temp + skew_factor * np.log10(1000.0 / pressure)

pressure = np.linspace(1000, 100, 40)
height = 44307.7 * (1.0 - (pressure / 1000.0) ** 0.190284)
env_temps = surface_temp - 6.5 * (height / 1000.0)
parcel_temps = surface_temp - 9.8 * (height / 1000.0)

fig, (ax_skewt, ax_info) = plt.subplots(1, 2, figsize=(16, 8), gridspec_kw={"width_ratios": [2, 1]})
fig.patch.set_facecolor('#f7f7f7')

ax_skewt.set_facecolor('#f0f4fb')
ax_skewt.set_yscale('log')
ax_skewt.invert_yaxis()
ax_skewt.set_ylim(1000, 100)
ax_skewt.set_xlim(-40, 50)
ax_skewt.set_title('skew-t log-p diagram', fontsize=18, weight='bold')
ax_skewt.set_xlabel('temperature (°c)')
ax_skewt.set_ylabel('pressure (hpa)')
ax_skewt.grid(True, linestyle='--', alpha=0.4)

# draw vertical temperature lines in the background for orientation
for T in range(-80, 60, 10):
    ax_skewt.plot(skew_x(np.full_like(pressure, T), pressure), pressure, color='#bbbbbb', linewidth=1, alpha=0.6)

# draw the dashed lines that show a simple rising temperature path without moisture
for theta in range(260, 420, 20):
    theta_K = float(theta)
    T_dry = theta_K * (pressure / 1000.0) ** 0.286 - 273.15
    ax_skewt.plot(skew_x(T_dry, pressure), pressure, color='#ff9f00', linestyle='--', linewidth=0.8, alpha=0.7)

ax_skewt.plot(skew_x(env_temps, pressure), pressure, color='#d62728', linewidth=2, label='environmental temp')
ax_skewt.plot(skew_x(parcel_temps, pressure), pressure, color='#1f77b4', linewidth=2, label='parcel ascent')
ax_skewt.fill_betweenx(
    pressure,
    skew_x(env_temps, pressure),
    skew_x(parcel_temps, pressure),
    where=skew_x(parcel_temps, pressure) > skew_x(env_temps, pressure),
    color='#ffcccc',
    alpha=0.4,
)

ax_skewt.set_yticks([1000, 850, 700, 500, 300, 200, 150, 100])
ax_skewt.set_yticklabels(["1000", "850", "700", "500", "300", "200", "150", "100"])
ax_skewt.legend(loc='lower left')

ax_info.axis('off')
ax_info.set_title('severe weather forecast', fontsize=18, weight='bold')

info_lines = [ # a block of text that summarizes the input conditions and the forecast
    f"location: {location['label']}",
    f"cape: {cape:.0f} j/kg",
    f"surface temp: {surface_temp:.1f} °c / {surface_temp_f:.1f} °f",
    f"wind speed: {wind_speed:.1f} m/s / {wind_speed_ft:.1f} ft/s",
    "",
    f"adjusted cape: {adjusted_cape:.0f} j/kg",
    f"adjusted temp: {adjusted_temp:.1f} °c",
    f"adjusted wind: {adjusted_wind:.1f} m/s",
    "",
    f"severe chance: {chance * 100:.1f}%",
    f"severity: {severity}",
    "",
    "risk breakdown:",
    f"  tornado: {risk_components['Tornado'] * 100:.1f}%",
    f"  hail: {risk_components['Hail'] * 100:.1f}%",
    f"  damaging wind: {risk_components['Damaging wind'] * 100:.1f}%",
    f"  flash flood: {risk_components['Flash flood'] * 100:.1f}%",
    "",
    "skew-t key:",
    "  red: environmental temperature profile",
    "  blue: parcel ascent temperature",
    "  light orange dashed lines: dry adiabats",
    "  grey slanted lines: isotherms",
]
info_text = "\n".join(info_lines)
ax_info.text(
    0.01,
    0.98,
    info_text,
    fontsize=12,
    va='top',
    family='monospace',
    bbox=dict(facecolor='white', alpha=0.95, edgecolor='#c8ccd1'),
)

severity_colors = {'Low': '#66c2a5', 'Moderate': '#ffd166', 'High': '#ef476f', 'Extreme': '#8d1a45'}
ax_info.text(
    0.5,
    0.18,
    severity,
    fontsize=24,
    weight='bold',
    color=severity_colors[severity],
    ha='center',
    transform=ax_info.transAxes,
)

plt.tight_layout()
plt.show()
