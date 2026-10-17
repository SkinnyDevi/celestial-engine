import argparse

from core.celestial_importer import CelestialImporter, Time
from core.catalogs import CatalogSource

def main():
    parser = argparse.ArgumentParser(
        description="Celestial Body Engine Data Importer with Astropy Precision 3D Mapping & Magnitude Filter"
    )
    parser.add_argument("--degrees", type=float, default=1.0, help="Search radius degrees around target (default: 1.0)")
    parser.add_argument("--target", type=str, default="M31", help="Target celestial object or galaxy (default: 'M31')")
    parser.add_argument("--limit", type=int, default=-1, help="Max stars to fetch (-1 for unlimited, default: -1)")
    parser.add_argument("--max-mag", type=float, default=18.0, help="Apparent magnitude cutoff: drops objects fainter than this (default: 18.0; pass -1 to disable)")
    parser.add_argument("--drop-unmeasured", action="store_true", default=False, help="Drop stars that lack photometric measurement in catalog")
    parser.add_argument("--distance-pc", type=float, default=780000.0, help="Default distance in parsecs for region objects (default: 780000 for M31)")
    parser.add_argument(
        "--source",
        type=str,
        default="auto",
        choices=["auto", "gaia", "bailer-jones", "starhorse", "hipparcos", "simbad"],
        help="Distance catalog source: 'auto' (smart routing), 'gaia' (DR3 geometric parallax), 'bailer-jones' (Bayesian distance), 'starhorse' (dense/dust fields), 'hipparcos' (bright stars m < 6), 'simbad' (default Simbad)"
    )
    parser.add_argument(
        "--bj-mode",
        type=str,
        default="photogeometric",
        choices=["photogeometric", "geometric"],
        help="Bailer-Jones distance method: 'photogeometric' (stellar models + parallax) or 'geometric' (space density prior)"
    )
    parser.add_argument(
        "--enrich-simbad",
        action="store_true",
        default=False,
        help="Enrich Simbad stars with precision distance measurements from Gaia/Bailer-Jones/StarHorse/Hipparcos"
    )
    parser.add_argument("--skip-solar-system", action="store_true", default=False, help="Skip adding Sun, planets and moons")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path (default: real_world_data_<target>_<source>_<degrees>deg.json)")
    parser.add_argument("--date", type=str, default="2024-10-05T12:30:00", help="Simulation epoch date (default: 2024-10-05T12:30:00)")
    args = parser.parse_args()

    max_mag = None if (args.max_mag is not None and args.max_mag < 0) else args.max_mag
    keep_unmeasured = not args.drop_unmeasured
    prefer_photogeometric = (args.bj_mode == "photogeometric")

    print("=== Celestial Body Engine Importer ===")
    print(f"Epoch Date: {args.date}")
    print(f"Target Region: {args.target} (Radius: {args.degrees} deg)")
    print(f"Catalog Source: {args.source} (Bailer-Jones mode: {args.bj_mode})")
    print(f"Apparent Magnitude Cutoff: {f'm <= {max_mag}' if max_mag is not None else 'Disabled (all magnitudes)'}")
    print(f"Keep Unmeasured Photometry: {keep_unmeasured}")

    importer = CelestialImporter(
        Time(args.date),
        max_apparent_magnitude=max_mag,
        keep_unmeasured=keep_unmeasured,
        prefer_photogeometric=prefer_photogeometric
    )
    
    # -------------------------------------------------------------------------
    # SOLAR SYSTEM (Sun, All 8 Planets, Dwarf Planet Pluto, and Major Moons)
    # -------------------------------------------------------------------------
    if not args.skip_solar_system:
        importer.add_solar_system(include_moons=True, include_dwarf_planets=True)
    
    # -------------------------------------------------------------------------
    # STELLAR OBJECTS & 3D PRECISION MAPPING
    # -------------------------------------------------------------------------
    if args.source == "simbad":
        importer.add_stars_in_region(
            args.target,
            radius_degrees=args.degrees,
            limit=args.limit,
            default_distance_pc=args.distance_pc,
            use_precise_distances=args.enrich_simbad
        )
    else:
        importer.add_stars_from_catalog(
            center_name=args.target,
            radius_degrees=args.degrees,
            source=args.source,
            limit=args.limit,
            default_distance_pc=args.distance_pc,
        )

    out_file = args.output if args.output else f'real_world_data_{args.target.replace(" ", "-")}_{args.source}_maxmag_{"disabled" if max_mag is None else int(max_mag)}_{args.degrees:g}deg.json'
    importer.save(out_file)

if __name__ == "__main__":
    main()
