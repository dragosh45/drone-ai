"""Gate 0 CLI: environment diagnostics only."""

import argparse
from pathlib import Path

from .doctor import doctor


def main() -> int:
    parser = argparse.ArgumentParser(prog="drone-arm")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("doctor", help="Check configuration, imports and ccx version")
    check.add_argument("--config", type=Path, default=Path("configs/study.json"))
    args = parser.parse_args()
    return doctor(args.config)
