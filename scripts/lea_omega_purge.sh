#!/usr/bin/env bash
# LEA-Ω (Loose End Annihilator)
# Sovereign Purge Script - Zero Thermodynamic Residue

set -e

echo "[LEA-Ω] Initiating thermodynamic purge..."

# 1. Purge Python cache residues
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -type f -name "*.pyd" -delete
rm -rf .pytest_cache
rm -rf .coverage
rm -rf .tox
rm -rf build/
rm -rf dist/
rm -rf *.egg-info

# 2. Purge Rust target/debug if necessary (excluding target/release if we want to keep it, but cargo clean is safer)
# cargo clean # Uncomment if full Rust purge is needed

# 3. Aniquilar logs muertos y scratchpads huérfanos que no estén en control de versiones
rm -rf scratch/*
rm -rf agents-archi/* # Empty out the untracked agents-archi folder if any

echo "[LEA-Ω] Entropy anihilated. State is C5-REAL."
