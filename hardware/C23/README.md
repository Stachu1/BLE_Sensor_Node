# BSN-C23 (TI CC2340R5 variant)

KiCad project: `BSN-C23.kicad_pro`. See the root README for the board naming scheme.

## Rev A (`BSN-C23-A`)

This project started as a copy of `BSN-N54-A` (board outline, power, sensors, antenna and
test points), with the MCU, power tree, 48 MHz crystal, RF network and SWD pins replaced for the
CC2340R5. Rev A was exported and ordered on the combined panel (`hardware/panel/`).

**Population:** DNP = U2 (SHTC3), X2 (32 kHz, LFOSC is used instead), C9, C14, C15, C16, C19, C20,
J1 (U.FL), L4. Everything else is fitted.

**RF network as fitted** (values from the TI reference design, not tuned for this board):

| Ref | Value | Part |
|---|---|---|
| C7, C8 | 1.5 pF | 490-8087-1-ND |
| L1 | 2.8 nH | LQW15AN2N8G80D |
| C6 | 15 pF | 490-11191-1-ND |
| L2 | 6.7 nH | LQW15AN6N7B00D |
| L3 | 7.3 nH | 490-6844-1-ND |
| AE1 | Chip antenna | AANI-CH-0138-Q-T |

**Tuned antenna match** (VNA, battery connector fitted, see below): L2 = **4.3 nH**, **2.1 pF** on the
L3 pads instead of the 7.3 nH. Not yet fitted on board #1.

### Bring-up status

Procedure and per-board results: [`firmware/C23/BRINGUP.md`](../../firmware/C23/BRINGUP.md).

| Board | BLE address | Status |
|---|---|---|
| #1 | FC:DE:C5:73:2F:4E | Flashes over SWD. `hwtest` 13/13 PASS. `ble_sensor` advertises BTHome and readings are received on the PC with `tools/bsn_scan.py`. Still has the TI reference RF values. |
| RF test | (no MCU) | Antenna-only board used for VNA matching, see below. |
| RF CW | | MCU, X1, pi network (C7/L1/C8) and J1 only, no antenna. Used with `cwtest` for the carrier frequency and output power, see [`testing/RF_CARRIER.md`](testing/RF_CARRIER.md): HFXT trim set to 44 (+2.2 ppm), +6.7 dBm at the +8 dBm setting. |

### Antenna matching

Full notes and data: [`testing/ANTENNA_MATCHING.md`](testing/ANTENNA_MATCHING.md).

The TI reference values don't fit this layout. At 2.44 GHz the bare antenna is about 6.4 − j13 Ω, and
6.7 nH for L2 is about three times too much. On the RF-only test board (Keysight P9370B through J1):

| Date | Configuration | L2 (series) | L3 pads (shunt) | S11 at 2.44 GHz | Worst in 2.40–2.48 GHz |
|---|---|---|---|---|---|
| — | TI reference | 6.7 nH | 7.3 nH | not measured | — |
| 2026-10-23 | Matched, no battery | 3.3 nH | 2.0 pF | −18.8 dB | −11.0 dB |
| 2026-10-23 | Same, battery fitted | 3.3 nH | 2.0 pF | −3.1 dB (9.5 + j12.3 Ω) | — |
| 2026-10-26 | **Matched, battery connector fitted** | **4.3 nH** | **2.1 pF** | **−32.1 dB** | **−10.3 dB** |

The battery connector raises the board and detunes the antenna, lowering its resistance to about a third;
with the connector fitted, the coin cell in or out makes almost no difference. **Use 4.3 nH + 2.1 pF.**
Until they are fitted on a working board, RSSI and range numbers from board #1 (reference values) are
only a pre-tuning baseline.

### Rework log

Hand-modified boards are marked `A*` (see the root README).

| Board | Date | Change | Reason |
|---|---|---|---|
| RF test | 2026-10-23 | No MCU, C8 or L1. J1 (U.FL) fitted, one 15 pF series bridged, L2 = 3.3 nH, 2.0 pF on the L3 pads | Antenna matching with a VNA |
| RF test | 2026-10-26 | Battery connector fitted, L2 = 4.3 nH, 2.1 pF on the L3 pads | Re-match with the battery connector |

Known issues to fix in rev B are listed at the end of [`BRINGUP.md`](../../firmware/C23/BRINGUP.md#notes-for-rev-b).

## CC2340R5 design resources

There is no CC2340 part in the official KiCad library and no TI equivalent of Nordic's
KiCad design blocks, so the design blocks table is empty for now.

| Resource | Format | Link |
|---|---|---|
| CC2340R5 symbol + footprint + STEP (RGE VQFN-24 4x4) | KiCad v6+ export via Ultra Librarian (free login) | https://vendor.ultralibrarian.com/TI/embedded/?gpn=CC2340R5&package=RGE&pin=24 |
| LP-EM-CC2340R53 LaunchPad design files (uses the 40-pin RKP package, but the RF, crystal and DC/DC circuits carry over) | Allegro/OrCAD + schematic/layout PDF, BOM, Gerbers, ODB++ | https://www.ti.com/lit/zip/SWRC397 |
| LP-EM-CC2340R53 user guide | PDF | https://www.ti.com/lit/pdf/SWRU637 |
| CC234x/CC27xx hardware configuration & PCB design (SWRA834) | PDF | https://www.ti.com/lit/pdf/SWRA834 |
| Product page (packages, docs) | Web | https://www.ti.com/product/CC2340R5 |

### CC2340R5 part in the `BSN-C23` library

| Part | Symbol | Footprint | 3D model |
|---|---|---|---|
| CC2340R52E0RGER (VQFN-24 4x4) | `CC2340R52E0RGER` | `Texas_RGE0024B_VQFN-24-1EP_4x4mm_P0.5mm_EP2.45x2.45mm_ThermalVias` | `Texas_RGE0024H_VQFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm.step` |

These were made here from the datasheet and KiCad's stock library rather than downloaded:

- **Symbol:** drawn from the datasheet (SWRS272F), Figure 6-2 and Tables 6-1 to 6-13. The exposed pad is pin 25 (GND).
- **Footprint:** KiCad's stock `VQFN-24-1EP_4x4mm_P0.5mm_EP2.45x2.45mm_ThermalVias`, renamed. It matches TI's RGE0024B land pattern (2.45 mm pad, 9 vias on a 0.975 mm grid). The signal pads are 0.775 mm long versus 0.6 mm in TI's example.
- **3D model:** KiCad has no STEP file for the 2.45 mm pad version. This one is the TI RGE0024H body, which is identical apart from a 2.7 mm exposed pad hidden under the package.