import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { HEADLINE, ORIGINAL } from "../src/data/facts.js";

const snapshot = JSON.parse(readFileSync(new URL("../public/data.json", import.meta.url), "utf8"));
const { stats, cards } = snapshot;

test("snapshot metadata and public headline describe the same run", () => {
  for (const [field, expected] of Object.entries({
    records: HEADLINE.records,
    candidates: HEADLINE.candidates,
    crossProduct: HEADLINE.crossProduct,
    withPartner: HEADLINE.withPartner,
    trueMatches: HEADLINE.trueMatches,
    accepted: HEADLINE.accepted,
    queue: HEADLINE.queued,
    different: HEADLINE.different,
    precision: HEADLINE.precision,
    recall: HEADLINE.recall,
    f1: HEADLINE.f1,
    uSampleSeed: HEADLINE.uSampleSeed,
    originalF1: ORIGINAL.f1,
  })) assert.equal(stats[field], expected, field);
  assert.equal(stats.accepted + stats.queue + stats.different, stats.records);
  assert.equal(Object.values(stats.byReason).reduce((a, b) => a + b, 0), stats.queue);
  assert.ok(Math.abs((1 - stats.candidates / stats.crossProduct) * 100 - 98.9988) < 0.00001);
});

test("fixed sample outcomes and visible answer keys are internally consistent", () => {
  assert.equal(cards.length, 120);
  assert.equal(stats.sample.n, cards.length);
  assert.equal(Object.values(stats.sample.drawQuota).reduce((a, b) => a + b, 0), cards.length);
  assert.equal(new Set(cards.map((card) => card.id)).size, cards.length);
  const actual = Object.fromEntries(Object.entries(stats.sample.actual).sort());
  const counted = {};
  for (const card of cards) {
    counted[card.outcome] = (counted[card.outcome] ?? 0) + 1;
    assert.ok(card.blocks.length > 0, card.id);
    const shown = card.blocks.flatMap((block) => block.members.map((member) => member.amazon_id));
    assert.equal(new Set(shown).size, shown.length, card.id);
    assert.deepEqual(card.truthShown, card.truth.filter((id) => shown.includes(id)), card.id);
    if (card.outcome === "accept") {
      assert.ok(card.systemPick && shown.includes(card.systemPick), card.id);
    } else {
      assert.ok(card.outcome.startsWith("review_"), card.id);
      assert.equal(card.systemPick, null, card.id);
    }
    for (const block of card.blocks) {
      assert.equal(block.shown, block.members.length, card.id);
      assert.equal(block.truncated, block.shown < block.true_size, card.id);
      for (const member of block.members) {
        assert.equal("match_probability" in member, false, card.id);
        assert.equal("bits" in member, false, card.id);
      }
    }
  }
  assert.deepEqual(actual, Object.fromEntries(Object.entries(counted).sort()));
  assert.equal(stats.sample.actual.accept + cards.filter((card) => card.outcome !== "accept").length, 120);
  assert.equal(stats.sample.actual.accept, 49);
  assert.equal(cards.find((card) => card.id === "A_657")?.outcome, "review_not_reciprocal");
});
