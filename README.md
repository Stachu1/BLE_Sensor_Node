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
hardware/
  N54/          BSN-N54 - Nordic nRF54L variant (KiCad project BSN-N54.kicad_pro)
  C23/          BSN-C23 - TI CC2340R5 variant
firmware/
  N54/          Firmware for BSN-N54 boards
  C23/          Firmware for BSN-C23 boards
docs/           Notes, datasheets, write-ups
results/        Power profiling logs, range-test data
```

The two MCU candidates are different chips (different pinout, power tree, likely BOM) rather
than build options of one board, so each gets its own KiCad project under `hardware/<variant>/`
and its own `firmware/<variant>/`, where `<variant>` is the variant code below. Both live side by side on `main` and iterate through normal
commits. Once a chip is selected, the other candidate's folder can be
archived or removed.

## Naming Scheme

Each board is identified as **`BSN-<variant>-<revision>`**, e.g. `BSN-N54-A`.

```
BSN-N54-A
 │   │  └─ PCB revision  (A, B, C …)
 │   └──── MCU variant   (N54 = Nordic nRF54L, C23 = TI CC2340R5)
 └──────── Board name    (BSN = BLE Sensor Node)
```

| Part | Values | Meaning |
|---|---|---|
| Board | `BSN` | BLE Sensor Node. Never changes. |
| Variant | `N54`, `C23` | First letter of the MCU part prefix (**n**RF54 → N, **C**C2340 → C) + MCU family number. Stays the same across parts in one family (e.g. nRF54L05/L10/L15). |
| Revision | `A`, `B`, `C` | Bare-PCB revision. Bumped only when copper or fab outputs change, i.e. when new boards are ordered. |
| Assembly option *(optional)* | e.g. `-UFL` | Population option on the same bare PCB (e.g. U.FL fitted instead of the chip antenna). Does not change the revision. |

Rules:

- **Each variant has its own revision counter.** `BSN-N54-C` and `BSN-C23-A` can exist at the same time.
- **Letters are only for boards that were ordered.** Work in progress before an order is still the upcoming letter.
  Once gerbers are sent to the fab that letter is frozen, and any later change means the next letter.
- **Reworked boards are not new revisions.** A hand-modified board is marked `A*` and the rework is noted in the variant README.
- **The ID is on the board itself.** The revision is set in the KiCad title block, and the ID is printed on the silkscreen.

Where the name appears:

| Item | Example |
|---|---|
| Hardware / firmware folder | `hardware/N54/`, `firmware/N54/` |
| KiCad project | `hardware/N54/BSN-N54.kicad_pro` |
| BOM in the repo | `hardware/N54/BSN-N54_BOM.csv` |
| Exported fab package | `BSN-N54-A_gerbers.zip`, `BSN-N54-A_BOM.csv`, `BSN-N54-A_pos.csv` |
| Git tag on the ordered commit | `hw/BSN-N54-A` |
| Firmware | board target `BSN_N54`, hardware revision `A` (also reported in the BLE Device Information Service) |

Boards:

| Board | MCU | Status |
|---|---|---|
| `BSN-N54-A` | nRF54L05 | Ordered and assembled (2 boards). Board #1 advertising BTHome. Board #2 (U.FL): HFXO trimmed to 11.75 pF, PA network bypassed (the rev A layout of it loses 10 dB), 0.0 dBm at the 0 dBm setting. Floor 4.20 µA, 7.6 µC per advert |
| `BSN-C23-A` | CC2340R5 | Ordered and assembled. Board #1 flashed and advertising BTHome; antenna matched with the battery connector fitted (L2 4.3 nH, L3 2.1 pF). Floor 0.366 µA, 12.6 µC per advert. CW boards with and without the PA pi network |

## Status

Rev A of both variants was compared (thesis test T0). **Rev B uses the TI CC2340R5 (`BSN-C23-B`)** with a PCB trace
antenna; the N54 variant stops at rev A. Reasons: [`hardware/MCU_DECISION.md`](hardware/MCU_DECISION.md). Rev C is
the final prototype with the rev B fixes.

| | `BSN-C23-A` | `BSN-N54-A` |
|---|---|---|
| Sleep floor | 0.366 µA | 4.20 µA (System OFF 2.05 µA; about 1.4 µA above the datasheet on both boards, cause not found) |
| Charge per advert, 0 dBm | 12.6 µC | 7.6 µC |
| Charge per sensor reading, timer / DRDY wake | 9.56 / 3.72 µC | 2.01 / 1.78 µC |
| Conducted power at the 0 dBm setting | −2.1 dBm | 0.0 dBm (PA network bypassed) |
| Harmonics (conducted, FCC restricted-band limit −41.2 dBm) | Pass with the pi network at +8 dBm (2440 and 2480 MHz), 9.5 dB margin (H5). Without it, H3 −28.6 dBm at +8 dBm | H3 −24.3 dBm at 0 dBm with no filter (fails by 17 dB); no working filter on this layout yet |
| Notes | [`hardware/C23/testing`](hardware/C23/testing) | [`hardware/N54/testing`](hardware/N54/testing) |
