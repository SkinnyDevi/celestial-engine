"""
JPL Horizons Moon Provider
Dynamically resolves natural satellite ephemerides and orbital elements from NASA JPL Horizons.
Safely handles celestial exceptions, network fallbacks, and coordinate origin singularities (such as the Sun).
"""

from typing import Any
import math
from astropy.coordinates import SkyCoord
from astropy.time import Time
from astropy.table import Table

from core.constants import AU_TO_METERS, DEG_TO_RAD, G_CONST
from core.space import MoonClass, AtmosphereType
from core.math import safe_float
from core.planets.models import OrbitRecord
from core.moons.models import MoonRecord, sanitize_moon_id, classify_moon_type
from core.moons.providers.base import BaseMoonProvider
from core.moons.providers.solar_system import SolarSystemMoonProvider


class JPLHorizonsMoonProvider(BaseMoonProvider):
    """
    Ephemeris provider querying the NASA JPL Horizons system for moon orbits and state vectors.
    Includes robust error handling and fallbacks for when Horizons is unreachable or when invalid
    targets (such as the Sun) are specified.
    """

    # Mapping of common moon names to (jpl_id, center_id, host_planet_name, host_planet_id)
    KNOWN_JPL_MOONS: dict[str, tuple[str, str, str, str]] = {
        "MOON": ("301", "@399", "Earth", "EARTH"),
        "LUNA": ("301", "@399", "Earth", "EARTH"),
        "PHOBOS": ("401", "@499", "Mars", "MARS"),
        "DEIMOS": ("402", "@499", "Mars", "MARS"),
        "IO": ("501", "@599", "Jupiter", "JUPITER"),
        "EUROPA": ("502", "@599", "Jupiter", "JUPITER"),
        "GANYMEDE": ("503", "@599", "Jupiter", "JUPITER"),
        "CALLISTO": ("504", "@599", "Jupiter", "JUPITER"),
        "AMALTHEA": ("505", "@599", "Jupiter", "JUPITER"),
        "HIMALIA": ("506", "@599", "Jupiter", "JUPITER"),
        "MIMAS": ("601", "@699", "Saturn", "SATURN"),
        "ENCELADUS": ("602", "@699", "Saturn", "SATURN"),
        "TETHYS": ("603", "@699", "Saturn", "SATURN"),
        "DIONE": ("604", "@699", "Saturn", "SATURN"),
        "RHEA": ("605", "@699", "Saturn", "SATURN"),
        "TITAN": ("606", "@699", "Saturn", "SATURN"),
        "HYPERION": ("607", "@699", "Saturn", "SATURN"),
        "IAPETUS": ("608", "@699", "Saturn", "SATURN"),
        "PHOEBE": ("609", "@699", "Saturn", "SATURN"),
        "ARIEL": ("701", "@799", "Uranus", "URANUS"),
        "UMBRIEL": ("702", "@799", "Uranus", "URANUS"),
        "TITANIA": ("703", "@799", "Uranus", "URANUS"),
        "OBERON": ("704", "@799", "Uranus", "URANUS"),
        "MIRANDA": ("705", "@799", "Uranus", "URANUS"),
        "PUCK": ("715", "@799", "Uranus", "URANUS"),
        "TRITON": ("801", "@899", "Neptune", "NEPTUNE"),
        "NEREID": ("802", "@899", "Neptune", "NEPTUNE"),
        "PROTEUS": ("808", "@899", "Neptune", "NEPTUNE"),
        "CHARON": ("901", "@999", "Pluto", "PLUTO"),
        "NIX": ("902", "@999", "Pluto", "PLUTO"),
        "HYDRA": ("903", "@999", "Pluto", "PLUTO"),
    }

    def __init__(self, fallback_provider: SolarSystemMoonProvider | None = None) -> None:
        self.fallback_provider: SolarSystemMoonProvider = (
            fallback_provider if fallback_provider is not None else SolarSystemMoonProvider()
        )

    @property
    def name(self) -> str:
        return "jpl_horizons_moons"

    def query_by_host_planet(
        self,
        planet_name: str,
        host_id: str | None = None,
        **kwargs: Any
    ) -> list[MoonRecord]:
        """
        Queries JPL Horizons for moons of a given planet.
        Handles the SUN exception case gracefully: Sun has no direct moons.
        """
        clean_name = planet_name.strip().upper()
        if clean_name in ("SUN", "SOL", "THE SUN"):
            print("Notice: The Sun is a star, not a planet. Natural satellites orbit planets, so no moons orbit the Sun directly.")
            return []

        # Use fallback curated provider as base, then enrich if online is requested
        return self.fallback_provider.query_by_host_planet(planet_name, host_id=host_id, **kwargs)

    def query_by_system(
        self,
        host_star_name: str,
        **kwargs: Any
    ) -> list[MoonRecord]:
        """
        Queries all natural satellites in the system of the given star.
        For Sun/Sol, returns all Solar System moons.
        """
        clean_name = host_star_name.strip().upper()
        if clean_name in ("SUN", "SOL", "THE SUN"):
            return self.fallback_provider.query_by_system("Sun", **kwargs)
        return []

    def get_known_moon(
        self,
        moon_name: str,
        sim_time: Time | None = None,
        use_online: bool = False,
        **kwargs: Any
    ) -> MoonRecord | None:
        """
        Resolves a moon either via online JPL Horizons query or curated fallback.
        """
        clean_name = moon_name.strip().upper()
        if clean_name in ("SUN", "SOL", "THE SUN"):
            raise ValueError(
                "Cannot query 'Sun' as a moon: The Sun is a star, not a natural satellite."
            )

        if use_online and clean_name in self.KNOWN_JPL_MOONS:
            jpl_id, center_id, host_planet, host_bid = self.KNOWN_JPL_MOONS[clean_name]
            try:
                rec = self.fetch_moon_from_jpl(
                    name=moon_name,
                    jpl_id=jpl_id,
                    center_id=center_id,
                    host_planet_name=host_planet,
                    host_planet_id=host_bid,
                    sim_time=sim_time,
                )
                if rec is not None:
                    return rec
            except Exception as e:
                print(f"Warning: JPL Horizons query failed for '{moon_name}' ({e}). Using precision catalog.")

        return self.fallback_provider.get_known_moon(moon_name, sim_time=sim_time, **kwargs)

    def get_all_moons(self, **kwargs: Any) -> list[MoonRecord]:
        return self.fallback_provider.get_all_moons(**kwargs)

    def query_by_region(
        self,
        center_coord: SkyCoord,
        radius_deg: float,
        **kwargs: Any
    ) -> list[MoonRecord]:
        return self.fallback_provider.query_by_region(center_coord, radius_deg, **kwargs)

    def fetch_moon_from_jpl(
        self,
        name: str,
        jpl_id: str,
        center_id: str,
        host_planet_name: str,
        host_planet_id: str | None = None,
        sim_time: Time | None = None,
        **kwargs: Any
    ) -> MoonRecord | None:
        """
        Directly queries astroquery.jplhorizons for a moon's Keplerian elements and position vectors.
        Raises ValueError if center or target is the Sun.
        """
        clean_target = name.strip().upper()
        if clean_target in ("SUN", "SOL", "THE SUN") or jpl_id in ("10", "SUN"):
            raise ValueError(
                "The Sun cannot be queried as a moon in JPL Horizons ephemerides."
            )

        if center_id.lower() in ("@sun", "@10", "@0") and clean_target in ("SUN", "SOL"):
            raise ValueError("Center body cannot be identical to target body in JPL Horizons query.")

        epoch_jd = sim_time.jd if sim_time is not None else Time.now().jd

        try:
            from astroquery.jplhorizons import Horizons
        except ImportError:
            print("Warning: astroquery not available; using fallback catalog.")
            return self.fallback_provider.get_known_moon(name)

        obj = Horizons(id=jpl_id, location=center_id, epochs=epoch_jd)
        elements = obj.elements()
        vectors = obj.vectors()

        if elements is None or len(elements) == 0 or vectors is None or len(vectors) == 0:
            return None

        clean_name, body_id = sanitize_moon_id(name)
        h_name, h_id = host_planet_name, (host_planet_id or host_planet_name.upper())

        a_au = safe_float(elements['a'][0])
        a_km = a_au * (AU_TO_METERS / 1000.0)
        e = safe_float(elements['e'][0])
        inc_rad = safe_float(elements['incl'][0]) * DEG_TO_RAD
        node_rad = safe_float(elements['Omega'][0]) * DEG_TO_RAD
        peri_rad = safe_float(elements['w'][0]) * DEG_TO_RAD
        m_rad = safe_float(elements['M'][0]) * DEG_TO_RAD
        period_days = safe_float(elements['P'][0])

        pos = {
            "x": safe_float(vectors['x'][0]) * AU_TO_METERS,
            "y": safe_float(vectors['y'][0]) * AU_TO_METERS,
            "z": safe_float(vectors['z'][0]) * AU_TO_METERS,
        }

        orbit = OrbitRecord(
            semimajor_axis=a_km * 1000.0,
            eccentricity=e,
            inclination=inc_rad,
            longitude_of_ascending_node=node_rad,
            argument_of_periapsis=peri_rad,
            mean_anomaly_at_epoch=m_rad,
            orbital_period_days=period_days,
            mean_anomaly=m_rad,
            center_position={"x": 0.0, "y": 0.0, "z": 0.0},
        )

        # Merge known physical params from fallback if available
        known_ref = self.fallback_provider.get_known_moon(name)
        mass = known_ref.mass_kg if known_ref else 1.0e20
        radius = known_ref.radius_m if known_ref else 1.0e5
        moon_cls = known_ref.moon_class if known_ref else MoonClass.ROCKY
        atm = known_ref.atmosphere_type if known_ref else AtmosphereType.NONE
        albedo = known_ref.albedo if known_ref else 0.3
        temp = known_ref.surface_temperature_k if known_ref else 100.0

        rec = MoonRecord(
            name=clean_name,
            body_id=body_id,
            host_planet_name=h_name,
            host_planet_id=h_id,
            moon_class=moon_cls,
            atmosphere_type=atm,
            position=pos,
            semi_major_axis_km=a_km,
            eccentricity=e,
            inclination_rad=inc_rad,
            longitude_ascending_node_rad=node_rad,
            argument_periapsis_rad=peri_rad,
            mean_anomaly_rad=m_rad,
            orbital_period_days=period_days,
            mass_kg=mass,
            radius_m=radius,
            albedo=albedo,
            surface_temperature_k=temp,
            orbit=orbit,
            extra_metadata={"jpl_id": jpl_id, "source": "jpl_horizons"},
        )
        return rec
