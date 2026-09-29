import { Eyebrow, Reveal } from "./ui";

const ROWS = [
  ["Boundary", "commit 9819d63 · 20 September 2026"],
  ["Proof", "OpenTimestamps proof file included with the repository"],
  ["Record", "55 decision entries · 14 pre-registration sections · 368 tests"],
  ["Original", "59.46% F1 under the pre-registered decision rule"],
  ["Revision", "Mutual-best-match and tie handling adopted after label-informed evaluation"],
];

export default function Method() {
  return (
    <>
      <Reveal>
        <Eyebrow>Evaluation chronology</Eyebrow>
        <h3 className="mt-4 font-display text-[clamp(1.55rem,3vw,2.35rem)] leading-tight tracking-[-0.015em]">
          What was fixed, and when
        </h3>
      </Reveal>

      <div className="mt-10 grid gap-10 lg:grid-cols-2">
        <Reveal>
          <div className="space-y-5 text-dim">
            <p>
              Early train and validation exploration used labels. Later blocking and matching work
              after the documented boundary did not use label feedback for those design decisions.
              The loader requires an explicit override to open labelled splits; tests can use it.
            </p>
            <p>
              The original decision thresholds and evaluation plan were committed before the final
              all-split evaluation. That rule scored 59.46% F1. Later reciprocity and tie-handling
              revisions were chosen with label feedback and have a separate result.
            </p>
            <p className="text-ink">
              The decision log records both the failed pre-evaluation expectations and the
              post-evaluation corrections. Those two stages should be read as different evidence.
            </p>
          </div>
        </Reveal>

        <Reveal delay={0.08}>
          <dl className="divide-y divide-line overflow-hidden rounded-xl ring-1 ring-line">
            {ROWS.map(([k, v]) => (
              <div key={k} className="grid gap-1.5 bg-panel px-5 py-4 sm:grid-cols-[110px_1fr] sm:gap-5">
                <dt className="font-mono text-[0.8125rem] uppercase tracking-[0.09em] text-faint">{k}</dt>
                <dd className="text-sm leading-relaxed">{v}</dd>
              </div>
            ))}
          </dl>
        </Reveal>
      </div>
    </>
  );
}
