import { Eyebrow, Reveal } from "./ui";

const ROWS = [
  ["Boundary", "commit 9819d63 · 20 September 2026"],
  ["Proof", "OpenTimestamps, anchored in the Bitcoin blockchain — controlled by neither the author nor the host"],
  ["Record", "41 decision entries · 10 pre-registration sections · 254 tests"],
  ["Evaluation", "One pass over all three splits, nothing adjusted afterwards"],
];

export default function Method() {
  return (
    <>
      <Reveal>
        <Eyebrow>How it was kept honest</Eyebrow>
        <h2 className="mt-4 font-display text-[clamp(2rem,4vw,3.25rem)] leading-tight tracking-[-0.015em]">
          The seal
        </h2>
      </Reveal>

      <div className="mt-10 grid gap-10 lg:grid-cols-2">
        <Reveal>
          <div className="space-y-5 text-dim">
            <p>
              No labelled data was read until the whole system was finished. That was enforced in
              code, not by intention: the loader refuses to open a labelled split without an
              explicit override, and the refusal has its own test.
            </p>
            <p>
              Every threshold, the review interface&rsquo;s display rules, the AI reviewer&rsquo;s
              exact prompt and model, and the full list of measurements were fixed in a
              pre-registration and committed before the answer key was opened. Corrections are made
              by adding new entries, never by revising old ones.
            </p>
            <p className="text-ink">
              The strongest evidence is not the timestamp. It is that the record documents its own
              system failing — and that the pre-unseal analysis turned out to be conservative about
              that failure rather than defensive of it.
            </p>
          </div>
        </Reveal>

        <Reveal delay={0.08}>
          <dl className="divide-y divide-line overflow-hidden rounded-xl ring-1 ring-line">
            {ROWS.map(([k, v]) => (
              <div key={k} className="grid gap-1.5 bg-panel px-5 py-4 sm:grid-cols-[110px_1fr] sm:gap-5">
                <dt className="font-mono text-[10px] uppercase tracking-[0.14em] text-faint">{k}</dt>
                <dd className="text-sm leading-relaxed">{v}</dd>
              </div>
            ))}
          </dl>
        </Reveal>
      </div>
    </>
  );
}
