import { motion } from "motion/react";
import { F1_BARS, HEADLINE } from "../data/facts";

// Hand-drawn so the page does not carry a charting library for three bars.
const W = 640, H = 196;
const X0 = 186, X1 = 556;        // plot area
const BAR_H = 26, GAP = 20, TOP = 16;
const AXIS_Y = TOP + F1_BARS.length * (BAR_H + GAP) + 6;
const scale = (v) => X0 + (v / 100) * (X1 - X0);
const TICKS = [0, 25, 50, 75, 100];

export default function F1Chart() {
  return (
    <figure className="m-0">
      <figcaption className="mb-5 flex items-baseline justify-between gap-4">
        <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-faint">F1 score</span>
        <span className="font-mono text-[11px] text-faint">higher is better</span>
      </figcaption>

      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img"
        aria-label={`F1 comparison. This system ${HEADLINE.f1}. Token-overlap baseline ${HEADLINE.baselineBest}. Baseline at matched coverage ${HEADLINE.baselineMatched}.`}>
        {TICKS.map((t) => (
          <line key={t} x1={scale(t)} x2={scale(t)} y1={TOP - 6} y2={AXIS_Y}
            stroke="#1E242B" strokeWidth="1" />
        ))}

        {F1_BARS.map((d, i) => {
          const y = TOP + i * (BAR_H + GAP);
          const w = scale(d.value) - X0;
          return (
            <g key={d.name}>
              <text x={X0 - 14} y={y + BAR_H / 2} textAnchor="end" dominantBaseline="central"
                fill={d.lead ? "#EEF1F4" : "#96A1AC"} fontSize="12.5"
                fontFamily="Inter, system-ui, sans-serif">
                {d.name}
              </text>
              <rect x={X0} y={y} width={X1 - X0} height={BAR_H} rx="3" fill="#101317" />
              <motion.rect
                x={X0} y={y} height={BAR_H} rx="3"
                fill={d.lead ? "#64E3A1" : "#2B333C"}
                initial={{ width: 0 }}
                whileInView={{ width: w }}
                viewport={{ once: true, margin: "-40px" }}
                transition={{ duration: 0.8, delay: 0.08 * i, ease: [0.16, 1, 0.3, 1] }}
              />
              <text x={scale(d.value) + 12} y={y + BAR_H / 2} dominantBaseline="central"
                fill={d.lead ? "#64E3A1" : "#96A1AC"} fontSize="13"
                fontFamily="JetBrains Mono, ui-monospace, monospace"
                style={{ fontVariantNumeric: "tabular-nums" }}>
                {d.value}
              </text>
            </g>
          );
        })}

        {/* where the baseline tops out, at any threshold */}
        <line x1={scale(HEADLINE.baselineBest)} x2={scale(HEADLINE.baselineBest)}
          y1={TOP - 6} y2={AXIS_Y} stroke="#6A7580" strokeWidth="1" strokeDasharray="3 3" />

        <line x1={X0} x2={X1} y1={AXIS_Y} y2={AXIS_Y} stroke="#1E242B" strokeWidth="1" />
        {TICKS.map((t) => (
          <text key={t} x={scale(t)} y={AXIS_Y + 16} textAnchor="middle" fill="#6A7580"
            fontSize="11" fontFamily="JetBrains Mono, ui-monospace, monospace">
            {t}
          </text>
        ))}
      </svg>

      <p className="mt-4 text-sm text-dim">
        The dashed line marks the baseline&rsquo;s best achievable score, at any threshold.
      </p>
    </figure>
  );
}
