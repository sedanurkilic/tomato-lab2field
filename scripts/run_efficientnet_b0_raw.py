"""Single entry point for the three-seed RAW baseline."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from efficientnet_raw import validate, run

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    config = json.loads((ROOT / 'configs/efficientnet_b0_raw.json').read_text())
    splits = validate(config)
    if not args.validate_only:
        run(config, splits)
