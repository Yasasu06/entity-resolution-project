import { Reveal } from "./ui";

export default function Closing() {
  return (
    <Reveal>
      <p className="font-mono text-xs uppercase tracking-[0.18em] text-faint">What this shows</p>
      <h2 className="mt-6 max-w-[24ch] font-display text-[clamp(2.2rem,5.6vw,4.25rem)] leading-[1.02] tracking-[-0.022em]">
        The system is not deployable. The record of finding that out is the result.
      </h2>
      <div className="mt-10 grid gap-8 lg:grid-cols-2">
        <p className="max-w-[56ch] text-lg leading-relaxed text-dim">
          59.96% precision on unattended output is not something you ship. The page says so in its
          first screen, because pretending otherwise would waste the only thing this project
          actually built: a method that catches its own mistakes.
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
