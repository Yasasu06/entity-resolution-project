import { useEffect } from "react";
import Hero from "./components/Hero";
import Problem from "./components/Problem";
import HowItWasRun from "./components/HowItWasRun";
import Closing from "./components/Closing";
import Ledger from "./components/Ledger";
import Charts from "./components/Charts";
import ReviewTool from "./components/ReviewTool";
import Investigation from "./components/Investigation";
import Method from "./components/Method";
import { Section } from "./components/ui";

const REPO = "https://github.com/Yasasu06/entity-resolution-project";
const GITHUB = "https://github.com/Yasasu06";
const LINKEDIN = "https://www.linkedin.com/in/yasaswidutta/";
const NAV = [
  ["what", "What it does"], ["evidence", "Why believe it"],
  ["measurements", "Measurements"], ["review", "Try it"],
];

export default function App() {
  // A fragment in the URL is resolved by the browser before this app has
  // mounted, so the target section does not exist yet and the page stays at the
  // top. Loading /#measurements landed on the hero. Scrolling once after mount
  // covers it; in-page nav clicks are unaffected because the target exists by
  // then and the browser handles them itself.
  useEffect(() => {
    const id = window.location.hash.slice(1);
    if (!id) return;
    // Re-applied on every frame for roughly half a second rather than once.
    // The document grows as sections below the target render, which moves the
    // target after the first scroll: a single scroll to #measurements landed
    // 86px short. Exiting as soon as two consecutive frames agreed on the
    // height was not enough, because the height settles briefly and then grows
    // again within the first few frames.
    let frames = 0;
    const settle = () => {
      const target = document.getElementById(id);
      if (target) target.scrollIntoView();
      frames += 1;
      if (frames < 36) requestAnimationFrame(settle);
    };
    requestAnimationFrame(settle);
  }, []);

  return (
    <div className="min-h-screen bg-void">
      <nav className="sticky top-0 z-30 border-b border-line bg-void/90 backdrop-blur-[2px]">
        <div className="mx-auto flex max-w-6xl items-center gap-6 overflow-x-auto px-6 py-3">
          <span className="whitespace-nowrap font-mono text-xs font-medium">Before the Answer Key</span>
          <div className="ml-auto flex gap-5">
            {NAV.map(([id, label]) => (
              <a key={id} href={`#${id}`} className="whitespace-nowrap font-mono text-xs text-faint transition hover:text-signal">
                {label}
              </a>
            ))}
          </div>
        </div>
      </nav>

      <Hero />

      {/* 2 - what it does, and the architecture it uses */}
      <Section id="what"><Problem /></Section>

      {/* 3 - why the claims can be believed: the seal, then the ledger it protects */}
      <Section id="evidence">
        <HowItWasRun />
        <div className="mt-24 border-t border-line pt-20"><Ledger /></div>
        <div className="mt-24 border-t border-line pt-20"><Method /></div>
      </Section>

      {/* 4 - every measurement, including the unflattering ones */}
      <Section id="measurements">
        <Charts />
        <div className="mt-24 border-t border-line pt-20"><Investigation /></div>
      </Section>

      <Section id="review"><ReviewTool /></Section>
      <Section id="closing" className="bg-lift"><Closing /></Section>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-12 text-sm text-faint">
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            <a className="text-signal hover:underline" href={REPO}>Source, decision log and pre-registration</a>
            <a className="text-signal hover:underline" href={`${REPO}/blob/main/docs/PREDICTIONS_VS_REALITY.md`}>The full predictions ledger</a>
          </div>
          <p className="max-w-[72ch]">
            Dataset: the dirty Walmart/Amazon benchmark from the Magellan collection. 2,554 and
            22,074 records, 56,376,996 possible pairs, reduced to 564,450 candidates (98.9988%).
            The 60-record human study is observed; full-queue estimates are projections.
          </p>
          <p className="border-t border-line pt-5 text-faint">
            Built by <span className="text-dim">Yasaswi Dutta</span>
            {/* Reviewed 27 September 2026 and kept. This separator measures 1.41
                against the page, below the 4.5 AA threshold for text, and is
                exempt: it carries no information and is hidden from assistive
                technology. The same applies to the arrow in Ledger.jsx. */}
            <span className="mx-2 text-line2" aria-hidden="true">&middot;</span>
            <a href={GITHUB}
               className="text-dim underline decoration-line2 underline-offset-4 transition hover:text-ink hover:decoration-dim">
              GitHub
            </a>
            <span className="mx-2 text-line2" aria-hidden="true">&middot;</span>
            <a href={LINKEDIN}
               className="text-dim underline decoration-line2 underline-offset-4 transition hover:text-ink hover:decoration-dim">
              LinkedIn
            </a>
          </p>
        </div>
      </footer>
    </div>
  );
}
