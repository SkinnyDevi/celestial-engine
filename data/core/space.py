from enum import Enum

class SpectralType(Enum):
    O = 0
    B = 1
    A = 2
    F = 3
    G = 4
    K = 5
    M = 6

# Planet Classes (matching PlanetClass enum in planet.h)
class PlanetClass(Enum):
    TERRESTRIAL = 0
    GAS_GIANT = 1
    ICE_GIANT = 2
    DWARF = 3
    ROGUE = 4

# Atmosphere Types (matching AtmosphereType enum in planet.h)
class AtmosphereType(Enum):
    NONE = 0
    THIN = 1
    STANDARD = 2
    DENSE = 3
    THICK_ENVELOPE = 4

# Moon Classes (matching MoonClass enum in moon.h)
class MoonClass(Enum):
    ROCKY = 0
    ICY = 1
    CAPTURED = 2
    VOLCANIC = 3

# Optical photometric bands for apparent magnitude filtering (ordered by preference)
# V: Johnson Visual, G: Gaia broadband, g/r: SDSS green/red, B: Johnson Blue, R/I: Cousins Red/Infrared
class OpticalMagBands(Enum):
    V = "V"
    G = "G"
    g = "g"
    r = "r"
    R = "R"
    B = "B"
    I = "I"
    
    @staticmethod
    def list() -> list[str]:
        """Get list of optical photometric bands."""
        return [item.value for item in OpticalMagBands]
    
    @staticmethod
    def from_str(s: str) -> 'OpticalMagBands':
        """Get OpticalMagBand from string."""
        for item in OpticalMagBands:
            if item.value == s:
                return item
        raise ValueError(f"Invalid OpticalMagBands value: {s}")
