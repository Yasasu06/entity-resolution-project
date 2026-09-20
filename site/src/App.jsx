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
const NAV = [
  ["problem", "The problem"], ["ledger", "Predictions"], ["result", "Result"],
  ["investigation", "The failure"], ["review", "Try it"],
];

export default function App() {
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
      <Section id="problem"><Problem /></Section>
      <Section id="sealed"><HowItWasRun /></Section>
      <Section id="ledger"><Ledger /></Section>
      <Section id="result"><Charts /></Section>
      <Section id="investigation"><Investigation /></Section>
      <Section id="review"><ReviewTool /></Section>
      <Section id="method"><Method /></Section>
      <Section id="closing" className="bg-base"><Closing /></Section>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-12 text-sm text-faint">
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            <a className="text-signal hover:underline" href={REPO}>Source, decision log and pre-registration</a>
            <a className="text-signal hover:underline" href={`${REPO}/blob/main/docs/PREDICTIONS_VS_REALITY.md`}>The full predictions ledger</a>
          </div>
          <p className="max-w-[72ch]">
            Dataset: the dirty Walmart/Amazon benchmark from the Magellan collection. 2,554 and
            22,074 records, 56,376,996 possible pairs, reduced to 564,450 candidates. Every figure
            on this page is measured, not illustrative.
          </p>
        </div>
      </footer>
    </div>
  );
}
