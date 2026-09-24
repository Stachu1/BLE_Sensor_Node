# BSN-C23 (TI CC2340R5 variant)

KiCad project: `BSN-C23.kicad_pro`. See the root README for the board naming scheme.

## Starting point

This project started as a copy of `BSN-N54-A` (board outline, power, sensors, antenna and
test points). Some parts are still nRF54L-specific and need to be replaced:

- [ ] U1: swap the nRF54L05 for the CC2340R52E0RGER (VQFN-24 4x4, RGE)
- [ ] Decoupling and power tree for the CC2340R5 (DC/DC inductor, VDDS/VDDR caps)
- [ ] 48 MHz HF crystal (the CC2340R5 uses 48 MHz; Y1 is currently the nRF 32 MHz part)
- [ ] RF matching network and filter per the TI CC2340R5 reference design
- [ ] Debug header: SWD pins for the CC2340R5

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

Next step: copy the RF matching network, crystals and DC/DC layout from the SWRC397 LaunchPad files.
