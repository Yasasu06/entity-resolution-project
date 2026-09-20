import { STEPS } from "../data/facts";
import { Eyebrow, Reveal } from "./ui";

export default function Investigation() {
  return (
    <>
      <Reveal>
        <Eyebrow>What went wrong, found before checking</Eyebrow>
        <h2 className="mt-4 font-display text-[clamp(2rem,4vw,3.25rem)] leading-tight tracking-[-0.015em]">
          The investigation
        </h2>
        <p className="mt-5 max-w-[62ch] text-dim">
          The system&rsquo;s central weakness was found, measured and published while the labels
          were still sealed — by two methods that needed no ground truth, and a third finding
          that neither could see.
        </p>
      </Reveal>

      <div className="mt-12 grid gap-10 lg:grid-cols-[1.15fr_0.85fr]">
        <ol className="relative space-y-8 border-l border-line pl-7">
          {STEPS.map((s, i) => (
            <Reveal key={s.h} delay={i * 0.06}>
              <li className="relative">
                <span className="absolute -left-[2.05rem] top-1.5 h-2.5 w-2.5 rounded-full bg-cool ring-4 ring-void" />
                <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-cool">{s.k}</div>
                <h3 className="mt-1.5 text-lg font-medium">{s.h}</h3>
                <p className="mt-2 max-w-[60ch] text-sm leading-relaxed text-dim">{s.p}</p>
              </li>
            </Reveal>
          ))}
        </ol>

        <div className="space-y-4">
          <Reveal delay={0.1}>
            <div className="rounded-xl bg-panel p-5 ring-1 ring-line">
              <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-faint">
                The clearest single error
              </div>
              <div className="mt-4 space-y-2.5 font-mono text-[13px] leading-relaxed">
                <Row k="Walmart" v={<>pny geforce <em className="not-italic text-signal">gt 520</em> 1024mb pcie</>} n="" />
                <Row k="Chosen" v={<>pny <em className="not-italic text-alarm">gt 430</em> 1024mb ddr3</>} n="12.7 bits" />
                <Row k="Correct" v={<>pny nvidia geforce <em className="not-italic text-signal">gt520</em> 1gb</>} n="8.0 bits" />
              </div>
              <p className="mt-4 border-t border-line pt-3 text-sm text-alarm">
                The wrong answer scored higher than the right one.
              </p>
            </div>
          </Reveal>

          <Reveal delay={0.16}>
            <div className="rounded-xl border-l-2 border-cool bg-panel/60 p-5">
              <p className="text-sm leading-relaxed text-dim">
                The error decomposition inverted the project&rsquo;s priorities. Of 456 wrong
                accepts, <span className="text-ink">413</span> were records with no partner and
                only <span className="text-ink">43</span> were cases where a partner existed and
                the wrong one was chosen. Three separate investigations had gone after the 9%.
              </p>
            </div>
          </Reveal>

          <Reveal delay={0.22}>
            <div className="rounded-xl bg-panel p-5 ring-1 ring-line">
              <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-faint">What followed</div>
              <ul className="mt-3 space-y-2.5 text-sm text-dim">
                <li><span className="text-ink">A quantity veto</span> — refusing pairs whose stated capacities contradict. Reaches 1.5% of accepts; that honest figure is reported rather than the 9.6% the probes implied.</li>
                <li><span className="text-ink">A mutual-best-match rule</span> — removed 62 accepts that were wrong 93.5% of the time.</li>
                <li><span className="text-ink">Not a threshold change</span> — tuned with full label access it gained 0.6 F1, a precision-for-recall trade rather than an improvement.</li>
              </ul>
            </div>
          </Reveal>
        </div>
      </div>
    </>
  );
}

function Row({ k, v, n }) {
  return (
    <div className="grid grid-cols-[62px_1fr_auto] items-baseline gap-3">
      <span className="text-faint text-[11px] uppercase tracking-wider">{k}</span>
      <span className="text-ink">{v}</span>
      <span className="tnum text-faint text-[11px]">{n}</span>
    </div>
  );
}
