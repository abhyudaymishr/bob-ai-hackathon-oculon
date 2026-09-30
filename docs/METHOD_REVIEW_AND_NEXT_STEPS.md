# Method review and evaluation plan

## What is implemented

- The multigram ranker blends calendar-month frequency, the most recent up-to-12,000 event tokens, and smoothed 1-, 2-, and 3-order location-sequence conditionals. Its weights and smoothing strength are fixed configuration values, not learned hyperparameters.
- Hotspots use a configurable top fraction (currently 10%). This is a ranking definition, not an extreme-value tail estimate. Actual labels use active units; predictions rank the candidate catalogue.
- Logistic comparisons use L2-regularized binary cross-entropy, damped Newton steps, and the Hessian of that regularized loss. Imbalanced labels make accuracy insufficient; imbalance alone does not imply every logistic coefficient is biased toward the majority class.
- The PIN-versus-metro comparison computes exact discrete 1-Wasserstein transport using min-cost flow. It is not entropic/Sinkhorn OT. Other reports use symmetric nearest-neighbor hotspot distance; the two measures answer different questions.
- The multigram evaluator scores each month using only events strictly earlier than that month. The random event split is still not a clean deployment simulation. The logistic comparison fits coefficients over the full training partition, which can include training events later than the target month; lag features alone do not remove that leakage.

## Preserved baseline

The four-dataset explorer, embedded map data, controls, colors, query behavior, and delivered random-split results are preserved. The baseline table is in `README.md` and full metrics in `reports/dataset_comparison.json`. New temporal validation writes separately and must not replace these files silently.

## New evaluation path

`src/delhi_hotspots/evaluate_rolling_origin.py` evaluates a privacy-minimized event table (`date,unit_id`) against an independent static unit catalogue. It reserves the latest 20% of complete observed calendar months (excluding a partial current month) and predicts each month using events dated strictly before that month. It reports hotspot classification, average precision, multiclass location log loss/Brier score, and exact Wasserstein distance. It does not replace or update the saved explorer metrics.

Multiclass log loss/Brier assess the full location probability distribution, not binary hotspot membership. ECE is omitted until there is a well-defined calibrated binary probability target.

## Further extensions (not currently run)

1. Tune seasonal/recent/n-gram weights and smoothing on rolling validation; never tune on final holdout months.
2. Add calibrated binary hotspot probabilities and report Brier/log loss and PR-AUC alongside F1.
3. Add spatial dependence only after defining a defensible adjacency graph or kernel; station points alone do not establish adjacency.
4. Consider hierarchical count models before Hawkes processes. Hawkes triggering requires credible event times and locations; proxy coordinates and sparse records limit identifiability.
5. Treat peaks-over-threshold and topological summaries as research diagnostics requiring stability checks, not automatic replacements for current rankings.

The missing-mobile CSV has no physical event location, so the package retains its temporal series and does not fabricate spatial accuracy or a map hotspot.
