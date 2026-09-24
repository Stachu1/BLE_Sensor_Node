# nRF54L variant

## ANT-pin matching network

The antenna matching network on the nRF54L05 ANT pin (U1 pin 31) is a
3-section ladder plus two more tuning elements (L5, L6) leading to the
antenna-select junction (AE1 chip antenna / J1 SMA test point):

```
U1.ANT(31) -- L2(2.7n) --o-- L3(3.5n) --o-- L4(3.5n) --o-- L5(7.3n) -- L6(6.7n) -- (AE1 / J1)
                          |              |              |
                         C14(1.5p)      C15(2.0p)      C16(0.3p)
                          |              |              |
                         GND            GND            GND
```

From the nRF54L and antenna datasheets I estimated both the MCU ANT-pin
source impedance and the actual antenna impedance. Worked through on a
Smith chart, stepping from the estimated MCU source impedance through all
8 elements to the antenna:

https://onlinesmithchart.com/?circuit=blackBox_34.1_-40.9_0__seriesInd_2.7_nH_0_0__shortedCap_1.5_pF_0_0_0__seriesInd_3.5_nH_0_0__shortedCap_2_pF_0_0_0__seriesInd_3.5_nH_0_0__shortedCap_0.3_pF_0_0_0__shortedInd_7.3_nH_0_0__seriesInd_6.7_nH_0_0&fSpan=0

## Simplified 3-element equivalent

Considering a simplified network that achieves the same impedance
translation straight from the MCU source to the antenna, without forcing
the trace through 50 Ω partway — down to just 3 components:

https://onlinesmithchart.com/?circuit=blackBox_34.1_-40.9_0__seriesInd_4.2_nH_0_0__shortedCap_0.3_pF_0_0_0__seriesInd_6.7_nH_0_0&fSpan=0

**Caveats:** the 8-element network likely also does 2nd/3rd-harmonic
low-pass filtering for regulatory compliance (FCC/ETSI spurious emissions),
which a bare 3-element network gives up some of; and both circuits above
use idealized lumped components — real inductors/capacitors have
parasitics, and the true MCU/antenna impedances include board parasitics
not captured here. Treat this as a starting point for simulation and bench
(VNA) verification, not a final BOM change.
