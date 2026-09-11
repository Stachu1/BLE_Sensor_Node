# BLE Sensor Node

**BEng in Electronics Engineering thesis project, focused on low-power design and RF performance.**

A compact, coin-cell-powered Bluetooth Low Energy sensor node that measures temperature and
humidity and advertises the data periodically, without needing a persistent connection.

## Goal

Keep average current low enough for multi-year operation on a single CR2032 cell, while staying
within a small form factor. Main areas of work: low-power firmware and advertising strategy,
antenna/RF performance (chip vs. trace antenna), and power budgeting around the coin cell's
current limits.

Two BLE MCUs are being evaluated in parallel: **Nordic nRF54L** and **TI CC2340R5**.

## Repository Structure

```
hardware/       KiCad schematics & PCB layout, one subfolder per MCU variant
firmware/       SDK-based firmware, one subfolder per MCU variant
docs/           Notes, datasheets, write-ups
results/        Power profiling logs, range-test data
```

The two MCU candidates are different chips (different pinout, power tree, likely BOM) rather
than build options of one board, so each gets its own KiCad project under `hardware/<variant>/`
and its own `firmware/<variant>/`. Both live side by side on `main` and iterate through normal
commits. Once a chip is selected, the other candidate's folder can be
archived or removed.

## Status

Early stage — component evaluation and initial hardware/firmware design.
