export const HEADLINE = {
  f1: 60.94, precision: 59.96, recall: 61.95,
  baselineBest: 57.66, baselineMatched: 54.24,
  accepted: 994, queued: 1191, different: 369,
  records: 2554, withPartner: 852, candidates: 564450, crossProduct: 56376996,
  trueMatches: 962, blockingRecall: 99.9,
};

export const PREDICTIONS = [
  { v: "held", claim: "Blocking keeps essentially every true match",
    real: "99.90% recall", detail:
    "961 of 962 true matches survive into the candidate set, and 100% of those in the test split. Blocking was designed and validated on reduction ratio and reachability alone, with no labels." },
  { v: "held", claim: "The prior implies roughly 1,128 matches exist",
    real: "962 actual", detail:
    "λ = 2.0×10⁻⁵ was derived structurally, with no labels, implying about 1,128 matches across 56.4M pairs. The true count is 962, within 17%. This had been the project's longest-running open worry." },
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
    "The model's posteriors summed to 12,941 expected matches against 962 real ones, inflated 13.5 times. The scores are not calibrated probabilities and were never treated as such." },
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
    "859 records had no candidate above p = 0.5. Whether that meant no counterpart exists or the pipeline failed them was registered in advance as unknowable, specifically so neither answer could later be presented as expected. The pipeline was largely right." },
];

export const F1_BARS = [
  { name: "This system", value: 60.94, lead: true },
  { name: "Token-overlap baseline", value: 57.66, lead: false },
  { name: "Baseline, matched coverage", value: 54.24, lead: false },
];

export const ERRORS = [
  { name: "Correct", value: 596, tone: "signal" },
  { name: "Record has no partner", value: 363, tone: "alarm" },
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
    p: "The probes were built by mutating partners of already-accepted pairs, so every probe had a true partner by construction. Both methods therefore missed the dominant failure entirely: records with no partner at all. Only 852 of 2,554 records have one, and the system accepted 994." },
];
