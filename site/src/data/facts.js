export const ORIGINAL = {
  f1: 59.46, precision: 56.82, recall: 62.37,
  accepted: 1056, correct: 600,
};

// D46/D54: the historical, unseeded post-evaluation run. The seeded current
// run is HEADLINE below; historical analyses elsewhere on the page keep the
// data they were actually measured against.
export const HISTORICAL = {
  f1: 61.46, precision: 61.17, recall: 61.75,
  accepted: 971, queued: 1214, correct: 594,
};

export const HEADLINE = {
  f1: 61.47, precision: 61.09, recall: 61.85,
  uSampleSeed: 0,
  baselineBest: 54.46, baselineMatched: 54.24,
  accepted: 974, correct: 595, queued: 1210, different: 370,
  records: 2554, withPartner: 852, candidates: 564450, crossProduct: 56376996,
  trueMatches: 962, blockingRecall: 99.9,
};

// The component swap (D43): a higher F1 that was measured, understood and declined.
export const SWAP = {
  f1: 66.86, precision: 56.14, recall: 82.64, accepted: 1416,
  noPartnerBefore: 342, noPartnerAfter: 590, noPartnerGrowth: 72.5,
  acceptGrowthCurrent: 45, comparatorCurrent: 974,
  acceptGrowthHistorical: 46, comparatorHistorical: 971, comparatorF1: 61.46,
};

// Seeded rerun of D52: reciprocity evaluated within bounded arrival windows.
// Same model and thresholds; only the number of visible records varies.
export const WINDOWS = {
  batchF1: 61.47, batchAccepted: 974,
  rows: [
    { w: 1,    accepted: 1058, precision: 56.81, f1: 59.50, diff: -1.97 },
    { w: 10,   accepted: 1058, precision: 56.81, f1: 59.50, diff: -1.97 },
    { w: 25,   accepted: 1057, precision: 56.86, f1: 59.53, diff: -1.94 },
    { w: 100,  accepted: 1054, precision: 57.02, f1: 59.62, diff: -1.85 },
    { w: 250,  accepted: 1052, precision: 57.13, f1: 59.68, diff: -1.79 },
    { w: 500,  accepted: 1042, precision: 57.68, f1: 59.98, diff: -1.49 },
    { w: 1000, accepted: 1017, precision: 58.90, f1: 60.54, diff: -0.93 },
    { w: 2554, accepted: 974,  precision: 61.09, f1: 61.47, diff: 0.00, batch: true },
  ],
};

// D51: one reviewer worked 60 queued records. Full-queue counts are projections
// obtained by reweighting observed rates, not additional observed decisions.
export const HUMAN = {
  queue: 1214, reviewed: 60, recall: 83.3, falseMatch: 36.7,
  recovered: 175, introduced: 368, tierPrecision: 31.8, autoPrecision: 61.17,
  noneCorrect: 82.7,
};

// Seeded rerun of the D48 record-level bootstrap. The benchmark comparison
// below remains a historical unseeded-model analysis.
export const CI = {
  system: [58.95, 64.09], baseline: [51.50, 56.80],
  gap: { point: 7.23, lo: 4.36, hi: 10.19 },
  benchmark: [46.61, 56.20],
};

// D44: the same matcher scored under the benchmark's own protocol, so the
// number can be set beside published results without comparing unlike things.
export const BENCHMARK = {
  pairs: 2049, matches: 193, density: 9.42,
  precision: 36.44, recall: 87.05,
  rows: [
    { name: "Ditto", f1: 85.69, labels: "60% of labels", verdict: "clearly ahead" },
    { name: "DeepMatcher", f1: 53.80, labels: "60% of labels", verdict: "tied, within noise" },
    { name: "This project", f1: 51.38, labels: "no pair-label training", ours: true },
    { name: "Magellan", f1: 37.40, labels: "60% of labels", verdict: "clearly behind" },
  ],
};

