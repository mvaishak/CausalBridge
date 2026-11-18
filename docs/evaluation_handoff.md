# Frozen evaluation handoff

Frozen before further ANM changes. This does not start a model run, does not
change the 17 pilot pairs, and does not replace the exploratory threshold 0.001.

The machine-readable case list is `configs/evaluation-roster.json`.

## Who holds which bundle

Faizah holds the committed case list, the scorer, the diagnosis checker, and the
raw Tübingen snapshot on this machine at `runs/pilot-preparation/raw/`. That
snapshot is gitignored. Its 218 file hashes are in `configs/pilot-data.json`,
and the same files can be downloaded again with the command below.

Faizah does not hold `runs/real-pilot-01/`. That directory is absent from this
checkout and was never committed. The commit that first records it is `a8ba5ba`
by Vaishak (`mvaishak`). Kris owns the live runner and the model server. Anish
needs that directory from Vaishak when the saved pilot requests, generations, or
margins are required. The roster and the reproduction commands below do not
depend on it.

## Validation code and artifacts

| Piece | Path |
| --- | --- |
| Case list, truth, scorability, and pass rules | `configs/evaluation-roster.json` |
| Roster builder | `src/causalbridge/evaluation/roster.py` |
| Weighted scorer | `src/causalbridge/evaluation/scoring.py` |
| Diagnosis and ANM receipt checks | `src/causalbridge/evaluation/diagnosis.py` |
| Original ANM request check | `src/causalbridge/discovery/anm.py` (`load_anm_artifacts`) |
| Frozen source manifest | `configs/pilot-data.json` |
| Pilot preparation and scoring commands | `docs/pilot_run.md` |

## Reproduction

```bash
uv sync --frozen --dev --extra anm
mkdir -p runs/pilot-preparation/raw
curl --fail --location https://webdav.tuebingen.mpg.de/cause-effect/pairs.zip \
  -o runs/pilot-preparation/pairs.zip
unzip -n -j runs/pilot-preparation/pairs.zip -d runs/pilot-preparation/raw
uv run --extra anm python -m causalbridge.evaluation.roster \
  --snapshot runs/pilot-preparation/raw \
  --manifest configs/pilot-data.json \
  --roster configs/evaluation-roster.json
uv run --extra anm python -m causalbridge.discovery.loader \
  --snapshot runs/pilot-preparation/raw \
  --manifest configs/pilot-data.json \
  --output runs/pilot-preparation/prepared
uv run --extra anm pytest tests/test_evaluation_roster.py tests/test_pilot_scoring.py tests/test_pilot_diagnosis.py -q
```

The roster command fails if a pinned file changed. Do not refresh the hashes to
make it pass. The loader writes the 17 pilot runtime pairs and their private
evaluator records. It does not put development or validation labels into the
runtime file.

On the machine that has the live bundle, score and diagnose only after inference:

```bash
uv run --extra anm python -m causalbridge.evaluation.scoring \
  --analysis runs/real-pilot-01/analysis.jsonl \
  --evaluator runs/pilot-preparation/prepared/evaluator/records.json \
  --mapping runs/real-pilot-01/evaluation_mapping.json \
  --output runs/real-pilot-01/pilot-scores.json
uv run --extra anm python -m causalbridge.evaluation.diagnosis \
  --analysis runs/real-pilot-01/analysis.jsonl \
  --evaluator runs/pilot-preparation/prepared/evaluator/records.json \
  --mapping runs/real-pilot-01/evaluation_mapping.json \
  --anm-root runs/real-pilot-01/anm \
  --output runs/real-pilot-01/diagnosis.json
```

## Development and validation cases

`anm_use` is the rule for an ANM change. Source groups are not split across roles.

| `anm_use` | Pairs | What Anish may do |
| --- | ---: | --- |
| `development` | 4 | Inspect these and choose a later change or threshold here |
| `validation` | 38 | Leave these untouched until the change is frozen |
| `frozen_pilot` | 17 | Do not retune on these. The live run already used them |
| `not_scorable` | 49 | Keep them out of every denominator |

Development pairs are census income 12 and 17, mopex 93, and nlschools 99.

Validation pairs are the eligible pairs in abalone, concrete, cpus,
janzing_brightness, janzing_mechanics, janzing_temperature, janzing_voltage,
liver_disorders, moffat_ecosystem, pima_diabetes, solly_soil, and
spatial_econometrics. Pairs 89, 90, 98, and 105 stay inside test groups and are
`not_scorable`.

## Truth and scorability

`reference_direction` is the benchmark cause, in original file order.
`first_to_second` means columns 1 then 2. `second_to_first` means columns 2
then 1. A pair with any other column layout has no direction.

`scorable` is true only for a pilot, development, or validation pair with a
direction, a positive finite weight, and no exclusion reason. An analysis row
is a separate label: `prediction_scorable` must be true before a released
direction counts. A released direction with `prediction_scorable` false is an
error, not an abstention.

## Metrics and pass criteria

These are the agreed definitions. There is no numeric accuracy bar. The pilot's
40.0% weighted selective accuracy is a finding, not a target.

| Metric | Definition |
| --- | --- |
| Weighted coverage | Released weight / total weight |
| Correct-answer yield | Correct released weight / total weight |
| Wrong-answer yield | Wrong released weight / total weight |
| Selective accuracy | Correct released weight / released weight, or null when nothing is released |

A later ANM change is eligible for a validation score only when all of these hold:

1. The change and its threshold were chosen without the 17 pilot outcomes and without the 38 validation pairs.
2. Every scorable pair in the scored split stays in the denominator.
3. The margin equals `score_ba - score_ab`, and the arrow follows that margin and the declared threshold.
4. The original request, configuration, and case binding still verify.
5. The report states coverage, both yields, selective accuracy, and the total weight.

Selective accuracy alone is not a pass. A process check is not a statement that the direction is causal.
