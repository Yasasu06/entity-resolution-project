(function(){
  var cards = [], i = 0, picked = null, done = false;
  var seen = 0, right = 0, held = 0;

  var REASON = {
    accept: "auto-accepted without review",
    review_tied: "queued — tied at the top",
    review_unsure: "queued — score below the bar",
    review_not_reciprocal: "queued — match not mutual",
    review_quantity_conflict: "queued — quantities conflict"
  };
  var FIELDS = ["title","brand","modelno","price","category"];
  var $ = function(id){ return document.getElementById(id); };
  function esc(s){ return String(s == null ? "" : s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }

  function fields(rec){
    return FIELDS.filter(function(f){ return rec[f] != null && rec[f] !== ""; })
      .map(function(f){ return '<div class="f"><span>'+f+'</span><span>'+esc(rec[f])+'</span></div>'; })
      .join("");
  }

  function render(){
    var c = cards[i];
    picked = null; done = false;
    $("rec-id").textContent = c.id;
    $("rec-why").textContent = REASON[c.outcome] || c.outcome;
    $("subject").innerHTML = fields(c.walmart);
    $("reveal").hidden = true;
    $("reveal").classList.remove("in");
    $("btn-next").hidden = true;
    $("btn-confirm").disabled = true;
    ["btn-confirm","btn-none","btn-cant"].forEach(function(b){ $(b).disabled = false; });

    var html = "";
    c.blocks.forEach(function(b){
      var note = "";
      if (b.tied) {
        note = '<div class="grp-note">' + b.members.length +
          " candidates the evidence cannot separate — shown in no particular order" +
          (b.truncated ? " · showing " + b.shown + " of " + b.true_size : "") + "</div>";
      } else if (b.truncated) {
        note = '<div class="grp-note">showing ' + b.shown + " of " + b.true_size + "</div>";
      }
      html += '<div class="grp' + (b.tied ? " tied" : "") + '">' + note +
        b.members.map(function(m){
          var meta = FIELDS.slice(1).filter(function(f){ return m[f]; })
            .map(function(f){ return f + " " + m[f]; }).join("  ·  ");
          return '<button class="cand" type="button" data-id="' + esc(m.amazon_id) +
            '" aria-pressed="false"><span class="id">' + esc(m.amazon_id) +
            '</span><span><span class="ttl">' + esc(m.title) + "</span>" +
            (meta ? '<span class="meta">' + esc(meta) + "</span>" : "") + "</span></button>";
        }).join("") + "</div>";
    });
    $("cands").innerHTML = html;
    tally();
  }

  function tally(){
    $("tally").textContent = seen === 0 ? "no decisions yet"
      : right + " of " + seen + " correct" + (held ? "  ·  " + held + " held" : "");
  }

  $("cands").addEventListener("click", function(e){
    if (done) return;
    var btn = e.target.closest(".cand");
    if (!btn) return;
    Array.prototype.forEach.call($("cands").querySelectorAll(".cand"), function(el){
      el.setAttribute("aria-pressed", String(el === btn));
    });
    picked = btn.dataset.id;
    $("btn-confirm").disabled = false;
  });

  function answer(kind){
    if (done) return;
    done = true;
    var c = cards[i];
    var hasTruth = c.truth.length > 0;
    var shownTruth = c.truthShown.length > 0;
    var correct = false, verdict = "", why = "";

    if (kind === "match") {
      correct = c.truth.indexOf(picked) !== -1;
      verdict = correct ? "Correct." : "Not a match.";
      why = correct ? "That pair is in the answer key."
        : (hasTruth ? "This record does have a partner, but not that one."
                    : "This record has no partner in the answer key at all.");
    } else if (kind === "none") {
      if (!hasTruth) { correct = true; verdict = "Correct.";
        why = "This record has no partner in the answer key — two thirds of records don't."; }
      else if (!shownTruth) { correct = true; verdict = "Correct, given what you were shown.";
        why = "A partner exists, but the display cap cut it from the list. The answer key still scores this wrong — that gap belongs to the interface, not to you."; }
      else { verdict = "There was a match."; why = "The correct partner was on the list."; }
    } else {
      held++; verdict = "Held."; why = "Recorded as undecided — not counted either way.";
    }
    if (kind !== "cant") { seen++; if (correct) right++; }

    Array.prototype.forEach.call($("cands").querySelectorAll(".cand"), function(el){
      el.disabled = true;
      if (c.truth.indexOf(el.dataset.id) !== -1) el.classList.add("right");
      else if (kind === "match" && el.dataset.id === picked) el.classList.add("wrong");
    });

    var keyTxt = hasTruth
      ? (shownTruth ? c.truthShown.join(", ") + " — shown above in green"
                    : c.truth.join(", ") + " — not among the candidates shown")
      : "no partner exists for this record";
    var aiTxt = c.ai
      ? (c.ai.decision === "match" ? "chose " + c.ai.amazon_id
         : c.ai.decision === "none_of_these" ? "none of these" : "couldn't tell")
      : "not reviewed by the AI arm — the system accepted this one";
    var sysTxt = c.outcome === "accept"
      ? "accepted " + c.systemPick + " with no human review"
      : "withheld it — " + (REASON[c.outcome] || c.outcome);

    $("reveal").innerHTML =
      '<div class="verdict ' + (kind === "cant" ? "" : (correct ? "ok" : "bad")) + '">' +
        esc(verdict) + "</div>" +
      '<p class="note">' + esc(why) + "</p>" +
      '<div class="rows">' +
        '<div class="row"><span class="lbl">Answer key</span><span>' + esc(keyTxt) + "</span></div>" +
        '<div class="row"><span class="lbl">AI reviewer</span><span>' + esc(aiTxt) + "</span></div>" +
        '<div class="row"><span class="lbl">The system</span><span>' + esc(sysTxt) + "</span></div>" +
      "</div>";
    $("reveal").hidden = false;
    requestAnimationFrame(function(){ $("reveal").classList.add("in"); });
    ["btn-confirm","btn-none","btn-cant"].forEach(function(b){ $(b).disabled = true; });
    $("btn-next").hidden = false;
    tally();
  }

  $("btn-confirm").addEventListener("click", function(){ if (picked) answer("match"); });
  $("btn-none").addEventListener("click", function(){ answer("none"); });
  $("btn-cant").addEventListener("click", function(){ answer("cant"); });
  $("btn-next").addEventListener("click", function(){
    i = (i + 1) % cards.length; render();
    $("tool").scrollIntoView({ block: "start", behavior: "smooth" });
  });

  fetch("data.json")
    .then(function(r){ if(!r.ok) throw new Error(r.status); return r.json(); })
    .then(function(d){ cards = d.cards; render(); })
    .catch(function(){
      document.getElementById("cands").innerHTML =
        '<p class="note">The sample records could not be loaded. This page reads '
        + '<code>data.json</code> over HTTP, so it needs to be served rather than '
        + 'opened straight from disk.</p>';
    });
})();
