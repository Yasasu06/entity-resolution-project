import F1Chart from "./F1Chart";
import { ERRORS, HEADLINE } from "../data/facts";
import { Eyebrow, Reveal } from "./ui";

const C = { signal: "#64E3A1", alarm: "#F0785A", hold: "#E3C46A", line: "#1E242B",
  dim: "#96A1AC", faint: "#6A7580", cool: "#6BA8F5" };

function Box({ children }) {
  return (
    <div className="rounded-xl bg-panel px-5 py-5 ring-1 ring-line sm:px-6 sm:py-6">{children}</div>
  );
}

export default function Charts() {
  const errTotal = ERRORS.reduce((s, e) => s + e.value, 0);
  return (
    <>
      <Reveal>
        <Eyebrow>The result</Eyebrow>
        <h2 className="mt-4 font-display text-[clamp(2rem,4vw,3.25rem)] leading-tight tracking-[-0.015em]">
          It works, modestly. Not deployably.
        </h2>
        <p className="mt-5 max-w-[62ch] text-dim">
          Six probabilistic comparisons trained by expectation&ndash;maximisation, against a
          five-line token-overlap heuristic tuned to its own optimum. The gap is 3.3&nbsp;points.
        </p>
      </Reveal>

      <div className="mt-10 grid gap-4 lg:grid-cols-5">
        <Reveal className="lg:col-span-3">
          <Box>
            <F1Chart />
          </Box>
        </Reveal>

        <Reveal delay={0.08} className="lg:col-span-2">
          <Box>
            <div className="mb-1 font-mono text-xs uppercase tracking-[0.14em] text-faint">
              What the 994 accepted records are
            </div>
            <div className="mb-5 flex items-baseline gap-2">
              <span className="font-display text-5xl leading-none text-alarm tnum">363</span>
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
              852 of 2,554 records have any partner in the answer key, and 994 were accepted.
            </p>
          </Box>
        </Reveal>
      </div>

      <Reveal delay={0.12}>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { v: `${HEADLINE.blockingRecall}%`, l: "Blocking recall", s: "961 of 962 kept" },
            { v: `${HEADLINE.precision}%`, l: "Precision", s: "on 994 unattended" },
            { v: `${HEADLINE.recall}%`, l: "Recall", s: "of 962 true matches" },
            { v: HEADLINE.queued.toLocaleString(), l: "Sent to review", s: "not decided alone" },
          ].map((k) => (
            <div key={k.l} className="rounded-xl bg-panel px-5 py-4 ring-1 ring-line">
              <div className="font-display tnum text-3xl leading-none">{k.v}</div>
              <div className="mt-2 font-mono text-xs uppercase tracking-[0.14em] text-faint">{k.l}</div>
              <div className="mt-1 text-xs text-dim">{k.s}</div>
            </div>
          ))}
        </div>
      </Reveal>
    </>
  );
}
