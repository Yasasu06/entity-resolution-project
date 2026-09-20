import { motion } from "motion/react";
import { Eyebrow, Reveal } from "./ui";

const W_REC = { src: "Walmart", id: "A_1607",
  title: ["maxell", "couleur", "series", "ear", "buds", "purple", "maxell", "190238"],
  price: "16.18", brand: "—" };
const A_REC = { src: "Amazon", id: "B_13172",
  title: ["new-purple", "couleur", "series", "ear", "buds", "-", "de6235", "headphones"],
  price: "21.00", brand: "maxell" };
const SHARED = new Set(["couleur", "series", "ear", "buds"]);

const FUNNEL = [
  { n: "56,376,996", l: "possible pairs", s: "text-[clamp(1.9rem,5.2vw,3.4rem)]", tone: "text-ink" },
  { n: "564,450", l: "survive blocking", s: "text-[clamp(1.6rem,4.2vw,2.7rem)]", tone: "text-ink", note: "99.0% removed" },
  { n: "994", l: "accepted unattended", s: "text-[clamp(1.4rem,3.4vw,2.2rem)]", tone: "text-cool" },
  { n: "600", l: "actually correct", s: "text-[clamp(1.3rem,3vw,1.9rem)]", tone: "text-signal" },
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
          Two retailers describe the same pair of earbuds. Nothing links them — no common
          identifier, no matching model number, not even the same brand field filled in.
          A person sees one product in a second. A database sees two unrelated rows.
        </p>
      </Reveal>

      <Reveal delay={0.08}>
        <div className="mt-10 grid gap-3 lg:grid-cols-[1fr_auto_1fr] lg:items-center">
          <Record rec={W_REC} align="left" />
          <div className="flex items-center justify-center py-2 lg:py-0">
            <span className="rounded-full bg-signal/10 px-4 py-1.5 font-mono text-[11px] uppercase tracking-[0.14em] text-signal ring-1 ring-signal/30">
              same product
            </span>
          </div>
          <Record rec={A_REC} align="left" />
        </div>
        <p className="mt-5 max-w-[62ch] text-sm text-faint">
          Four words in common out of thirteen. The model numbers —
          <span className="font-mono text-alarm"> 190238</span> and
          <span className="font-mono text-alarm"> de6235</span> — disagree completely, because
          retailers carry their own catalogue numbers for the same item. Prices differ by 30%.
        </p>
      </Reveal>

      <Reveal delay={0.14}>
        <div className="mt-16 border-t border-line pt-10">
          <div className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">
            Doing that 56 million times
          </div>
          <div className="mt-7 grid gap-x-8 gap-y-7 sm:grid-cols-2 lg:grid-cols-4">
            {FUNNEL.map((f, i) => (
              <motion.div key={f.l} className="relative"
                initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-40px" }}
                transition={{ duration: 0.5, delay: i * 0.09, ease: [0.16, 1, 0.3, 1] }}>
                <div className={`font-display tnum leading-none ${f.s} ${f.tone}`}>{f.n}</div>
                <div className="mt-2.5 font-mono text-[10px] uppercase tracking-[0.14em] text-faint">{f.l}</div>
                {f.note && <div className="mt-1 font-mono text-[10px] text-signal">{f.note}</div>}
                {i < FUNNEL.length - 1 && (
                  <span aria-hidden="true"
                    className="absolute right-[-1.1rem] top-[0.9rem] hidden text-line2 lg:block">→</span>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </Reveal>
    </>
  );
}

function Record({ rec }) {
  return (
    <div className="rounded-xl bg-panel p-5 ring-1 ring-line">
      <div className="flex items-baseline justify-between gap-3">
        <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-faint">{rec.src}</span>
        <span className="font-mono text-[10px] text-faint">{rec.id}</span>
      </div>
      <p className="mt-3 text-[1.02rem] leading-relaxed">
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
