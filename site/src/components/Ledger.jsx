import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { PREDICTIONS } from "../data/facts";
import { Eyebrow, Reveal } from "./ui";

const TONE = {
  held: { bar: "bg-signal", txt: "text-signal", label: "held" },
  failed: { bar: "bg-alarm", txt: "text-alarm", label: "failed" },
  open: { bar: "bg-faint", txt: "text-faint", label: "no prediction" },
};

export default function Ledger() {
  const [open, setOpen] = useState(null);
  return (
    <>
      <Reveal>
        <Eyebrow>The ledger</Eyebrow>
        <h2 className="mt-4 font-display text-[clamp(2rem,4vw,3.25rem)] leading-tight tracking-[-0.015em]">
          Predicted blind, then measured
        </h2>
        <p className="mt-5 max-w-[62ch] text-dim">
          Every substantive claim made before the labels were read, against what the answer key
          said. The misses are here because a table showing only successes would be worth nothing.
          Select any row for the detail.
        </p>
      </Reveal>

      <Reveal delay={0.06}>
        <div className="mt-10 flex flex-wrap gap-1.5" aria-hidden="true">
          {PREDICTIONS.map((p, i) => (
            <motion.span key={i}
              initial={{ opacity: 0, scaleY: 0.3 }}
              whileInView={{ opacity: 1, scaleY: 1 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 0.45, delay: i * 0.035, ease: [0.16, 1, 0.3, 1] }}
              onMouseEnter={() => setOpen(i)}
              className={`h-14 flex-1 min-w-[26px] origin-bottom rounded-sm ${TONE[p.v].bar}
                ${open === i ? "opacity-100" : "opacity-45"} transition-opacity`} />
          ))}
        </div>
        <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 font-mono text-xs uppercase tracking-[0.14em] text-faint">
          <span><span className="text-signal">&#9632;</span> 8 held</span>
          <span><span className="text-alarm">&#9632;</span> 3 failed</span>
          <span><span className="text-faint">&#9632;</span> 1 registered unknowable</span>
        </div>
      </Reveal>

      <Reveal delay={0.1}>
        <ul className="mt-8 divide-y divide-line rounded-xl bg-panel/60 ring-1 ring-line overflow-hidden">
          {PREDICTIONS.map((p, i) => {
            const t = TONE[p.v];
            const isOpen = open === i;
            return (
              <li key={i}>
                <button
                  onClick={() => setOpen(isOpen ? null : i)}
                  aria-expanded={isOpen}
                  className="group grid w-full grid-cols-[3px_1fr_auto] items-center gap-4 px-4 py-4 text-left transition hover:bg-raised sm:grid-cols-[3px_1fr_auto_18px] sm:gap-5 sm:px-5"
                >
                  <span className={`h-full min-h-[34px] rounded-full ${t.bar} opacity-70`} />
                  <span className="text-base leading-snug">{p.claim}</span>
                  <span className={`font-mono tnum text-sm ${t.txt} text-right`}>{p.real}</span>
                  <span className="hidden text-faint transition group-hover:text-dim sm:block">
                    <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"
                      style={{ transform: isOpen ? "rotate(180deg)" : "none", transition: "transform .2s" }}>
                      <path d="M2 4.5 6 8.5 10 4.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
                    </svg>
                  </span>
                </button>
                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
                      className="overflow-hidden bg-void/40"
                    >
                      <p className="max-w-[72ch] px-5 pb-5 pt-1 text-sm leading-relaxed text-dim sm:pl-[2.1rem]">
                        {p.detail}
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </li>
            );
          })}
        </ul>
      </Reveal>
    </>
  );
}
