# BSN-C23 soak and spatial log (flat)

Several nodes placed around the user's flat, received by the NINA-W15 on the laptop with
`bsn_scan_nina.py --csv`. Scanner started 2026-11-20 21:07:44 (first CSV row). Check with `python soak_status.py`. The laptop leaves on Mon 2026-11-23 morning, so this
log ends then. The nodes keep running on their cells, a new log file starts when the laptop is back.

## Placement (2026-11-20)

| Address (FC:DE:C5:73:...) | Board | Place | Supply |
|---|---|---|---|
| 2F:4E | A #1 | living room, right window (kitchen side) | CR2032 |
| 2F:77 | A #2 | bedroom, window next to the bed | CR2032 |
| 2F:67 | B #1 | entrance | CR2032 |
| 2F:5A | B #2 | living room, corner right of the door | CR2032 |
| 2F:60 | B #3 | living room, other window, next to the coffee machine | AA pack (saves a fresh CR2032), not part of the battery soak |
| 2F:82 | B #6 | bedroom, other window, next to the desks | CR2032 |
| 2F:5B | B #8 | kitchen, on the shelves above | CR2032 |
| 2F:65 | B #9 | bathroom | CR2032 |

The user gave the first one as "E4". It is taken as 2F:4E (A #1), the only board with a 4 and an E in the address.

## Builds seen in the data (2026-11-20, 21:30)

Packet id rate from the CSV at about 21:30. The soak build (`LOG=0 DRDY=4 RELOAD=0`) gives one id per about 5 s.

- 5.0 to 5.3 s per id: 2F:4E, 2F:77, 2F:5A, 2F:67, 2F:65.
- About 10 s per id: 2F:5B (B #8) and 2F:82 (B #6). This matches the makefile defaults (10 s timer), not the
  soak build.
- About 3.3 s per id: 2F:60 (B #3). Matches no known build, not investigated.
- **B #3, B #6 and B #8 reflashed with the soak build at about 21:55–21:58.** Checked at 22:01: B #6 5.3 s, B #8
  5.1 s, B #3 about 4.8 s per id (ids restart from 0 after the reflash). From then on all eight nodes run the soak
  build. Data before the reflash from these three is on other builds, cut it in the analysis.

## Files

- `soak_2026-11-20.csv`: one row per received advert, no header. Columns: time, address, RSSI (dBm), packet id,
  temperature (°C), RH (%), VDD (V), battery (%).
- `soak_2026-11-20.log`: scanner console output, the loss summary per node is at the end.

## Event sheet

| Time | Event |
|---|---|
| | |
