import { motion } from "motion/react";

export function Reveal({ children, delay = 0, className = "" }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.5, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
}

export function Eyebrow({ children }) {
  return (
    <div className="font-mono text-[11px] tracking-[0.18em] uppercase text-faint">
      {children}
    </div>
  );
}

export function Section({ id, children, className = "" }) {
  return (
    <section id={id} className={`border-t border-line ${className}`}>
      <div className="mx-auto max-w-6xl px-6 py-24 sm:py-32">{children}</div>
    </section>
  );
}

export function Stat({ value, label, tone = "ink", size = "lg" }) {
  const tones = { ink: "text-ink", signal: "text-signal", alarm: "text-alarm", dim: "text-dim" };
  const sizes = { lg: "text-5xl sm:text-6xl", md: "text-4xl", sm: "text-2xl" };
  return (
    <div className="flex flex-col gap-1.5">
      <div className={`font-display tnum leading-none ${sizes[size]} ${tones[tone]}`}>{value}</div>
      <div className="font-mono text-[11px] tracking-[0.14em] uppercase text-faint">{label}</div>
    </div>
  );
}
