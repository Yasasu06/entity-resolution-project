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
          The measured unattended precision is too low for automatic deployment. Uncertain records
          are routed to a local JSON review queue, and one owner reviewer completed 60 distinct
          records in a terminal study. That does not establish an operating review service.
        </p>
        <p className="max-w-[56ch] text-lg leading-relaxed text-dim">
          The original rule&rsquo;s 59.46% F1 is the pre-registered evaluation. The later policy was
          revised with label feedback, so its higher F1 is a post-evaluation result. The public demo
          uses a fixed snapshot of that policy and reveals the benchmark answer after each choice.
        </p>
      </div>
    </Reveal>
  );
}
