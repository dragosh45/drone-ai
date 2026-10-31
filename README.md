# Drone AI — Lightweight PETG Quadcopter Arm

## Project topic

Designing a lighter quadcopter motor arm for PETG 3D-printing prototypes, using
a machine-learning surrogate trained on finite-element analysis results.

## Description

This project aims to reduce the mass of a quadcopter motor-support arm while
preserving its reach, mounting interfaces and specified mechanical limits.
The proposed design is a parametric rectangular box section with circular
lightening holes in its side walls. Wall thickness, section height and hole
size vary; the material remains PETG.

The planned workflow generates geometric configurations using Latin Hypercube
sampling and evaluates them with finite-element analysis (FEA), recording tip
deflection, stresses and natural frequencies. These simulation results will be
used to train and compare linear regression, polynomial regression, Random Forest,
Gaussian process and multilayer perceptron (MLP) models, alongside simple baselines
and analytical beam calculations.

The selected surrogate will provide fast response estimates during a search for
lower-mass geometry that satisfies stiffness and strength constraints. Candidate
designs will then be checked again with FEA and compared with the original design,
an analytical approach and a direct FEA search.

**Mass is calculated from geometry and material density.** Machine learning predicts
mechanical responses; the design optimiser changes geometry to reduce mass.
The study will assess whether a surrogate provides a useful benefit once the cost
of generating its training data is included.

This is an individual university course project in AI and machine learning applied
to computer-aided engineering and manufacturing. The intended outcome is a
simulation-based prototype design with STEP/STL exports. Physical printing and
testing are possible extensions; flight suitability has not been established.

## Current implementation

**Gate 0 is complete.** The repository currently contains:

- A provisional study configuration, validation checks and a reproducible config hash.
- Analytical comparisons of flat and box sections, including beam-theory checks.
- A conda environment, a macOS arm64 package lock and an environment diagnostic command.
- Tests for the configuration, analytical calculations and diagnostics.

CAD generation, meshing, FE simulations, dataset generation, ML training and design
optimisation are planned work. No trained surrogate or optimised arm is available yet.

## Tools

| Tool | Role |
|---|---|
| Python 3.12 | Implementation and workflow orchestration |
| CadQuery | Planned parametric geometry and STEP/STL export |
| Gmsh | Planned finite-element meshing |
| CalculiX | Planned static and modal finite-element analysis |
| scikit-learn | Planned regression models and evaluation |
| SciPy | Planned sampling and differential-evolution design search |
| pandas and Matplotlib | Tables and plots |
| pytest | Automated checks |

## Getting started

Install Miniforge, then run these commands from the repository root in a shell
with conda available:

```bash
conda env create --file environment.yml
conda activate drone-ai
python -m pip install --no-deps --no-build-isolation -e .
python -m drone_arm doctor
pytest -q
```

On the existing Mac installation, conda can be enabled in the current shell with
`source ~/miniforge3/etc/profile.d/conda.sh`. On Windows, use the Miniforge prompt.
The environment has been checked on macOS arm64; Windows and Ubuntu remain unverified.

The doctor checks imports and runs `ccx -v`; a passing result confirms tool
availability, not the validity of a structural simulation. CalculiX 2.23 returns
exit code 201 for its version query; the doctor accepts it only with the expected
version response. Gmsh requires both the `gmsh` and `python-gmsh` conda packages.
`pip` and `setuptools` install this local Python package; conda supplies its dependencies.

To reproduce the resolved macOS arm64 package versions:

```bash
conda create --name drone-ai-repro --file locks/macos-arm64.txt
conda activate drone-ai-repro
python -m pip install --no-deps --no-build-isolation -e .
export OMP_NUM_THREADS=1
python -m drone_arm doctor
pytest -q
```

This lock is platform-specific. A fresh installation from it has not yet been
tested. The environment YAML sets `OMP_NUM_THREADS=1`; explicit locks do not
include environment variables or the editable local package.

## Reproduce the analytical examples

```bash
python -m drone_arm.screening
python tests/test_beam_theory.py
```

The first command writes eight section comparisons to `results/screening.csv`.
The second prints the reference tube's analytical inputs and results and runs its
tests. These examples assume uniform, unperforated beams and are not FEA results.

## Repository layout

```text
configs/       Study configuration and provisional engineering assumptions
src/drone_arm/ Implementation and diagnostic CLI
tests/         Automated checks and analytical reference examples
results/       Small reproducible analytical results
locks/         Platform-specific conda package locks
```

Course documents, internal planning notes, agent instructions and machine-specific
doctor logs are kept locally and excluded from tracking. They are not required to
run the implementation. This repository contains the implementation and its
public project overview.
