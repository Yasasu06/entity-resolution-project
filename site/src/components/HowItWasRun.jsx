import { Eyebrow, Reveal } from "./ui";

const STAGES = [
  { n: "01", h: "Sealed", tone: "text-cool", ring: "ring-cool/25",
    p: "The loader refuses to open a labelled split without an explicit override, and the refusal has its own test. Not a promise — a mechanism." },
  { n: "02", h: "Predicted", tone: "text-hold", ring: "ring-hold/25",
    p: "Every threshold, the review interface's display rules, the AI reviewer's exact prompt, and the full list of measurements — fixed in writing, committed, and timestamped into the Bitcoin blockchain." },
  { n: "03", h: "Opened once", tone: "text-signal", ring: "ring-signal/25",
    p: "One pass over all three splits at the end. Nothing was adjusted afterwards. Corrections are added as new entries, never as edits to old ones." },
];

export default function HowItWasRun() {
  return (
    <>
      <Reveal>
        <Eyebrow>How this was run</Eyebrow>
        <h2 className="mt-4 max-w-[20ch] font-display text-[clamp(2.1rem,5vw,3.75rem)] leading-[1.02] tracking-[-0.02em]">
          The answers stayed locked until the end.
        </h2>
        <p className="mt-6 max-w-[58ch] text-lg leading-relaxed text-dim">
          Every claim on this page was written down before anyone could check it. That is what
          makes the next section mean anything.
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
