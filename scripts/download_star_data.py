from pathlib import Path
import argparse
from star_chart import default_data_cache, download_star_data, download_milky_way_data, validate_star_cache

parser = argparse.ArgumentParser(description="Download HYG, Stellarium sky cultures, and Milky Way outlines.")
parser.add_argument("--data-cache", type=Path, default=default_data_cache())
parser.add_argument("--milky-way-only", action="store_true", help="Only download Milky Way outlines, preserving existing star data.")
if __name__ == "__main__":
    args = parser.parse_args()
    try:
        (download_milky_way_data if args.milky_way_only else download_star_data)(args.data_cache, print)
        errors = validate_star_cache(args.data_cache)
        if errors: raise RuntimeError("\n".join(errors))
    except Exception as exc:
        parser.exit(1, f"Download failed: {exc}\n")
    print(f"Validated cache: {args.data_cache}")
