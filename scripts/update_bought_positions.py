"""Rewrite the bought_positions section of config/config.yaml from an IBKR
"Open Positions" CSV export (e.g. U15665321_20260724.csv).

Usage:
    python scripts/update_bought_positions.py <path_to_csv> [path_to_config.yaml]
"""

import csv
import re
import sys
from pathlib import Path

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "config.yaml"


def parse_positions(csv_path):
    """Extract (symbol, shares, entry_price) tuples from an Open Positions CSV export."""
    positions = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            fields = row[0].split(",")
            if len(fields) < 9:
                continue
            if fields[0] != "Open Positions" or fields[1] != "Data" or fields[2] != "Summary":
                continue
            symbol = fields[5]
            quantity = float(fields[6])
            cost_price = float(fields[8])
            positions.append((symbol, quantity, cost_price))
    return positions


def format_shares(quantity):
    if quantity == int(quantity):
        return str(int(quantity))
    return str(quantity)


def build_section(positions):
    lines = []
    for symbol, quantity, cost_price in positions:
        lines.append(f'  - id: "{symbol}"')
        lines.append(f"    symbol: {symbol}")
        lines.append(f"    entry_price: {round(cost_price, 2)}")
        lines.append(f"    shares: {format_shares(quantity)}")
    return "\n".join(lines) + "\n"


def replace_bought_positions(config_text, new_section):
    pattern = re.compile(
        r"(bought_positions:\n)(?:(?:  - .*\n|    .*\n)*)",
        re.MULTILINE,
    )
    if not pattern.search(config_text):
        raise ValueError("Could not find bought_positions: section in config.yaml")
    return pattern.sub(lambda m: m.group(1) + new_section, config_text, count=1)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/update_bought_positions.py <path_to_csv> [path_to_config.yaml]")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    config_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_CONFIG_PATH

    positions = parse_positions(csv_path)
    if not positions:
        print("No positions found in CSV.")
        sys.exit(1)

    new_section = build_section(positions)
    config_text = config_path.read_text(encoding="utf-8")
    updated_text = replace_bought_positions(config_text, new_section)
    config_path.write_text(updated_text, encoding="utf-8")

    print(f"Updated {len(positions)} bought positions in {config_path}")


if __name__ == "__main__":
    main()
