"""Regenerate the review's eight analytical section comparisons, not an ML dataset."""

import argparse
import csv
from pathlib import Path

from .beam_theory import box, cantilever, rectangle, tip_mass_frequency
from .config import load_config


def screening_rows(config: dict) -> list[dict]:
    sections = [
        ("flat_25x4", rectangle(25, 4)),
        ("flat_25x6", rectangle(25, 6)),
        ("flat_25x10", rectangle(25, 10)),
        ("edge_4x25", rectangle(4, 25)),
        ("box_20x20_t2", box(20, 20, 2)),
        ("box_20x25_t2", box(20, 25, 2)),
        ("box_20x25_t2.5", box(20, 25, 2.5)),
        ("box_20x25_t3", box(20, 25, 3)),
    ]
    rows = []
    for name, section in sections:
        values = cantilever(
            section, length_mm=config["interfaces"]["reach_mm"],
            force_N=config["loads"]["LC1"]["force_N"][2],
            modulus_MPa=config["material"]["youngs_modulus_MPa"],
            density_g_cm3=config["material"]["density_g_cm3"],
        )
        values["estimated_f1_Hz"] = tip_mass_frequency(
            values["stiffness_N_mm"], values["arm_mass_g"], config["interfaces"]["tip_mass_g"])
        rows.append({"section": name, **values})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/study.json"))
    parser.add_argument("--output", type=Path, default=Path("results/screening.csv"))
    args = parser.parse_args()
    rows = screening_rows(load_config(args.config))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} analytical comparisons to {args.output}; no FE runs.")


if __name__ == "__main__":
    main()
