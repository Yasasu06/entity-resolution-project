import F1Chart from "./F1Chart";
import { BENCHMARK, CI, ERRORS, HEADLINE, HUMAN, SWAP, WINDOWS } from "../data/facts";
import { Eyebrow, Reveal } from "./ui";

const C = { signal: "var(--color-signal)", alarm: "var(--color-alarm)", hold: "var(--color-hold)", line: "var(--color-line)",
  dim: "var(--color-dim)", faint: "var(--color-faint)", cool: "var(--color-cool)" };

function Box({ children }) {
  return (
    <div className="rounded-xl bg-panel px-5 py-5 ring-1 ring-line sm:px-6 sm:py-6">{children}</div>
  );
}

function Benchmark() {
  const max = Math.max(...BENCHMARK.rows.map((r) => r.f1));
  return (
    <Box>
      <div className="font-mono text-[0.8125rem] uppercase tracking-[0.09em] text-faint">
        The same matcher, scored the way the literature scores
      </div>
      <p className="mt-4 max-w-[62ch] text-sm leading-relaxed text-dim">
        The {HEADLINE.f1}% above is measured under this project&rsquo;s own protocol: its own
        blocking, all three splits, and one match per record. Published results use the
        benchmark&rsquo;s candidate pairs, the test split alone, and judge each pair
        independently. Those numbers cannot be set side by side, so the matcher was rerun
        under the benchmark&rsquo;s rules instead. It scores{" "}
        <span className="tnum font-medium text-ink">{BENCHMARK.rows.find((r) => r.ours).f1}%</span>.
      </p>

      <div className="mt-7 flex flex-col gap-3">
        {BENCHMARK.rows.map((r) => (
          <div key={r.name} className="flex items-center gap-3">
            <div className={`w-28 shrink-0 text-sm ${r.ours ? "text-ink" : "text-dim"}`}>
              {r.name}
            </div>
            <div className="h-7 flex-1 overflow-hidden rounded-[3px] bg-raised ring-1 ring-line">
              <div
                className={`h-full ${r.ours ? "bg-signal" : "bg-cool-tint"}`}
                style={{ width: `${(r.f1 / max) * 100}%` }}
              />
            </div>
            <div className={`w-14 shrink-0 text-right font-display tnum text-base ${r.ours ? "text-signal" : "text-dim"}`}>
              {r.f1.toFixed(2)}
            </div>
            <div className={`w-32 shrink-0 text-right font-mono text-[0.68rem] ${r.ours ? "text-ink" : "text-faint"}`}>
              <div>{r.labels}</div>
              {r.verdict && (
                <div className={r.verdict === "tied, within noise" ? "text-hold" : "text-faint"}>
                  {r.verdict}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <p className="mt-6 max-w-[62ch] text-sm leading-relaxed text-dim">
        On 2,049 pairs holding 193 matches, that figure carries a 95% interval of{" "}
        <span className="tnum text-ink">[{CI.benchmark[0]}, {CI.benchmark[1]}]</span>, which
        contains DeepMatcher&rsquo;s 53.80. The honest reading is{" "}
        <span className="text-ink">clearly above Magellan, clearly below Ditto, and
        statistically indistinguishable from DeepMatcher</span>. An earlier version of this
        page ranked it 2.42 points below DeepMatcher, which the data does not support.
        The three published systems each train on 60% of the labels. This one has never
        read one except to measure. That narrows the gap. It does not turn it into a win.
      </p>
      <p className="mt-3 max-w-[62ch] text-sm leading-relaxed text-faint">
        Recall holds at {BENCHMARK.recall}% while precision falls to {BENCHMARK.precision}%,
        which is a threshold in the wrong place rather than a model that cannot rank. The
        benchmark&rsquo;s candidate set is roughly 4,700 times denser than the one the
        threshold was chosen against. Correcting for that analytically recovers most of the
        gap, but the correction needs the answer key to compute, so it is not claimed here.
      </p>
    </Box>
  );
}

function Chosen() {
  return (
    <Box>
      <div className="font-mono text-[0.8125rem] uppercase tracking-[0.09em] text-faint">
        How the reported configuration was chosen
      </div>
      <h3 className="mt-4 max-w-[30ch] font-display text-[clamp(1.5rem,3vw,2.25rem)] leading-tight tracking-[-0.015em]">
        The bar was set before the numbers existed.
      </h3>

      <p className="mt-6 max-w-[62ch] text-[0.95rem] leading-relaxed text-dim">
        One condition was committed in writing beforehand: a change would be adopted only if it
        reduced the count of accepted pairs whose products have no counterpart in the other
        catalogue.
      </p>
      <p className="mt-4 max-w-[62ch] text-[0.95rem] leading-relaxed text-dim">
        Measurement then produced a configuration scoring{" "}
        <span className="tnum font-medium text-ink">{SWAP.f1}% F1</span> against{" "}
        <span className="tnum font-medium text-ink">{HEADLINE.f1}%</span>. It reaches that score by
        accepting {SWAP.acceptGrowth}% more pairs &mdash;{" "}
        <span className="tnum">{SWAP.accepted.toLocaleString()}</span> rather than{" "}
        <span className="tnum">{HEADLINE.accepted.toLocaleString()}</span> &mdash; which catches more
        genuine matches and more that are not genuine. The group the condition named moved from{" "}
        <span className="tnum">{SWAP.noPartnerBefore}</span> to{" "}
        <span className="tnum font-medium text-alarm">{SWAP.noPartnerAfter}</span>, and precision from{" "}
        <span className="tnum">{HEADLINE.precision}%</span> to{" "}
        <span className="tnum">{SWAP.precision}%</span>.
      </p>

      <p className="mt-4 max-w-[62ch] text-[0.95rem] leading-relaxed">
        <span className="text-ink">The condition had already been written. This site reports the
        configuration that met it.</span>{" "}
        <span className="text-dim">Entity resolution feeds catalogues, billing and identity systems,
        where a confident wrong answer travels further than a missed one.</span>
      </p>
    </Box>
  );
}

function LabelValue() {
  const rows = [
    { l: "12 labels, chosen by score", v: 4.06, tone: "bg-alarm-tint", ring: "ring-alarm/30" },
    { l: "no labels at all", v: 47.54, tone: "bg-raised", ring: "ring-line2" },
    { l: "12 labels, chosen at the boundary", v: 60.94, tone: "bg-signal-tint", ring: "ring-signal/40" },
  ];
  const max = 70;
  return (
    <Box>
      <div className="font-mono text-[0.8125rem] uppercase tracking-[0.09em] text-faint">
        What labels would have bought
      </div>
      <p className="mt-4 max-w-[62ch] text-[0.95rem] leading-relaxed text-dim">
        The standing objection to building without labels is that labels are cheap: the two most used
        open-source tools reach production quality from thirty or forty hand-labelled pairs. That was
        measured rather than argued.{" "}
        <span className="text-ink">Twelve labels are worth either &minus;43 F1 points or +13,
        depending entirely on which twelve pairs are labelled.</span>
      </p>

      <div className="mt-7 flex flex-col gap-2.5">
        {rows.map((r) => (
          <div key={r.l} className="flex items-center gap-3">
            <div className="w-[15rem] shrink-0 text-sm text-dim">{r.l}</div>
            <div className="h-7 flex-1 overflow-hidden rounded-[3px] bg-raised ring-1 ring-line">
              <div className={`h-full ${r.tone}`} style={{ width: `${(r.v / max) * 100}%` }} />
            </div>
            <div className="w-12 shrink-0 text-right font-display tnum text-base">{r.v}</div>
          </div>
        ))}
      </div>

      <p className="mt-7 max-w-[62ch] text-[0.95rem] leading-relaxed text-dim">
        A threshold is a decision about where to <span className="text-ink">stop</span> accepting,
        and it cannot be learned from a sample that is almost entirely accepts. Ranking by score
        finds matches efficiently and leaves two negatives in twelve. Querying near the decision
        boundary leaves eleven. Both runs stay inside a fixed six-comparison model, so the ceiling
        near 70 belongs to that model rather than to supervision in general.
      </p>
    </Box>
  );
}

function ReviewTier() {
  return (
    <Box>
      <div className="font-mono text-[0.8125rem] uppercase tracking-[0.09em] text-faint">
        What routing to a person actually recovers
      </div>
      <h3 className="mt-4 max-w-[30ch] font-display text-[clamp(1.5rem,3vw,2.25rem)] leading-tight tracking-[-0.015em]">
        The review tier, measured rather than assumed.
      </h3>

      <p className="mt-6 max-w-[62ch] text-[0.95rem] leading-relaxed text-dim">
        The architecture sends <span className="tnum">{HUMAN.queue.toLocaleString()}</span>{" "}
        uncertain records to human review. How much that recovers had been modelled and never
        measured, so one reviewer worked <span className="tnum">{HUMAN.reviewed}</span> of them at
        about a minute each.
      </p>
      <p className="mt-4 max-w-[62ch] text-[0.95rem] leading-relaxed text-dim">
        They found <span className="tnum font-medium text-ink">{HUMAN.recall}%</span> of the matches
        that were present, above what was predicted in advance. On records where no match existed,
        they identified one anyway <span className="tnum font-medium text-ink">{HUMAN.falseMatch}%</span>{" "}
        of the time. At queue scale those rates recover{" "}
        <span className="tnum font-medium text-signal">{HUMAN.recovered}</span> genuine matches and
        introduce <span className="tnum font-medium text-alarm">{HUMAN.introduced}</span>, giving the
        review tier&rsquo;s output a precision of{" "}
        <span className="tnum">{HUMAN.tierPrecision}%</span> alongside the automated tier&rsquo;s{" "}
        <span className="tnum">{HUMAN.autoPrecision}%</span>.
      </p>
      <p className="mt-4 max-w-[62ch] text-[0.95rem] leading-relaxed text-dim">
        This is a property of the task rather than the reviewer. Shown a shortlist of plausible
        candidates and asked whether one of them matches, the shortlist is persuasive &mdash; and{" "}
        <span className="tnum">{HUMAN.noneCorrect}%</span> of the time the accurate answer is that
        none of them does.
      </p>
      <p className="mt-4 max-w-[62ch] text-[0.95rem] leading-relaxed">
        <span className="text-ink">The measurement establishes that the review tier needs its own
        acceptance rule rather than being trusted by construction.</span>{" "}
        <span className="text-dim">The earlier model assumed a single uniform error rate across
        every record; the reviewer is strongly asymmetric between records that have a match and
        records that do not, which no single rate represents.</span>
      </p>
    </Box>
  );
}

function ArrivalWindows() {
  const lo = 59.0, hi = 62.0;
  const pos = (f1) => ((f1 - lo) / (hi - lo)) * 100;
  return (
    <Box>
      <div className="font-mono text-[0.8125rem] uppercase tracking-[0.09em] text-faint">
        Reciprocity under bounded arrival
      </div>
      <h3 className="mt-4 max-w-[32ch] font-display text-[clamp(1.5rem,3vw,2.25rem)] leading-tight tracking-[-0.015em]">
        What the matcher measures when it cannot see every record.
      </h3>

      <p className="mt-6 max-w-[62ch] text-[0.95rem] leading-relaxed text-dim">
        Three stages of the decision rule read one record at a time: the accept threshold, the
        margin against the runner-up, and the quantity veto. One stage reads across records. It
        asks whether a candidate&rsquo;s own highest-scoring record is the record being judged,
        which requires the other records to be available.
      </p>
      <p className="mt-4 max-w-[62ch] text-[0.95rem] leading-relaxed text-dim">
        The same trained model and the same thresholds were run with that stage given a bounded
        window of arrivals, from a single record up to the full{" "}
        <span className="tnum">2,554</span>.
      </p>

      <div className="mt-8 flex flex-col gap-2">
        <div className="flex items-center gap-3 font-mono text-[0.72rem] text-faint">
          <span className="w-16 shrink-0 text-right">window</span>
          <span className="flex-1">F1 across {lo.toFixed(1)} to {hi.toFixed(1)}</span>
          <span className="w-12 shrink-0 text-right">F1</span>
          <span className="w-16 shrink-0 text-right">accepted</span>
        </div>
        {WINDOWS.rows.map((r) => (
          <div key={r.w} className="flex items-center gap-3">
            <div className={`w-16 shrink-0 text-right font-mono text-[0.78rem] tnum ${r.batch ? "text-ink" : "text-dim"}`}>
              {r.w.toLocaleString()}
            </div>
            <div className="h-6 flex-1 overflow-hidden rounded-[3px] bg-raised ring-1 ring-line">
              <div className={`h-full ${r.batch ? "bg-signal" : "bg-cool-tint"}`}
                   style={{ width: `${Math.max(pos(r.f1), 1)}%` }} />
            </div>
            <div className={`w-12 shrink-0 text-right font-display tnum text-sm ${r.batch ? "text-signal" : "text-dim"}`}>
              {r.f1.toFixed(2)}
            </div>
            <div className="w-16 shrink-0 text-right font-mono text-[0.72rem] tnum text-faint">
              {r.accepted.toLocaleString()}
            </div>
          </div>
        ))}
      </div>

      <p className="mt-7 max-w-[62ch] text-[0.95rem] leading-relaxed text-dim">
        At a window of <span className="tnum">250</span> records, a tenth of the population,{" "}
        <span className="tnum">0.18</span> of the{" "}
        <span className="tnum">2.00</span> difference is present. Half of it appears between
        windows of <span className="tnum">500</span> and{" "}
        <span className="tnum">1,000</span>, where the window holds 39% of every record in the
        dataset. The movement is carried by precision, which runs from{" "}
        <span className="tnum">56.82%</span> to <span className="tnum">61.17%</span>; the stage
        withholds pairs rather than adding them, and the accepted count falls from{" "}
        <span className="tnum">1,056</span> to <span className="tnum">971</span>.
      </p>
      <p className="mt-4 max-w-[62ch] text-[0.95rem] leading-relaxed text-faint">
        Each window is evaluated independently. A deployment that had emitted a pair could not
        withdraw it when a later record arrived, and that constraint is not modelled here. It is a
        property of the measurement&rsquo;s design.
      </p>
    </Box>
  );
}

export default function Charts() {
  const errTotal = ERRORS.reduce((s, e) => s + e.value, 0);
  return (
    <>
      <Reveal>
        <Eyebrow>The measurements</Eyebrow>
        <h2 className="mt-4 max-w-[28ch] font-display text-[clamp(2rem,4vw,3.25rem)] leading-tight tracking-[-0.015em]">
          Measured completely, and reported with its limits.
        </h2>
        <p className="mt-5 max-w-[62ch] text-dim">
          Six probabilistic comparisons trained by expectation&ndash;maximisation, against a
          five-line token-overlap heuristic tuned to its own optimum. The gap is 6.5&nbsp;points.
        </p>
      </Reveal>

      <div className="mt-10 grid gap-4 lg:grid-cols-5">
        <Reveal className="lg:col-span-3">
          <Box>
            <F1Chart />
            <div className="mt-4 border-t border-line pt-3 font-mono text-[0.7rem] text-faint">
              95% interval, bootstrapped over {HEADLINE.records.toLocaleString()} records:{" "}
              <span className="tnum text-dim">
                {HEADLINE.f1} [{CI.system[0]}, {CI.system[1]}]
              </span>
              {" "}against the baseline&rsquo;s{" "}
              <span className="tnum text-dim">
                {HEADLINE.baselineMatched} [{CI.baseline[0]}, {CI.baseline[1]}]
              </span>. The gap, paired on the same records, is{" "}
              <span className="tnum text-dim">
                +{CI.gap.point} [+{CI.gap.lo}, +{CI.gap.hi}]
              </span>.
            </div>
          </Box>
        </Reveal>

        <Reveal delay={0.08} className="lg:col-span-2">
          <Box>
            <div className="mb-1 font-mono text-[0.8125rem] uppercase tracking-[0.09em] text-faint">
              What the 971 accepted records are
            </div>
            <div className="mb-5 flex items-baseline gap-2">
              <span className="font-display text-5xl leading-none text-alarm tnum">342</span>
              <span className="text-sm text-dim">have no partner at all</span>
            </div>
            <div className="flex h-12 w-full overflow-hidden rounded-md ring-1 ring-line">
              {ERRORS.map((e) => (
                <div key={e.name} style={{ width: `${(e.value / errTotal) * 100}%`, background: C[e.tone] }}
                  title={`${e.name}: ${e.value}`} />
              ))}
            </div>
            <ul className="mt-5 space-y-3">
              {ERRORS.map((e) => (
                <li key={e.name} className="flex items-baseline gap-3">
                  <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: C[e.tone] }} />
                  <span className="flex-1 text-sm text-dim">{e.name}</span>
                  <span className="font-mono tnum text-sm">{e.value}</span>
                </li>
              ))}
            </ul>
            <p className="mt-5 text-sm leading-relaxed text-dim">
              <span className="text-ink">The dominant error is absence, not confusion.</span> Only
              852 of 2,554 records have any partner in the answer key, and 971 were accepted.
            </p>
          </Box>
        </Reveal>
      </div>

      <Reveal delay={0.05}>
        <div className="mt-4"><Benchmark /></div>
      </Reveal>

      <Reveal delay={0.05}>
        <div className="mt-4"><Chosen /></div>
      </Reveal>

      <Reveal delay={0.05}>
        <div className="mt-4"><LabelValue /></div>
      </Reveal>

      <Reveal delay={0.05}>
        <div className="mt-4"><ReviewTier /></div>
      </Reveal>

      <Reveal delay={0.05}>
        <div className="mt-4"><ArrivalWindows /></div>
      </Reveal>

      <Reveal delay={0.12}>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { v: `${HEADLINE.blockingRecall}%`, l: "Blocking recall", s: "961 of 962 kept" },
            { v: `${HEADLINE.precision}%`, l: "Precision", s: "on 971 unattended" },
            { v: `${HEADLINE.recall}%`, l: "Recall", s: "of 962 true matches" },
            { v: HEADLINE.queued.toLocaleString(), l: "Sent to review", s: "not decided alone" },
          ].map((k) => (
            <div key={k.l} className="rounded-xl bg-panel px-5 py-4 ring-1 ring-line">
              <div className="font-display tnum text-3xl leading-none">{k.v}</div>
              <div className="mt-2 font-mono text-[0.8125rem] uppercase tracking-[0.09em] text-faint">{k.l}</div>
              <div className="mt-1 text-xs text-dim">{k.s}</div>
            </div>
          ))}
        </div>
      </Reveal>
    </>
  );
}
