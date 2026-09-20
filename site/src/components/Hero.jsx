import { motion } from "motion/react";
import { HEADLINE } from "../data/facts";
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
          className="mt-7 font-display text-[clamp(2.75rem,7.5vw,6rem)] leading-[0.95] tracking-[-0.02em] max-w-[16ch]"
        >
          We wrote down how our matcher would fail, then checked.
        </motion.h1>

        <motion.p
          custom={2} initial="hidden" animate="show" variants={fade}
          className="mt-8 max-w-[58ch] text-lg leading-relaxed text-dim"
        >
          A record-linkage system built without ever reading a label. Every threshold fixed,
          every design decision argued, and the expected failures documented, all committed
          and independently timestamped before the answer key was opened once, at the end.
        </motion.p>

        <motion.div
          custom={3} initial="hidden" animate="show" variants={fade}
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
    { n: 8, l: "predictions held", tone: "text-signal", ring: "ring-signal/25" },
    { n: 3, l: "failed", tone: "text-alarm", ring: "ring-alarm/25" },
    { n: 1, l: "registered unknowable", tone: "text-faint", ring: "ring-line2" },
  ];
  return (
    <>
      {cells.map((c) => (
        <div key={c.l} className={`flex-1 min-w-[150px] rounded-xl bg-panel px-5 py-4 ring-1 ${c.ring}`}>
          <div className={`font-display tnum text-5xl leading-none ${c.tone}`}>{c.n}</div>
          <div className="mt-2 font-mono text-xs tracking-[0.14em] uppercase text-faint">{c.l}</div>
        </div>
      ))}
      <div className="flex-[1.6] min-w-[240px] rounded-xl bg-panel px-5 py-4 ring-1 ring-line2">
        <div className="flex items-baseline gap-3">
          <span className="font-display tnum text-5xl leading-none">{HEADLINE.f1}%</span>
          <span className="font-mono text-xs text-dim">F1</span>
        </div>
        <div className="mt-2 font-mono text-xs tracking-[0.14em] uppercase text-faint">
          against a five-line heuristic&rsquo;s {HEADLINE.baselineBest}%
        </div>
      </div>
    </>
  );
}
