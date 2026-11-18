# Tübingen data audit

Checked 16 November 2026 against the pinned snapshot in `configs/pilot-data.json`.
The local files match all 218 recorded SHA-256 hashes. Raw files stay in ignored
`runs/pilot-preparation/raw/`. This audit does not change the 17 pairs already
used in `runs/real-pilot-01/`.

Check mode and `--write` both hash every pinned file before reading pair values.
A changed numeric file with its old hash, a missing file, a duplicate metadata id,
or a nonfinite or negative weight is rejected.

Reproduce the check when the snapshot is present:

```bash
uv run --extra anm python -m causalbridge.discovery.data_audit \
  --snapshot runs/pilot-preparation/raw \
  --manifest configs/pilot-data.json
```

## Rules

A pair is eligible only when all of these hold:

1. Official weight is positive.
2. Both sides are one column, either columns 1 then 2 or columns 2 then 1.
3. Every data line has two finite numbers, with no blank line.
4. There are at least 100 rows, and each column has at least three distinct values.
5. The description does not make the rows a time series, a time index, successive
   days, or a repeated measure of the same units.

The first failing rule is the exclusion reason. Pairs that fail inside a pilot
family stay in that family. They are not moved to test. Eligible groups that
were not used in the pilot are split by shuffling the group names with seed 261:
20 percent go to development, and the rest go to test. There are 15 such groups,
so 3 are development and 12 are test. The shuffle does not use labels or model
output.

## Pilot pairs

Cause column comes from `pairmeta.txt`. Column order in the runtime file is the
original file order. Names match the description. Units stay blank, including
pair 86, whose description states square meters and euros, because the completed
pilot prompts used the frozen names. Pair 23's description says "Weight: Height
in centimeters," so no weight unit was guessed. Pair 56's benchmark cause is the
second column, latitude, not female life expectancy.

| Pair | Group | Weight | Rows | Benchmark direction |
| ---: | --- | ---: | ---: | --- |
| 1 | dwd_stations | 0.166 | 349 | altitude to temperature |
| 2 | dwd_stations | 0.166 | 349 | altitude to precipitation |
| 3 | dwd_stations | 0.167 | 349 | longitude to temperature |
| 4 | dwd_stations | 0.166 | 349 | altitude to sunshine duration |
| 13 | auto_mpg | 0.250 | 392 | displacement to fuel economy |
| 14 | auto_mpg | 0.250 | 392 | horsepower to fuel economy |
| 15 | auto_mpg | 0.250 | 392 | weight to fuel economy |
| 16 | auto_mpg | 0.250 | 392 | horsepower to acceleration |
| 18 | gag_urine | 1.000 | 314 | age to GAG concentration |
| 20 | dwd_stations | 0.166 | 349 | latitude to temperature |
| 21 | dwd_stations | 0.167 | 349 | longitude to precipitation |
| 22 | arrhythmia | 0.333 | 450 | age to height |
| 23 | arrhythmia | 0.333 | 452 | age to weight |
| 24 | arrhythmia | 0.334 | 451 | age to heart rate |
| 56 | undata | 0.083 | 192 | latitude to female life expectancy |
| 86 | kamernet_rent | 1.000 | 666 | apartment size to monthly rent |
| 88 | bone_children | 1.000 | 261 | age to relative spinal density |

The included weight sum is 6.081. DWD stations are six spatially dependent
rows of one family, and the UNdata row is one country cross-section. Those
limitations stay with the pilot result.

## Pairs kept in the pilot families

| Pair | Reason |
| ---: | --- |
| 54 | zero weight, and more than one column |
| 57–63, 74, 75 | eligible, but the UNdata family was already used |
| 64 | blank row in the data file |
| 73 | country-year panel, 1960–2005 |

## Development groups

census_income (pairs 12 and 17), mopex (pair 93), nlschools (pair 99).

## Test groups

abalone, concrete, cpus, janzing_brightness, janzing_mechanics,
janzing_temperature, janzing_voltage, liver_disorders, moffat_ecosystem,
pima_diabetes, solly_soil, spatial_econometrics.

Inside those groups, pair 98 has fewer than 100 rows, pair 105 is not
scalar-scalar, and pairs 89 and 90 repeat the same litterbags on two dates.
Those four stay in their groups and are not eligible rows.

## Ineligible groups

acute inflammations, Armann and Buelthoff, BAFU, environmental, FAO, Old
Faithful, Hipel and McLeod, Janzing weather, Mahecha flux, indoor and outdoor
temperature, NCEP/NCAR, network traffic at the institute, Oswald milk, Schuett
contrast, sunspots, Tarim electricity, traffic counts, Whistler snow, and
Yahoo finance.

Their reasons are zero weight, more than one column, an invalid row, fewer than
three distinct values, or time dependence. No row was dropped or imputed.