export const PREDICTIONS = [
  { v: "held", claim: "Blocking keeps essentially every true match",
    real: "99.90% recall", detail:
    "961 of 962 true matches survive into the candidate set, and 100% of those in the test split. After the documented boundary, blocking was designed using reduction ratio and reachability without label feedback." },
  { v: "held", claim: "The prior implies roughly 1,128 matches exist",
    real: "962 actual", detail:
    "λ = 2.0×10⁻⁵ was derived structurally without label feedback during the later design period, implying about 1,128 matches across 56.4M pairs. The true count is 962, within 17%." },
  { v: "held", claim: "“Confidently different” is our most exposed claim",
    real: "0.5% wrong", detail:
    "The pre-registration named one outcome that would constitute outright failure: a substantial share of the 369 records marked confidently different turning out to have matches. Two did." },
  { v: "held", claim: "Picking the top tied candidate is near a coin flip",
    real: "66.3% vs 53.4%", detail:
    "The project refused to let the system pick the highest-scoring tied candidate, and committed in advance to reporting that decision as wrong if the pick beat chance. It did not, decisively." },
  { v: "held", claim: "Tied groups often hold no correct partner at all",
    real: "present 25.7%", detail:
    "Three quarters of tied groups contain no correct answer, which is why the interface had to make “none of these” a first-class option rather than a fallback." },
  { v: "held", claim: "The display cap costs some true matches",
    real: "11 of 1,129", detail:
    "Capping how many candidates a reviewer sees was recorded as a judgement the label-free data could not settle. It cost eleven records." },
  { v: "held", claim: "The auto-accepted set is unreliable",
    real: "43% wrong", detail:
    "Two independent label-free methods concluded the accepted pairs were unreliable at the level of product identity. 456 of 1,056 were wrong. The finding was published weeks before the answer key was opened." },
  { v: "held", claim: "Aggregate confidence is badly inflated",
    real: "12,941 vs 962", detail:
    "The model's posterior values summed to 12,941 expected matches against 962 real ones, inflated 13.5 times. They are useful ranking signals here, not calibrated probabilities." },
  { v: "failed", claim: "“A threshold will not fix it”",
    real: "56.8% → 75.0%", detail:
    "Precision rises 18 points when the threshold is raised. The reasoning came from planted probes, which measured only near-miss confusion, which is genuinely threshold-invariant. Most wrong accepts fail for a different reason: the record has no partner at all. The decision to keep the threshold still holds on F1; the reasoning did not." },
  { v: "failed", claim: "An AI judge put ~31% of accepts wrong",
    real: "43% were", detail:
    "The independent judge underestimated the error rate. On the subset it actually reviewed, 51.3% were wrong, and of the accepts it positively endorsed only 73.4% were correct. It was useful for finding the failure, not for sizing it." },
  { v: "failed", claim: "A test-only figure would be reported",
    real: "not computable", detail:
    "746 of the 900 records appearing in the test split also appear in train. The benchmark splits pairs; this system decides records. A record-level figure on a pair-level split cannot be computed without double-counting. This is a flaw in a document written before the labels." },
  { v: "open", claim: "Do low-scoring records have partners?",
    real: "4.7% of 859", detail:
    "859 records had no candidate above the model's nominal 0.5 score. Whether that meant no counterpart exists or the pipeline failed them was registered in advance as unknowable, specifically so neither answer could later be presented as expected. The pipeline was largely right." },
];

export const F1_BARS = [
  { name: "This system", value: 61.47, lead: true },
  { name: "Token-overlap baseline", value: 54.46, lead: false },
  { name: "Baseline, matched coverage", value: 54.24, lead: false },
];

export const ERRORS = [
  { name: "Correct", value: 595, tone: "signal" },
  { name: "Record has no partner", value: 344, tone: "alarm" },
  { name: "Wrong partner chosen", value: 35, tone: "hold" },
];

export const STEPS = [
  { k: "Method one", h: "An independent judge",
    p: "A language model decided 704 of the auto-accepted pairs cold, never seeing a score. It disagreed with 31%. Disagreement fell steadily with score, 72.6% in the lowest band against 11.2% in the highest, which is the signature of real signal rather than a capricious judge." },
  { k: "Method two", h: "Planted near-misses",
    p: "Every accepted pair's partner was cloned with exactly one attribute changed, so the clone was definitely a different product. Ground truth by construction, no judgement involved. The clone tied or beat the true partner 49% of the time; the median gap was zero bits." },
  { k: "The mechanism", h: "Overlap cannot see contradiction",
    p: "Every comparison measures token overlap. A mutated token joins the evidence set rather than displacing anything, so the shared evidence is unchanged and the score does not move." },
  { k: "The blind spot", h: "Both methods missed the real failure",
    p: "The probes were built by mutating partners of already-accepted pairs, so every probe had a true partner by construction. Both methods missed the dominant failure: records with no partner. Only 852 of 2,554 records have one, and the historical unseeded policy accepted 971." },
];
