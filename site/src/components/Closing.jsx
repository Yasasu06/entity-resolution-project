import { Reveal } from "./ui";

export default function Closing() {
  return (
    <Reveal>
      <p className="font-mono text-[0.8125rem] uppercase tracking-[0.11em] text-faint">What this shows</p>
      <h2 className="mt-6 max-w-[24ch] font-display text-[clamp(2.2rem,5.6vw,4.25rem)] leading-[1.02] tracking-[-0.022em]">
        Unattended output is not production-ready. The record of establishing that is the result.
      </h2>
      <div className="mt-10 grid gap-8 lg:grid-cols-2">
        <p className="max-w-[56ch] text-lg leading-relaxed text-dim">
          61.17% precision on unattended output is not something to ship unattended, which is why
          1,214 records go to a person instead. Every figure on this page carries its interval and
          its error profile, because stating the limits beside a number rather than after it is the
          only thing that makes the number worth reading.
        </p>
        <p className="max-w-[56ch] text-lg leading-relaxed text-dim">
          Every material weakness was found, measured and published <span className="text-ink">before</span> the
          answer key was opened, and the analysis written while blind turned out to be
          <span className="text-signal"> conservative</span> about the failure, not defensive of it.
          That is harder to fake than a good score.
        </p>
      </div>
    </Reveal>
  );
}
