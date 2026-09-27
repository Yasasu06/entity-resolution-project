import { motion } from "motion/react";
import { BENCHMARK, CI, HEADLINE } from "../data/facts";
import { Eyebrow } from "./ui";

const fade = {
  hidden: { opacity: 0, y: 18 },
  show: (i) => ({ opacity: 1, y: 0, transition: { duration: 0.65, delay: 0.06 * i, ease: [0.16, 1, 0.3, 1] } }),
};

export default function Hero() {
  return (
    <header className="grain relative overflow-hidden">
      <div className="mx-auto max-w-6xl px-6 pt-20 pb-24 sm:pt-28 sm:pb-32">
        <motion.div custom={0} initial="hidden" animate="show" variants={fade}>
          <Eyebrow>Entity resolution · Walmart × Amazon · 56,376,996 possible pairs</Eyebrow>
        </motion.div>

        <motion.h1
          custom={1} initial="hidden" animate="show" variants={fade}
          className="mt-7 font-display text-[clamp(2.6rem,6.6vw,5.25rem)] leading-[0.97] tracking-[-0.02em] max-w-[24ch]"
        >
          Built without a single labelled example. Measured against systems trained on thousands.
        </motion.h1>

        <motion.p
          custom={2} initial="hidden" animate="show" variants={fade}
          className="mt-8 max-w-[64ch] text-lg leading-relaxed text-dim"
        >
          Under the benchmark&rsquo;s own protocol this system scores{" "}
          <span className="tnum text-ink">{BENCHMARK.rows.find((r) => r.ours).f1} F1
          [{CI.benchmark[0]}, {CI.benchmark[1]}]</span>. DeepMatcher, a supervised deep-learning
          matcher trained on 60% of the labelled data, scores <span className="tnum text-ink">53.80</span>{" "}
          &mdash; inside that interval, so the two are not separated by this measurement. Ditto, the
          transformer state of the art, scores <span className="tnum text-ink">85.69</span> and is
          clearly ahead. The interval is wide because the test split holds 193 matches; every figure
          on this page carries its own, including the unflattering ones.
        </motion.p>

        <motion.p
          custom={3} initial="hidden" animate="show" variants={fade}
          className="mt-5 max-w-[64ch] text-lg leading-relaxed text-dim"
        >
          Twelve predictions about how this would fail were committed and timestamped to the Bitcoin
          blockchain before the answer key was opened. <span className="text-ink">Eight held.</span>
        </motion.p>

        <motion.div
          custom={4} initial="hidden" animate="show" variants={fade}
          className="mt-12 flex flex-wrap items-stretch gap-3"
        >
          <Scorecard />
        </motion.div>
      </div>
    </header>
  );
}

function Scorecard() {
  const cells = [
    { n: 8, l: "predictions held", tone: "text-signal", ring: "ring-signal/30" },
    { n: 3, l: "did not", tone: "text-alarm", ring: "ring-alarm/30" },
    { n: 1, l: "registered unanswerable", tone: "text-faint", ring: "ring-line2" },
  ];
  return (
    <>
      {cells.map((c) => (
        <div key={c.l} className={`flex-1 min-w-[150px] rounded-xl bg-panel px-5 py-4 ring-1 ${c.ring}`}>
          <div className={`font-display tnum text-5xl leading-none ${c.tone}`}>{c.n}</div>
          <div className="mt-2 font-mono text-[0.8125rem] tracking-[0.09em] uppercase text-faint">{c.l}</div>
        </div>
      ))}
      <div className="flex-[1.5] min-w-[230px] rounded-xl bg-panel px-5 py-4 ring-1 ring-signal/30">
        <div className="flex items-baseline gap-2">
          <span className="font-display tnum text-5xl leading-none">{BENCHMARK.rows.find((r) => r.ours).f1}</span>
          <span className="tnum font-mono text-[0.8125rem] text-dim">[{CI.benchmark[0]}, {CI.benchmark[1]}]</span>
        </div>
        <div className="mt-2 font-mono text-[0.8125rem] tracking-[0.09em] uppercase text-faint">
          F1, zero labels &middot; benchmark protocol
        </div>
      </div>
      <div className="flex-[1.5] min-w-[230px] rounded-xl bg-panel px-5 py-4 ring-1 ring-line2">
        <div className="flex items-baseline gap-2">
          <span className="font-display tnum text-5xl leading-none">{HEADLINE.f1}</span>
          <span className="tnum font-mono text-[0.8125rem] text-dim">[{CI.system[0]}, {CI.system[1]}]</span>
        </div>
        <div className="mt-2 font-mono text-[0.8125rem] tracking-[0.09em] uppercase text-faint">
          F1, own protocol
        </div>
      </div>
    </>
  );
}
