import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Eyebrow, Reveal } from "./ui";

const FIELDS = ["brand", "modelno", "price", "category"];
const REASON = {
  accept: ["auto-accepted, no review", "text-alarm ring-alarm/30 bg-alarm/10"],
  review_tied: ["queued · tied at the top", "text-hold ring-hold/30 bg-hold/10"],
  review_unsure: ["queued · below the bar", "text-cool ring-cool/30 bg-cool/10"],
  review_not_reciprocal: ["queued · match not mutual", "text-cool ring-cool/30 bg-cool/10"],
  review_quantity_conflict: ["queued · quantities conflict", "text-cool ring-cool/30 bg-cool/10"],
};

export default function ReviewTool() {
  const [cards, setCards] = useState(null);
  const [err, setErr] = useState(false);
  const [i, setI] = useState(0);
  const [picked, setPicked] = useState(null);
  const [res, setRes] = useState(null);
  const [tally, setTally] = useState({ seen: 0, right: 0, held: 0 });

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data.json`)
      .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then((d) => setCards(d.cards))
      .catch(() => setErr(true));
  }, []);

  const c = cards?.[i];
  const shown = useMemo(
    () => (c ? c.blocks.flatMap((b) => b.members.map((m) => m.amazon_id)) : []),
    [c]
  );

  function decide(kind) {
    if (!c || res) return;
    const hasTruth = c.truth.length > 0;
    const shownTruth = c.truthShown.length > 0;
    let ok = false, verdict = "", why = "";
    if (kind === "match") {
      ok = c.truth.includes(picked);
      verdict = ok ? "Correct." : "Not a match.";
      why = ok ? "That pair is in the answer key."
        : hasTruth ? "This record does have a partner — but not that one."
        : "This record has no partner in the answer key at all.";
    } else if (kind === "none") {
      if (!hasTruth) { ok = true; verdict = "Correct."; why = "No partner exists. Two thirds of records have none."; }
      else if (!shownTruth) { ok = true; verdict = "Correct, given what you were shown."; why = "A partner exists, but the display cap cut it from the list. The answer key still scores this wrong — that gap belongs to the interface, not to you."; }
      else { verdict = "There was a match."; why = "The correct partner was on the list."; }
    } else { verdict = "Held."; why = "Recorded as undecided — not counted either way."; }
    setRes({ kind, ok, verdict, why });
    setTally((t) => kind === "cant"
      ? { ...t, held: t.held + 1 }
      : { ...t, seen: t.seen + 1, right: t.right + (ok ? 1 : 0) });
  }

  function next() { setRes(null); setPicked(null); setI((n) => (n + 1) % cards.length); }

  return (
    <>
      <Reveal>
        <Eyebrow>The interactive part</Eyebrow>
        <h2 className="mt-4 font-display text-[clamp(2rem,4vw,3.25rem)] leading-tight tracking-[-0.015em]">
          Try deciding one yourself
        </h2>
        <p className="mt-5 max-w-[62ch] text-dim">
          Real records from the live pipeline, shown through the same interface rules the project
          argued its way to. Decide, then see what the answer key, the AI reviewer and the system
          each said. Tied candidates appear unordered and unnumbered — among them the model
          genuinely cannot tell, and ranking them would invent a preference from row order.
        </p>
      </Reveal>

      <Reveal delay={0.08}>
        <div className="mt-10 overflow-hidden rounded-xl bg-panel ring-1 ring-line2">
          {err && <p className="p-6 text-dim">The sample records could not be loaded.</p>}
          {!err && !c && <p className="p-6 font-mono text-sm text-faint">Loading records…</p>}
          {c && (
            <>
              <div className="flex flex-wrap items-center gap-3 border-b border-line bg-void/40 px-5 py-3.5">
                <span className="rounded-md px-2 py-1 font-mono text-[11px] text-dim ring-1 ring-line2">{c.id}</span>
                <span className={`rounded-md px-2 py-1 font-mono text-[11px] uppercase tracking-wider ring-1 ${REASON[c.outcome][1]}`}>
                  {REASON[c.outcome][0]}
                </span>
                <span className="ml-auto font-mono tnum text-xs text-faint">
                  {tally.seen ? `${tally.right} / ${tally.seen} correct` : "no decisions yet"}
                  {tally.held ? ` · ${tally.held} held` : ""}
                </span>
              </div>

              <div className="border-b border-line px-5 py-5">
                <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-faint">Walmart record</div>
                <p className="mt-2.5 max-w-[64ch] text-[1.02rem] leading-snug">{c.walmart.title}</p>
                <dl className="mt-3 flex flex-wrap gap-x-7 gap-y-1 font-mono text-xs text-dim">
                  {FIELDS.filter((f) => c.walmart[f]).map((f) => (
                    <div key={f} className="flex gap-2">
                      <dt className="text-faint">{f}</dt><dd>{c.walmart[f]}</dd>
                    </div>
                  ))}
                </dl>
              </div>

              <div className="max-h-[520px] space-y-4 overflow-y-auto px-5 py-5">
                {c.blocks.map((b, bi) => (
                  <div key={bi} className={b.tied ? "rounded-lg border border-dashed border-hold/35 bg-hold/[0.04] p-3" : ""}>
                    {b.tied && (
                      <div className="mb-2.5 font-mono text-[10px] uppercase tracking-[0.12em] text-hold">
                        {b.members.length} candidates the evidence cannot separate — no order implied
                        {b.truncated && ` · showing ${b.shown} of ${b.true_size}`}
                      </div>
                    )}
                    <div className="space-y-2">
                      {b.members.map((m) => {
                        const isTruth = res && c.truth.includes(m.amazon_id);
                        const isWrong = res?.kind === "match" && m.amazon_id === picked && !isTruth;
                        return (
                          <button key={m.amazon_id} disabled={!!res}
                            onClick={() => setPicked(m.amazon_id)}
                            className={`flex w-full gap-3 rounded-lg px-3 py-2.5 text-left ring-1 transition
                              ${isTruth ? "bg-signal/10 ring-signal/50"
                                : isWrong ? "bg-alarm/10 ring-alarm/50"
                                : picked === m.amazon_id ? "bg-cool/10 ring-cool/50"
                                : "bg-raised ring-line hover:ring-line2"}`}>
                            <span className="shrink-0 rounded px-1.5 py-0.5 font-mono text-[10px] text-faint ring-1 ring-line">
                              {m.amazon_id}
                            </span>
                            <span className="min-w-0">
                              <span className="block text-sm leading-snug">{m.title}</span>
                              {FIELDS.some((f) => m[f]) && (
                                <span className="mt-1 block font-mono text-[11px] text-faint">
                                  {FIELDS.filter((f) => m[f]).map((f) => `${f} ${m[f]}`).join("  ·  ")}
                                </span>
                              )}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex flex-wrap items-center gap-2.5 border-t border-line bg-void/40 px-5 py-4">
                <button disabled={!picked || !!res} onClick={() => decide("match")}
                  className="rounded-lg bg-signal px-4 py-2 text-sm font-medium text-void transition disabled:opacity-30">
                  Confirm match
                </button>
                <button disabled={!!res} onClick={() => decide("none")}
                  className="rounded-lg px-4 py-2 text-sm ring-1 ring-line2 transition hover:ring-dim disabled:opacity-30">
                  None of these
                </button>
                <button disabled={!!res} onClick={() => decide("cant")}
                  className="rounded-lg px-4 py-2 text-sm ring-1 ring-line2 transition hover:ring-dim disabled:opacity-30">
                  Can&rsquo;t tell
                </button>
                {res && (
                  <button onClick={next} className="ml-auto rounded-lg px-4 py-2 text-sm ring-1 ring-line2 transition hover:ring-dim">
                    Next record →
                  </button>
                )}
              </div>

              <AnimatePresence>
                {res && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                    className="overflow-hidden border-t border-line bg-void/50">
                    <div className="px-5 py-5">
                      <div className={`font-display text-2xl ${res.kind === "cant" ? "text-dim" : res.ok ? "text-signal" : "text-alarm"}`}>
                        {res.verdict}
                      </div>
                      <p className="mt-2 max-w-[64ch] text-sm text-dim">{res.why}</p>
                      <dl className="mt-4 divide-y divide-line overflow-hidden rounded-lg ring-1 ring-line">
                        {[
                          ["Answer key", c.truth.length
                            ? (c.truthShown.length ? `${c.truthShown.join(", ")} — highlighted above` : `${c.truth.join(", ")} — not among the candidates shown`)
                            : "no partner exists for this record"],
                          ["AI reviewer", c.ai
                            ? (c.ai.decision === "match" ? `chose ${c.ai.amazon_id}` : c.ai.decision === "none_of_these" ? "none of these" : "couldn’t tell")
                            : "not reviewed — the system accepted this one"],
                          ["The system", c.outcome === "accept"
                            ? `accepted ${c.systemPick} with no human review`
                            : `withheld it — ${REASON[c.outcome][0]}`],
                        ].map(([k, v]) => (
                          <div key={k} className="grid gap-1 bg-panel px-4 py-3 sm:grid-cols-[130px_1fr] sm:gap-4">
                            <dt className="font-mono text-[10px] uppercase tracking-[0.14em] text-faint">{k}</dt>
                            <dd className="text-sm">{v}</dd>
                          </div>
                        ))}
                      </dl>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </>
          )}
        </div>
        <p className="mt-4 max-w-[70ch] text-sm text-faint">
          120 records sampled with a fixed seed across every outcome — 50 the system auto-accepted,
          70 it sent to review — so the mix reflects the real pipeline rather than a flattering selection.
        </p>
      </Reveal>
    </>
  );
}
