import { Eyebrow, Reveal } from "./ui";

const STAGES = [
  { n: "01", h: "Earlier exploration", tone: "text-cool", ring: "ring-cool/25",
    p: "Train and validation labels were inspected early in the project. That history limits any absolute claim that labels were never seen." },
  { n: "02", h: "Original rule fixed", tone: "text-hold", ring: "ring-hold/25",
    p: "After a documented boundary, later blocking and matching choices were made without label feedback. The original decision thresholds and evaluation plan were committed before final evaluation." },
  { n: "03", h: "Evaluated and revised", tone: "text-signal", ring: "ring-signal/25",
    p: "The original rule scored 59.46% F1. Later mutual-best-match and tie changes used evaluation labels; the resulting policy is reported separately." },
];

export default function HowItWasRun() {
  return (
    <>
      <Reveal>
        <Eyebrow>How this was run</Eyebrow>
        <h2 className="mt-4 max-w-[20ch] font-display text-[clamp(2.1rem,5vw,3.75rem)] leading-[1.02] tracking-[-0.02em]">
          The policy has two evaluation histories.
        </h2>
        <p className="mt-6 max-w-[58ch] text-lg leading-relaxed text-dim">
          The original decision rule was fixed before its final evaluation. The later policy uses
          what that evaluation taught, and its result is identified separately throughout this page.
        </p>
      </Reveal>

      <div className="mt-12 grid gap-4 md:grid-cols-3">
        {STAGES.map((s, i) => (
          <Reveal key={s.h} delay={i * 0.08}>
            <div className={`h-full rounded-xl bg-panel p-6 ring-1 ${s.ring}`}>
              <div className={`font-mono text-xs tracking-[0.2em] ${s.tone}`}>{s.n}</div>
              <h3 className={`mt-4 font-display text-3xl leading-none ${s.tone}`}>{s.h}</h3>
              <p className="mt-4 text-sm leading-relaxed text-dim">{s.p}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </>
  );
}
