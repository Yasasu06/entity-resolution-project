import { motion } from "motion/react";
import { HEADLINE } from "../data/facts";
import { Eyebrow, Reveal } from "./ui";

const W_REC = { src: "Walmart", id: "A_1607",
  title: ["maxell", "couleur", "series", "ear", "buds", "purple", "maxell", "190238"],
  price: "16.18", brand: "not given" };
const A_REC = { src: "Amazon", id: "B_13172",
  title: ["new-purple", "couleur", "series", "ear", "buds", "-", "de6235", "headphones"],
  price: "21.00", brand: "maxell" };
const SHARED = new Set(["couleur", "series", "ear", "buds"]);

const FUNNEL = [
  { n: "56,376,996", l: "possible pairs", s: "text-[clamp(1.9rem,5.2vw,3.4rem)]", tone: "text-ink" },
  { n: "564,450", l: "survive blocking", s: "text-[clamp(1.6rem,4.2vw,2.7rem)]", tone: "text-ink", note: "98.9988% reduction; 961/962 true-pair recall" },
  { n: HEADLINE.accepted.toLocaleString(), l: "accepted unattended", s: "text-[clamp(1.75rem,3.8vw,2.5rem)]", tone: "text-cool" },
  { n: HEADLINE.correct.toLocaleString(), l: "actually correct", s: "text-[clamp(1.6rem,3.2vw,2.2rem)]", tone: "text-signal" },
];

export default function Problem() {
  return (
    <>
      <Reveal>
        <Eyebrow>The problem</Eyebrow>
        <h2 className="mt-4 max-w-[19ch] font-display text-[clamp(2.1rem,5vw,3.75rem)] leading-[1.02] tracking-[-0.02em]">
          Same product. Two shops. No shared key.
        </h2>
        <p className="mt-6 max-w-[58ch] text-lg leading-relaxed text-dim">
          Two retailers describe the same pair of earbuds. Nothing links them. No common
          identifier, no matching model number, not even the same brand field filled in.
          A person sees one product in a second. A database sees two unrelated rows.
        </p>
      </Reveal>

      <Reveal delay={0.08}>
        <div className="mt-10 grid gap-3 lg:grid-cols-[1fr_auto_1fr] lg:items-center">
          <Record rec={W_REC} align="left" />
          <div className="flex items-center justify-center py-2 lg:py-0">
            <span className="rounded-full bg-signal/10 px-4 py-1.5 font-mono text-[0.8125rem] uppercase tracking-[0.09em] text-signal ring-1 ring-signal/30">
              same product
            </span>
          </div>
          <Record rec={A_REC} align="left" />
        </div>
        <p className="mt-5 max-w-[62ch] text-sm text-faint">
          Four words in common out of thirteen. The model numbers,
          <span className="font-mono text-alarm"> 190238</span> and
          <span className="font-mono text-alarm"> de6235</span>, disagree completely, because
          retailers carry their own catalogue numbers for the same item. Prices differ by 30%.
        </p>
      </Reveal>

      <Reveal delay={0.14}>
        <div className="mt-16 border-t border-line pt-10">
          <div className="font-mono text-[0.8125rem] uppercase tracking-[0.16em] text-faint">
            Doing that 56 million times
          </div>
          <div className="mt-7 grid gap-x-8 gap-y-7 sm:grid-cols-2 lg:grid-cols-4">
            {FUNNEL.map((f, i) => (
              <motion.div key={f.l} className="relative"
                initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-40px" }}
                transition={{ duration: 0.5, delay: i * 0.09, ease: [0.16, 1, 0.3, 1] }}>
                <div className={`font-display tnum leading-none ${f.s} ${f.tone}`}>{f.n}</div>
                <div className="mt-2.5 font-mono text-[0.8125rem] uppercase tracking-[0.09em] text-faint">{f.l}</div>
                {f.note && <div className="mt-1 font-mono text-xs text-signal">{f.note}</div>}
                {i < FUNNEL.length - 1 && (
                  <span aria-hidden="true"
                    className="absolute right-[-1.1rem] top-[0.9rem] hidden text-line2 lg:block">→</span>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </Reveal>

      <Reveal delay={0.1}>
        <div className="mt-20 border-t border-line pt-14">
          <h3 className="max-w-[26ch] font-display text-[clamp(1.6rem,3.2vw,2.5rem)] leading-tight tracking-[-0.015em]">
            Three answers, not two: match, reject, or hand it to a person.
          </h3>
          <p className="mt-6 max-w-[62ch] text-lg leading-relaxed text-dim">
            A matcher that must answer every pair will be wrong on the ones it cannot see clearly.
            This system is allowed a third answer, and the hardest cases go to a review queue
            instead of to a guess.
          </p>

          <div className="mt-10 grid gap-4 sm:grid-cols-3">
            {[
              { n: HEADLINE.accepted.toLocaleString(), l: "accepted automatically",
                s: "high enough evidence to commit", tone: "text-signal", ring: "ring-signal/30" },
              { n: HEADLINE.queued.toLocaleString(), l: "routed to local review queue",
                s: "uncertain, so not decided alone", tone: "text-hold", ring: "ring-hold/30" },
              { n: HEADLINE.different.toLocaleString(), l: "rejected outright",
                s: "evidence actively against a match", tone: "text-dim", ring: "ring-line2" },
            ].map((c) => (
              <div key={c.l} className={`rounded-xl bg-panel px-5 py-5 ring-1 ${c.ring}`}>
                <div className={`font-display tnum text-4xl leading-none ${c.tone}`}>{c.n}</div>
                <div className="mt-2 font-mono text-[0.8125rem] uppercase tracking-[0.09em] text-faint">{c.l}</div>
                <p className="mt-2 text-sm leading-relaxed text-dim">{c.s}</p>
              </div>
            ))}
          </div>

          <p className="mt-10 max-w-[62ch] text-base leading-relaxed text-dim">
            That three-way split is not an invention of this project. It is the decision rule
            Fellegi and Sunter set out in{" "}
            <span className="text-ink">A Theory for Record Linkage</span> in 1969, which proved it
            optimal: for fixed limits on false matches and missed matches, routing the uncertain
            middle to clerical review is the rule that leaves the smallest middle. National
            statistical offices and health registries have run on it for over fifty years, and the
            engine underneath this system is an implementation of it.
          </p>
        </div>
      </Reveal>
    </>
  );
}

function Record({ rec }) {
  return (
    <div className="rounded-xl bg-panel p-5 ring-1 ring-line">
      <div className="flex items-baseline justify-between gap-3">
        <span className="font-mono text-[0.8125rem] uppercase tracking-[0.16em] text-faint">{rec.src}</span>
        <span className="font-mono text-xs text-faint">{rec.id}</span>
      </div>
      <p className="mt-3 text-base leading-relaxed">
        {rec.title.map((w, i) => (
          <span key={i} className={SHARED.has(w) ? "text-signal" : "text-ink"}>
            {w}{i < rec.title.length - 1 ? " " : ""}
          </span>
        ))}
      </p>
      <dl className="mt-4 flex gap-7 border-t border-line pt-3 font-mono text-xs">
        <div className="flex gap-2"><dt className="text-faint">brand</dt><dd className="text-dim">{rec.brand}</dd></div>
        <div className="flex gap-2"><dt className="text-faint">price</dt><dd className="text-dim">{rec.price}</dd></div>
      </dl>
    </div>
  );
}
