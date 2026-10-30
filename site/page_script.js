(function () {
  const D = JSON.parse(document.getElementById("data").textContent);
  const C = D.C;
  const NAMES = { loneliness: "Loneliness", stress: "Stress", mood: "Low mood", self_esteem: "Low self-esteem" };
  const SHORT = { loneliness: "Lonely", stress: "Stress", mood: "Mood", self_esteem: "Esteem" };
  const VAR = { loneliness: "--c-lone", stress: "--c-stress", mood: "--c-mood", self_esteem: "--c-esteem" };
  const col = (c) => `var(${VAR[c]})`;
  const fmt = (x, d = 2) => (x < 0 ? "−" : "") + Math.abs(x).toFixed(d).replace(/^0\./, ".");
  const esc = (s) => s.replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
  const tagify = (s) => esc(s)
    .replace(/\[(EMAIL|PHONE|URL|NAME)\]/g, '<span class="redact">[$1]</span>')
    .replace(/\[MASK\]/g, '<span class="maskw">[MASK]</span>');
  const pids = Object.keys(D.people).sort();
  const $ = (id) => document.getElementById(id);

  // ---------- hero facts ----------
  const passN = D.results.filter((r) => r.all_three_pass).length;
  $("facts").innerHTML = [
    [pids.length, "simulated young adults"],
    [D.n_days.toLocaleString(), "person-days"],
    [D.n_msgs.toLocaleString(), "participant messages"],
    [`${passN} of ${C.length}`, "indicators pass all tests"],
  ].map(([b, s]) => `<div class="fact"><b>${b}</b><span>${s}</span></div>`).join("");

  // ---------- explorer ----------
  const state = { pid: "P001", con: "loneliness", day: 1, view: 1 };
  $("pid").innerHTML = pids.map((p) => `<option value="${p}">${p}${D.people[p].topic ? " · topic writer" : ""}</option>`).join("");
  $("con").innerHTML = C.map((c) => `<button type="button" data-c="${c}" aria-pressed="false"><span class="dot" style="background:${col(c)}"></span>${NAMES[c]}</button>`).join("");

  function zs(a) {
    const m = a.reduce((s, x) => s + x, 0) / a.length;
    const sd = Math.sqrt(a.reduce((s, x) => s + (x - m) ** 2, 0) / Math.max(a.length - 1, 1));
    return a.map((x) => (sd > 0 ? (x - m) / sd : 0));
  }
  function pearson(a, b) {
    const za = zs(a), zb = zs(b);
    return za.reduce((s, x, i) => s + x * zb[i], 0) / Math.max(a.length - 1, 1);
  }

  function drawChart() {
    const P = D.people[state.pid], ci = C.indexOf(state.con);
    const ema = P.days.map((d) => d.ema[ci]), ind = P.days.map((d) => d.ind[ci]);
    const ze = zs(ema), zi = zs(ind);
    const W = 640, H = 316, L = 58, R = 18, T = 16, B = 44;
    const x = (i) => L + (i * (W - L - R)) / (P.days.length - 1);
    const y = (v) => T + ((3 - Math.max(-3, Math.min(3, v))) * (H - T - B)) / 6;
    let s = "";
    for (const v of [-2, -1, 0, 1, 2]) {
      s += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="var(--rule)" stroke-width="1" ${v === 0 ? "" : 'stroke-dasharray="2 4"'}/>`;
      s += `<text x="${L - 24}" y="${y(v) + 4}" text-anchor="end">${v > 0 ? "+" + v : v === 0 ? "0" : "−" + -v}</text>`;
    }
    const sel = state.day - 1;
    s += `<rect x="${x(sel) - 14}" y="${T}" width="28" height="${H - T - B}" rx="4" fill="var(--accent-soft)"/>`;
    P.days.forEach((d, i) => { s += `<text x="${x(i)}" y="${H - 26}" text-anchor="middle">${d.d}</text>`; });
    const path = (arr) => arr.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
    s += `<path d="${path(ze)}" fill="none" stroke="${col(state.con)}" stroke-width="2.5" stroke-linejoin="round"/>`;
    s += `<path d="${path(zi)}" fill="none" stroke="var(--ink)" stroke-width="2" stroke-dasharray="6 4" stroke-linejoin="round"/>`;
    ze.forEach((v, i) => { s += `<circle cx="${x(i)}" cy="${y(v)}" r="${i === sel ? 5.5 : 4}" fill="${col(state.con)}"/>`; });
    zi.forEach((v, i) => { s += `<circle cx="${x(i)}" cy="${y(v)}" r="${i === sel ? 4.5 : 3}" fill="var(--surface)" stroke="var(--ink)" stroke-width="1.8"/>`; });
    P.days.forEach((d, i) => { s += `<rect data-day="${d.d}" x="${x(i) - 14}" y="${T}" width="28" height="${H - T - B}" fill="transparent" style="cursor:pointer"><title>Day ${d.d}</title></rect>`; });
    s += `<text x="${(L + W - R) / 2}" y="${H - 4}" text-anchor="middle">study day</text>`;
    $("chart").innerHTML = s;
    $("lg-ema").style.borderColor = col(state.con);
    $("lg-ind").style.borderColor = "var(--ink)";
    $("chart-title").textContent = `${NAMES[state.con]}: daily survey vs language indicator`;
    const r = pearson(ema, ind);
    const pooled = D.results.find((q) => q.construct === state.con).r_within;
    $("rline").innerHTML = `Within-person r for ${state.pid}: <b class="mono">${isFinite(r) ? fmt(r) : "n/a"}</b> over 14 days. Pooled across all ${pids.length} participants: <b class="mono">${fmt(pooled)}</b>. Single-person correlations from 14 days are noisy; the test uses the pooled value.`;
  }

  function drawDay() {
    const P = D.people[state.pid], d = P.days[state.day - 1];
    $("day-title").textContent = `Day ${d.d} · ${d.m.length} message${d.m.length === 1 ? "" : "s"}`;
    $("daybar").innerHTML = P.days.map((x) => `<button type="button" data-day="${x.d}" aria-pressed="${x.d === state.day}">${x.d}</button>`).join("");
    $("dayinfo").innerHTML = C.map((c, i) => `<div><span class="k">${SHORT[c]} survey</span><span class="v" style="color:${col(c)}">${d.ema[i]} / 7</span><span class="k">indicator ${fmt(d.ind[i])}</span></div>`).join("");
    const rows = d.m.map((m) => {
      const t = D.texts[m[state.view]];
      const sc = C.map((c, i) => {
        const v = m[3][i], w = Math.min(Math.abs(v), 0.6) / 0.6 * 50;
        const left = v >= 0 ? 50 : 50 - w;
        return `<div class="sc"><span>${SHORT[c]} ${fmt(v)}</span><div class="track"><span style="left:${left}%;width:${w}%;background:${col(c)}"></span></div></div>`;
      }).join("");
      return `<div class="bubble"><div class="txt">${tagify(t)}</div><div class="scores">${sc}</div></div>`;
    }).join("");
    $("chat").innerHTML = rows + `<div class="ai-note">AI replies in the export are discarded at the parse step and never scored.</div>`;
    document.querySelectorAll("#view button").forEach((b) => b.setAttribute("aria-pressed", String(+b.dataset.v === state.view)));
  }

  function drawTags() {
    const P = D.people[state.pid];
    const nm = P.days.reduce((s, d) => s + d.m.length, 0);
    const nPii = P.days.reduce((s, d) => s + d.m.filter((m) => m[0] !== m[1]).length, 0);
    let t = `<span class="tag">${nm} messages over 14 days</span>`;
    if (P.topic) t += `<span class="tag warn">Topic writer: asks about loneliness as a subject</span>`;
    if (nPii) t += `<span class="tag warn">${nPii} message${nPii > 1 ? "s" : ""} with personal details removed</span>`;
    $("ptags").innerHTML = t;
  }

  function render() {
    $("pid").value = state.pid;
    document.querySelectorAll("#con button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.c === state.con)));
    drawTags(); drawChart(); drawDay();
  }
  $("pid").addEventListener("change", (e) => { state.pid = e.target.value; state.day = 1; render(); });
  $("con").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { state.con = b.dataset.c; render(); } });
  $("daybar").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { state.day = +b.dataset.day; drawChart(); drawDay(); } });
  $("chart").addEventListener("click", (e) => { const r = e.target.closest("[data-day]"); if (r) { state.day = +r.dataset.day; drawChart(); drawDay(); } });
  $("view").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { state.view = +b.dataset.v; drawDay(); } });
  $("random").addEventListener("click", () => { state.pid = pids[Math.floor(Math.random() * pids.length)]; state.day = 1; render(); });
  const topicPids = pids.filter((p) => D.people[p].topic);
  let ti = 0;
  $("topicp").addEventListener("click", () => {
    state.pid = topicPids[ti++ % topicPids.length]; state.con = "loneliness"; state.view = 2;
    const P = D.people[state.pid];
    const tset = new Set(D.texts.map((t, i) => [t, i]).filter(([t]) => /loneliness|isolation/i.test(t) && /essay|research|statistics|paper/i.test(t)).map(([, i]) => i));
    const dd = P.days.find((d) => d.m.some((m) => tset.has(m[0])));
    state.day = dd ? dd.d : 1; render();
  });

  // ---------- encoder (port of sklearn TfidfVectorizer + TruncatedSVD) ----------
  const M = D.model, V = new Map(M.vocab.map((w, i) => [w, i])), K = M.comp[0].length;
  const PII = [[/\S+@\S+/g, "[EMAIL]"], [/\b0\d[\d ]{6,}\b/g, "[PHONE]"], [/https?:\/\/\S+/g, "[URL]"],
    [/\b(?:I am|I'm|this is) [A-Z][a-z]+(?: [A-Z][a-z]+)?/g, "[NAME]"]];
  const scrub = (t) => PII.reduce((s, [rx, tag]) => s.replace(rx, tag), t);
  function encode(text) {
    const toks = text.toLowerCase().match(/\b\w\w+\b/g) || [];
    const grams = toks.concat(toks.slice(1).map((w, i) => toks[i] + " " + w));
    const tf = new Map(); let known = 0;
    for (const g of grams) { if (V.has(g)) { tf.set(V.get(g), (tf.get(V.get(g)) || 0) + 1); } }
    let norm = 0; const xs = [];
    for (const [j, c] of tf) { const v = (1 + Math.log(c)) * M.idf[j]; xs.push([j, v]); norm += v * v; }
    norm = Math.sqrt(norm) || 1;
    const e = new Array(K).fill(0);
    for (const [j, v] of xs) { const row = M.comp[j]; for (let k = 0; k < K; k++) e[k] += (v / norm) * row[k]; }
    const n2 = Math.sqrt(e.reduce((s, x) => s + x * x, 0));
    const en = e.map((x) => x / Math.max(n2, 1e-9));
    toks.forEach((w) => { if (V.has(w)) known++; });
    return { e: en, toks: toks.length, known };
  }
  const dotmax = (e, A) => Math.max(...A.map((a) => a.reduce((s, x, k) => s + x * e[k], 0)));
  function scoreText(raw) {
    const s = scrub(raw), r = encode(s), base = dotmax(r.e, M.anchors.neutral);
    return { s, toks: r.toks, known: r.known, sc: C.map((c) => dotmax(r.e, M.anchors[c]) - base) };
  }
  window.__score = scoreText;
  const EX = ["I can't stop crying and nothing feels worth it", "deadline tomorrow and I'm so overwhelmed",
    "write an essay on loneliness in modern cities", "give me a recipe for pasta", "I'm not good enough for this job",
    "this is Sam Jones, my email is sam@uni.edu.au"];
  $("examples").innerHTML = EX.map((x) => `<button type="button">${esc(x)}</button>`).join("");
  $("examples").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { $("msg").value = b.textContent; tryRender(); } });
  function tryRender() {
    const r = scoreText($("msg").value);
    $("bars").innerHTML = C.map((c, i) => {
      const v = r.sc[i], w = Math.min(Math.abs(v), 0.8) / 0.8 * 50, left = v >= 0 ? 50 : 50 - w;
      return `<div class="bar-row"><span>${NAMES[c]}</span><div class="track"><span style="left:${left}%;width:${w}%;background:${col(c)}"></span></div><span class="val mono">${fmt(v)}</span></div>`;
    }).join("");
    $("scrubbed").innerHTML = `<span class="label">Text that gets scored</span><br>${tagify(r.s) || "<em>empty</em>"}`;
    $("cover").textContent = r.toks === 0 ? "Type a message to score it." :
      `${r.known} of ${r.toks} words are in the demo vocabulary (${M.vocab.length.toLocaleString()} terms from the simulated chats). Unknown words carry no signal here; a pretrained encoder would replace this in a real study. Scores above 0 mean the message is closer to the construct than to an ordinary task request.`;
  }
  $("msg").addEventListener("input", tryRender);

  // ---------- results ----------
  $("resgrid").innerHTML = D.results.map((r) => {
    const c = r.construct, ok = r.all_three_pass;
    const t = (pass, name, detail) => `<div class="test"><span class="ic ${pass ? "ok" : "no"}">${pass ? "✓" : "✗"}</span><div>${name}<small>${detail}</small></div></div>`;
    return `<div class="res-card">
      <h3><span class="dot" style="background:${col(c)}"></span>${NAMES[c]}</h3>
      <span class="verdict ${ok ? "ok" : "no"}">${ok ? "Passes all three" : "Fails"}</span>
      ${t(r.pass_convergence, "Convergence", `r = ${fmt(r.r_within)} [${fmt(r.ci_low)}, ${fmt(r.ci_high)}] · needs ≥ .20 · max other ${fmt(r.max_r_other)}`)}
      ${t(r.pass_robustness, "Robustness", `length-controlled ${fmt(r.r_length_controlled)} · topic-masked ${fmt(r.r_topic_masked)}`)}
      ${t(r.pass_agreement, "Human agreement", `rater ICC ${fmt(r.rater_icc)} (≥ .60) · r with raters ${fmt(r.r_indicator_raters)} (≥ .30)`)}
    </div>`;
  }).join("");
  const mx = Math.max(...D.cm.flat());
  $("matrix").innerHTML = `<thead><tr><th></th><th colspan="4">Daily survey item</th></tr><tr><th scope="col">Indicator</th>${C.map((c) => `<th scope="col">${SHORT[c]}</th>`).join("")}</tr></thead><tbody>` +
    D.cm.map((row, i) => `<tr><th scope="row">${SHORT[C[i]]}</th>${row.map((v, j) =>
      `<td class="${i === j ? "diag" : ""}" style="background:color-mix(in srgb, var(--accent) ${Math.round(Math.max(v, 0) / mx * 55)}%, var(--surface))">${fmt(v)}</td>`).join("")}</tr>`).join("") + "</tbody>";

  // ---------- traps ----------
  const allDays = pids.flatMap((p) => D.people[p].days);
  const voiced = C.map((c, i) => allDays.reduce((s, d) => s + d.shown[i], 0) / allDays.length);
  const piiEx = D.texts.find((t) => t.includes("[EMAIL]")) || "";
  const piiRaw = (() => { for (const p of pids) for (const d of D.people[p].days) for (const m of d.m) if (D.texts[m[1]] === piiEx) return D.texts[m[0]]; return ""; })();
  const es = D.results.find((r) => r.construct === "self_esteem"), lo = D.results.find((r) => r.construct === "loneliness");
  $("trapgrid").innerHTML = [
    ["Writing about loneliness is not feeling lonely",
      `${D.n_topic} of ${pids.length} simulated people ask the AI about loneliness as a subject (essays, statistics, papers), whatever they feel. Masking topic words removes that shortcut; the loneliness indicator still holds at r = ${fmt(lo.r_topic_masked)}.`,
      `<div class="ex">${tagify("write an essay on [MASK] in modern cities")}</div>`],
    ["Self-esteem is rarely voiced",
      `Low self-esteem is expressed in about ${(voiced[3] * 100).toFixed(1)}% of messages, against ${(voiced[0] * 100).toFixed(1)}–${(Math.max(voiced[1], voiced[2]) * 100).toFixed(1)}% for the other states. Its indicator reaches r = ${fmt(es.r_within)}, below the .20 threshold, so it fails convergence and robustness. A sound method should reject it, and it does.`, ""],
    ["Personal details appear in the text",
      `${D.n_pii} messages contain an email address, phone number or self-introduced name. They are replaced on the device before scoring, so no identifier reaches the daily scores.`,
      `<div class="ex">${esc(piiRaw)}</div><div class="ex">${tagify(piiEx)}</div>`],
  ].map(([h, p, ex]) => `<div class="trap"><h3>${h}</h3><p>${p}</p>${ex}</div>`).join("");

  render(); tryRender();
})();
