// app.js - the prototype page. Reads window.PROTOTYPE_DATA (data.js).
//
// Plain JavaScript, no libraries. Two screens share one page: a search screen,
// and a standard with what it builds on. Which one shows is decided by the part
// of the address after "#": "#s=378" opens record 378, so the browser's Back
// button works and a view can be bookmarked.

const DATA = window.PROTOTYPE_DATA;

const LINK_WORDS = {
  next_grade: "same strand, earlier grade",
  next_level: "same standard, lower proficiency level",
  builds_towards: "builds towards",
};
const SOURCE_WORDS = {
  structural: "read from the identifier",
  learning_commons: "Learning Commons",
  owner: "the owner",
};
const COURSE_ORDER = ["Algebra I", "Geometry", "Algebra II", "Math I", "Math II", "Math III"];
const PAGE = 40;      // search results shown before "Show more"

// What the teacher has chosen on screen.
const state = { q: "", subject: "", grade: "", course: "", level: "", inComponents: true,
                shown: PAGE, depth: 1, layout: "ladder", collected: [] };

// ---- small helpers -----------------------------------------------------

// el("p", {class: "muted"}, "text", childNode) builds one element. Text is
// always added as text, never as HTML, so nothing in the data can break the page.
function el(tag, attrs, ...children) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs || {})) {
    if (name === "onclick") node.addEventListener("click", value);
    else if (value !== null && value !== undefined && value !== false) node.setAttribute(name, value);
  }
  for (const child of children.flat(3)) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return node;
}

function plural(n, word) { return `${n} ${word}${n === 1 ? "" : "s"}`; }

// Lower case, and the minus sign and en dash as a hyphen, so text typed on a
// keyboard matches both ways CDE writes a dash (decision 0012).
function norm(text) { return text.toLowerCase().replace(/[−–]/g, "-"); }

function push(map, key, value) {
  if (!map.has(key)) map.set(key, []);
  map.get(key).push(value);
}

// ---- indexes built once from the data ----------------------------------

const byId = new Map();          // record ID -> standard
const edgesTo = new Map();       // record ID -> links arriving at it (what it builds on)
const edgesFrom = new Map();     // record ID -> links leaving it (what it leads on to)
const componentsOf = new Map();  // record ID -> learning components
const elaOfEld = new Map();      // "PI|6|4" (part, number, grade) -> ELA links
const eldOfEla = new Map();      // ELA record ID -> ELD links
const eldRecords = new Map();    // "PI|6|4" -> the ELD records of that standard

function buildIndexes() {
  for (const s of DATA.standards) {
    byId.set(s.id, s);
    s.label = s.identifier + (s.course || s.level ? ` (${s.course || s.level})` : "");
    s.words = norm([s.text, ...s.subs.map((x) => x[1])].join(" "));
    if (s.subject === "eld") push(eldRecords, `${s.strand}|${s.number}|${s.gmin}`, s);
  }
  for (const [from, to, type, source, note, reviewed, confidence] of DATA.edges) {
    const edge = { from, to, type, source, note, reviewed, confidence };
    push(edgesTo, to, edge);
    push(edgesFrom, from, edge);
  }
  for (const [id, letter, componentId, reviewed] of DATA.component_links) {
    const [text, author] = DATA.components[componentId];
    push(componentsOf, id, { letter, text, author, reviewed, search: norm(text) });
  }
  for (const [part, number, gmin, elaId, reviewed] of DATA.eld_ela) {
    const link = { part, number, gmin, elaId, reviewed };
    push(elaOfEld, `${part}|${number}|${gmin}`, link);
    push(eldOfEla, elaId, link);
  }
  // The records of one ELD standard in reading order: by letter, then Emerging, Expanding, Bridging.
  const levels = ["Emerging", "Expanding", "Bridging"];
  for (const records of eldRecords.values()) {
    records.sort((a, b) => a.identifier.replace(/\.\w+$/, "").localeCompare(b.identifier.replace(/\.\w+$/, "")) ||
      levels.indexOf(a.level) - levels.indexOf(b.level));
  }
}

// ---- search ------------------------------------------------------------
//
// How words are matched. The typed text is split into words, and small words
// (and, the, with...) are dropped. Each remaining word is matched at the start
// of a word in the standard, after cutting a common ending, so "adding" finds
// add, adds and addition. A teacher term from data/curated/search_terms.csv
// that matches typed words ("regrouping") also lets the standards' wording
// ("compose", "decompose") count for those words. A standard that has every
// word comes first; if none has every word, the ones with the most are shown.

const SMALL_WORDS = new Set(("a an and are as at be but by can for from has have he her him his i " +
  "in is it its of on or she so that the their them they this to was were when who will with").split(" "));

// Cut one common ending, keeping at least three letters: adding -> add,
// regrouping -> regroup, compose -> compos, multiply -> multipl.
function stem(word) {
  if (word.length <= 4) return word;
  for (const ending of ["ing", "ed", "es", "s", "e", "y"]) {
    if (word.endsWith(ending) && word.length - ending.length >= 3) return word.slice(0, -ending.length);
  }
  return word;
}

function words(text) { return norm(text).split(/[^a-z0-9]+/).filter(Boolean); }

function escapeRegExp(text) { return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }

// A pattern for a word or phrase as the standards write it: each word at the
// start of a word in the text, a space or hyphen between them, and the last
// word's ending cut. "skip-count" and "skip count" give the same pattern.
function pattern(phrase) {
  const parts = words(phrase);
  parts[parts.length - 1] = stem(parts[parts.length - 1]);
  const end = /^[0-9]+$/.test(parts[parts.length - 1]) ? "(?![0-9])" : "";   // 3 is not 30
  return new RegExp("\\b" + parts.map(escapeRegExp).join("[\\s-]+") + end);
}

// Does the typed word `typed` count as the term's word `termWord`?
function sameWord(typed, termWord) {
  return typed === termWord || (termWord.length >= 3 && typed.startsWith(stem(termWord)));
}

// The words to look for, as slots. A slot is satisfied when any of its
// alternatives is: the typed word itself, or (for a teacher term) the
// standards' wording. A teacher term of two words takes up two typed words.
function slotsFor(typedText) {
  const typed = words(typedText).filter((w) => !SMALL_WORDS.has(w));
  const terms = (DATA.search_terms || [])
    .map(([teacher, standards, subject, evidence, source, reviewed]) =>
      ({ teacher, teacherWords: words(teacher), standards, subject, source, reviewed }))
    .filter((t) => !state.subject || !t.subject || t.subject === state.subject)
    .sort((a, b) => b.teacherWords.length - a.teacherWords.length);
  const slots = [];
  for (let i = 0; i < typed.length;) {
    const size = terms.map((t) => t.teacherWords.length)
      .find((n) => terms.some((t) => t.teacherWords.length === n &&
        t.teacherWords.every((w, k) => typed[i + k] !== undefined && sameWord(typed[i + k], w))));
    if (size) {
      const span = typed.slice(i, i + size);
      const via = terms.filter((t) => t.teacherWords.length === size &&
        t.teacherWords.every((w, k) => sameWord(span[k], w)))
        .map((t) => ({ ...t, typed: span.join(" "), re: pattern(t.standards) }));
      // The typed words themselves count only as the phrase typed: "3 digit", not 3 and digit anywhere.
      slots.push({ typed: span.join(" "), own: [pattern(span.join(" "))], via });
      i += size;
    } else {
      slots.push({ typed: typed[i], own: [pattern(typed[i])], via: [] });
      i += 1;
    }
  }
  return slots;
}

// null if `text` does not satisfy the slot; "own" if the typed words are in
// it; otherwise the teacher term whose standards wording is. A term listed for
// one subject counts only in that subject: "compose" is regrouping in math,
// not in writing.
function satisfies(slot, text, subject) {
  if (slot.own.every((re) => re.test(text))) return "own";
  return slot.via.find((t) => (!t.subject || t.subject === subject) && t.re.test(text)) || null;
}

// How well one standard matches: which slot each part of it satisfies, and the
// learning component that helped, if one did.
function scoreStandard(s, slots) {
  const inText = slots.map((slot) => satisfies(slot, s.words, s.subject));
  let best = { how: inText, component: null };
  const count = (how) => how.filter(Boolean).length;
  if (state.inComponents && count(inText) < slots.length) {
    for (const c of componentsOf.get(s.id) || []) {
      const how = slots.map((slot, i) => inText[i] || satisfies(slot, c.search, s.subject));
      if (count(how) > count(best.how)) best = { how, component: c.text };
    }
  }
  return { ...best, count: count(best.how) };
}

// Returns {hits: [{s, rank, letter, score, copies}], slots, partial}.
//   rank 0  the code typed is this standard's code
//   rank 1  the code starts with what was typed
//   rank 2  every word is in the standard's text
//   rank 3  every word is in the text or one of its learning components
//   rank 4  only some of the words (shown only when nothing has them all)
function search() {
  const typed = norm(state.q.trim());
  const asCode = typed.replace(/\s+/g, "");
  const part = asCode.match(/^(.+\d)\.?([a-z])$/);     // l.5.1b -> l.5.1 and b
  const slots = typed ? slotsFor(typed) : [];
  const grade = state.grade === "" ? null : Number(state.grade);
  let found = [];

  for (const s of DATA.standards) {
    if (s.placeholder) continue;                        // "(Begins in grade 2)": not a standard
    if (state.subject && s.subject !== state.subject) continue;
    if (grade !== null && !(s.gmin <= grade && grade <= s.gmax)) continue;
    if (state.course && s.course && s.course !== state.course) continue;
    if (state.level && s.level && s.level !== state.level) continue;

    const hit = { s, rank: 2, letter: null, score: null, copies: [s] };
    if (typed) {
      const codes = [norm(s.norm), s.corrected ? norm(s.corrected) : null];
      if (codes.includes(asCode)) hit.rank = 0;
      else if (part && codes.includes(part[1]) && s.subs.some((x) => x[0] === part[2])) {
        hit.rank = 0;
        hit.letter = part[2];
      } else if (asCode.length >= 2 && /\d/.test(asCode) && codes[0].startsWith(asCode)) hit.rank = 1;
      else if (slots.length) {
        hit.score = scoreStandard(s, slots);
        if (!hit.score.count) continue;
        hit.rank = hit.score.count < slots.length ? 4 : hit.score.component ? 3 : 2;
      } else continue;
    }
    found.push(hit);
  }
  const partial = found.length > 0 && found.every((h) => h.rank === 4);
  if (!partial) found = found.filter((h) => h.rank < 4);
  // Stable sort: within a rank (and score), standards keep grade order.
  found.sort((a, b) => a.rank - b.rank || (b.score ? b.score.count : 0) - (a.score ? a.score.count : 0));

  // A high school math standard is one record per course. Show it once and
  // list the courses, so five near-identical results do not crowd the list.
  const groups = new Map();
  const hits = [];
  for (const hit of found) {
    const key = hit.s.course ? `${hit.s.identifier}|${hit.s.text}` : null;
    if (key && groups.has(key)) groups.get(key).copies.push(hit.s);
    else {
      if (key) groups.set(key, hit);
      hits.push(hit);
    }
  }
  return { hits, slots, partial };
}

const TERM_SOURCES = { claude: "Claude", owner: "the owner" };

function termWords(t) {
  const by = TERM_SOURCES[t.source] || t.source;
  return `${t.typed} → ${t.standards} (${t.reviewed ? "reviewed" : `suggested by ${by}, not reviewed`})`;
}

function resultCard(hit, slots) {
  const s = hit.s;
  const open = (record) => () => openStandard(record.id, hit.letter);
  const how = hit.score ? hit.score.how : [];
  const viaTerms = how.filter((h) => h && h !== "own");
  return el("div", { class: "card" },
    el("div", { class: "head" },
      el("button", { class: "code", onclick: open(s) },
        hit.copies.length > 1 ? s.identifier : s.label, hit.letter ? ` (part ${hit.letter})` : ""),
      el("span", {}, s.grade),
      el("span", { class: "muted" }, s.where)),
    el("p", {}, s.text),
    s.subs.length ? el("p", { class: "muted" }, plural(s.subs.length, "lettered part")) : null,
    s.url ? null : el("p", { class: "muted" },
      "CDE lists only the parts of this standard; the text of the whole is from Learning Commons."),
    hit.rank === 4
      ? el("p", { class: "muted" }, `Has ${hit.score.count} of the ${slots.length} words: ` +
          slots.filter((_, i) => how[i]).map((slot) => slot.typed).join(", "))
      : null,
    viaTerms.length
      ? el("p", { class: "muted" }, "Found through: ", viaTerms.map(termWords).join("; "))
      : null,
    hit.score && hit.score.component
      ? el("p", { class: "muted" }, "Found in a learning component: ", hit.score.component) : null,
    hit.copies.length > 1
      ? el("p", { class: "muted inline" }, `In ${hit.copies.length} courses. Open it in:`,
          hit.copies.map((c) => el("button", { class: "code", onclick: open(c) }, c.course)))
      : null);
}

function renderSearch() {
  const { hits, slots, partial } = search();
  const anyFilter = state.q.trim() || state.subject || state.grade !== "" || state.course || state.level;
  document.getElementById("course-box").hidden = state.subject && state.subject !== "math";
  document.getElementById("level-box").hidden = state.subject && state.subject !== "eld";

  const count = document.getElementById("count");
  const results = document.getElementById("results");
  if (!anyFilter) {
    count.textContent = "Type a code or some words, or choose a subject and grade.";
    results.replaceChildren();
    return;
  }
  count.textContent = hits.length ? `${plural(hits.length, "standard")} found.` : "Nothing found.";
  const parts = [];
  const used = slots.filter((slot) => slot.via.length);
  if (used.length) {
    parts.push(el("p", { class: "muted" }, "Your words were also looked for as the standards word them: ",
      used.map((slot) => `${slot.typed} → ${slot.via.map((t) => t.standards).join(" or ")}`).join("; "),
      `. These pairs are from the search terms list; ` +
      `${used.flatMap((slot) => slot.via).filter((t) => t.reviewed).length} of ` +
      `${used.flatMap((slot) => slot.via).length} are reviewed.`));
  }
  if (partial) {
    parts.push(el("p", { class: "notice" }, `No standard has all ${slots.length} words ` +
      `(${slots.map((slot) => slot.typed).join(", ")}). These have the most, best first.`));
  }
  if (!hits.length && state.q.trim()) {
    parts.push(el("p", { class: "muted" },
      "The search knows only the words the standards themselves use, and the teacher terms in its " +
      "list. It looks for the start of each word, so “subtract” also finds subtracting " +
      "and subtraction."));
  }
  if (!state.course && hits.some((h) => h.copies.length > 1)) {
    parts.push(el("p", { class: "notice" },
      "No high school math course is chosen, so every course was searched. California lists a " +
      "high school standard once for each course that teaches it. Such a standard is shown once " +
      "here with its courses; what it builds on can differ by course. Choose the student’s " +
      "course above to see only that course."));
  }
  parts.push(...hits.slice(0, state.shown).map((hit) => resultCard(hit, slots)));
  if (hits.length > state.shown) {
    parts.push(el("p", {}, el("button", {
      onclick: () => { state.shown += PAGE; renderSearch(); },
    }, `Show more (${hits.length - state.shown} left)`)));
  }
  results.replaceChildren(...parts);
}

// ---- walking the links -------------------------------------------------

// A sub-item record such as 4.NF.3.a also builds on whatever its parent
// standard 4.NF.3 builds on.
function withParent(id) {
  const parent = byId.get(id).parent;
  return parent === null ? [id] : [id, parent];
}

// Everything `id` builds on, nearest first: all standards one link away, then
// two links away, and so on. A standard reachable by two routes is listed once,
// at its shortest distance. The same search as walk_back() in src/lookup.py.
// Returns {found: [{steps, record, towards, edge}], more: is there anything further back}.
function walkBack(id, maxDepth) {
  const found = [];
  const seen = new Set(withParent(id));
  let frontier = [id];
  for (let steps = 1; steps <= maxDepth && frontier.length; steps++) {
    const next = [];
    for (const current of frontier) {
      for (const target of withParent(current)) {
        for (const edge of edgesTo.get(target) || []) {
          if (seen.has(edge.from)) continue;
          seen.add(edge.from);
          next.push(edge.from);
          found.push({ steps, record: byId.get(edge.from), towards: byId.get(target), edge });
        }
      }
    }
    frontier = next;
  }
  const more = frontier.some((r) => withParent(r).some((t) =>
    (edgesTo.get(t) || []).some((e) => !seen.has(e.from))));
  found.sort((a, b) => a.steps - b.steps || b.record.gmin - a.record.gmin ||
    a.record.identifier.localeCompare(b.record.identifier, "en", { numeric: true }));
  return { found, more };
}

// ---- pieces shared by the screens --------------------------------------

function whereFrom(record) {
  return record.url
    ? `CDE record ${record.id}`
    : "CDE has no record for the whole standard; text from Learning Commons";
}

// The sentence describing one link, e.g. "builds towards 4.NF.3; source: Learning Commons".
function linkSentence(item, start) {
  let words = LINK_WORDS[item.edge.type] || item.edge.type;
  if (item.edge.type === "builds_towards") words += ` ${item.towards.identifier}`;
  else if (item.towards.id !== start.id) words += ` (towards ${item.towards.identifier})`;
  let text = `${words}; source: ${SOURCE_WORDS[item.edge.source] || item.edge.source}`;
  if (item.edge.note) text += `; ${item.edge.note}`;
  return text;
}

function reviewWords(edge) {
  if (!edge.reviewed) return "not reviewed";
  return "reviewed" + (edge.confidence ? `, confidence ${edge.confidence}` : "");
}

function reviewChip(edge) {
  const words = reviewWords(edge);
  return el("span", { class: edge.reviewed ? "chip yes" : "chip no" },
    words[0].toUpperCase() + words.slice(1));
}

function howReached(item, start) {
  return `${plural(item.steps, "step")} back from ${start.identifier}; ` +
         `${linkSentence(item, start)}; ${reviewWords(item.edge)}`;
}

function codeButton(record, text) {
  return el("button", { class: "code", onclick: () => openStandard(record.id) }, text || record.label);
}

// ---- collected list ----------------------------------------------------

function sameItem(a, b) { return a.code === b.code && a.start === b.start && a.text === b.text; }

function addButton(entry) {
  const have = state.collected.some((c) => sameItem(c, entry));
  return el("button", {
    class: "small add", "aria-pressed": have ? "true" : "false",
    "aria-label": `${have ? "Remove" : "Add"} ${entry.code}`,
    onclick: () => {
      const at = state.collected.findIndex((c) => sameItem(c, entry));
      if (at >= 0) state.collected.splice(at, 1); else state.collected.push(entry);
      saveCollected();
      render();
    },
  }, have ? "Added" : "Add");
}

function entryFor(start, code, grade, text, how) {
  return { start: `${start.label} (${start.grade})`, code, grade, text, how };
}

function collectedText() {
  const lines = [];
  for (const start of new Set(state.collected.map((c) => c.start))) {
    lines.push(`Started from ${start}`);
    for (const c of state.collected.filter((x) => x.start === start)) {
      lines.push(`- ${c.code}${c.grade ? ` (${c.grade})` : ""}: ${c.text}`);
      lines.push(`  How it was reached: ${c.how}`);
    }
    lines.push("");
  }
  return lines.join("\n").trim();
}

// The browser's own storage keeps the list between visits, on this device
// only. Some browsers refuse it for a page opened from disk; the list then
// lasts until the page is closed.
function saveCollected() {
  try { localStorage.setItem("collected", JSON.stringify(state.collected)); } catch (error) { /* not kept */ }
}

function loadCollected() {
  try { state.collected = JSON.parse(localStorage.getItem("collected")) || []; } catch (error) { /* none */ }
}

function renderCollected() {
  document.getElementById("collected-count").textContent = state.collected.length
    ? plural(state.collected.length, "item") + " collected." : "Nothing collected yet.";
  document.getElementById("collected-text").value = collectedText();
}

// ---- the standard screen -----------------------------------------------

function standardCard(record, start, options) {
  // options: {cls, item (from walkBack), how, letter, title (plain text code, for the start)}
  const o = options || {};
  return el("div", { class: `card ${o.cls || ""}` },
    el("div", { class: "head" },
      o.title ? el("span", { class: "code" }, record.label) : codeButton(record),
      el("span", {}, record.grade),
      record.url
        ? el("a", { href: record.url, target: "_blank", rel: "noopener" }, whereFrom(record))
        : el("span", { class: "muted" }, whereFrom(record)),
      addButton(entryFor(start, record.identifier, record.grade, record.text, o.how))),
    o.title && record.where ? el("p", { class: "muted" }, record.where) : null,
    record.corrected
      ? el("p", { class: "muted" }, `CDE's identifier looks wrong; read here as ${record.corrected}.`)
      : null,
    el("p", {}, record.text),
    record.subs.length
      ? el("ol", { class: "subs" }, record.subs.map(([letter, text]) =>
          el("li", { class: letter === o.letter ? "marked" : null },
            el("span", {}, `${letter}. ${text}`),
            addButton(entryFor(start, `${record.identifier}${letter}`, record.grade, text,
              `part ${letter} of ${record.identifier}; ${o.how}`)))))
      : null,
    o.item
      ? el("p", { class: "link" }, linkSentence(o.item, start), " ", reviewChip(o.item.edge))
      : null);
}

function componentList(items, start, owner) {
  return el("ul", { class: "plain" }, items.map((c) =>
    el("li", {},
      c.letter ? el("strong", {}, `${c.letter}. `) : null, c.text, " ",
      addButton(entryFor(start, `Learning component of ${owner.identifier}${c.letter}`, "", c.text,
        `listed by Learning Commons for ${owner.identifier}; written by ${c.author}; ` +
        (c.reviewed ? "reviewed" : "not reviewed"))))));
}

function componentsPanel(start, parent) {
  const own = componentsOf.get(start.id) || [];
  const fromParent = parent ? componentsOf.get(parent.id) || [] : [];
  if (!own.length && !fromParent.length) {
    return el("p", { class: "muted" }, "No learning components are listed for this standard. " +
      "The data has them for math, and for ELA in grades K–2 only.");
  }
  const authors = [...new Set([...own, ...fromParent].map((c) => c.author))].join(", ");
  return el("details", { open: "" },
    el("summary", {}, `Learning components (${own.length + fromParent.length})`),
    el("p", { class: "muted" }, `The teachable pieces of the standard, written by ${authors}. Not reviewed.`),
    own.length ? [el("h3", {}, `For ${start.identifier}`), componentList(own, start, start)] : null,
    fromParent.length
      ? [el("h3", {}, `For the whole standard ${parent.identifier}`), componentList(fromParent, start, parent)]
      : null);
}

function reviewedCount(links) {
  return `${links.filter((l) => l.reviewed).length} of ${links.length} reviewed.`;
}

// ELA and ELD side by side, for a student who is an English learner with an IEP.
function bridgePanel(start) {
  const source = "Source: notes on Learning Commons’ California ELD items. ";
  if (start.subject === "eld") {
    const links = (elaOfEld.get(`${start.strand}|${start.number}|${start.gmin}`) || [])
      .filter((l) => !byId.get(l.elaId).placeholder);
    if (!links.length) return null;
    const groups = new Map();
    for (const l of links) push(groups, byId.get(l.elaId).strand, byId.get(l.elaId));
    return el("details", {},
      el("summary", {}, `ELA standards listed against this ELD standard (${links.length})`),
      el("p", { class: "muted" }, `They are listed against ELD ${start.strand} standard ${start.number}, ` +
        `${start.grade}, as a whole: every proficiency level and letter. ${source}${reviewedCount(links)}`),
      el("ul", { class: "plain" }, [...groups].map(([strand, records]) =>
        el("li", { class: "inline" }, el("strong", {}, strand + ":"), records.map((r) => codeButton(r))))));
  }
  if (start.subject === "ela") {
    const links = eldOfEla.get(start.id) || [];
    if (!links.length) return null;
    return el("details", {},
      el("summary", {}, `ELD standards that list this standard (${links.length})`),
      el("p", { class: "muted" }, `Each ELD standard has a record for every proficiency level. ` +
        `${source}${reviewedCount(links)}`),
      el("ul", { class: "plain" }, links.map((l) =>
        el("li", { class: "inline" }, el("strong", {}, `ELD ${l.part} standard ${l.number}:`),
          (eldRecords.get(`${l.part}|${l.number}|${l.gmin}`) || []).map((r) =>
            codeButton(r, r.identifier.replace(/^ELD\.P[I]+\./, "")))))));
  }
  return null;
}

// One step forward: what this standard leads on to. Useful for showing how
// below-grade teaching connects to grade-level work.
function forwardPanel(start) {
  const edges = withParent(start.id).flatMap((id) => edgesFrom.get(id) || []);
  if (!edges.length) return null;
  return el("details", {},
    el("summary", {}, `Leads on to (${edges.length})`),
    el("p", { class: "muted" }, "One step forward: the standards that build on this one."),
    el("ul", { class: "plain" }, edges.map((e) => {
      const r = byId.get(e.to);
      return el("li", {}, codeButton(r), ` ${r.grade}. `, r.text, " ",
        el("span", { class: "muted" }, `Source: ${SOURCE_WORDS[e.source] || e.source}. `), reviewChip(e));
    })));
}

function ladder(items, start) {
  const box = el("section", { "aria-label": "Ladder layout" });
  for (const n of new Set(items.map((i) => i.steps))) {
    const level = items.filter((i) => i.steps === n);
    box.append(el("h3", {}, `${plural(n, "step")} back (${level.length})`));
    for (const item of level) {
      box.append(standardCard(item.record, start, { item, how: howReached(item, start) }));
    }
  }
  return box;
}

function table(items, start) {
  const head = ["Steps back", "Standard", "Grade", "Text", "Link", "Source", "Reviewed", ""];
  return el("section", { "aria-label": "Table layout" },
    el("div", { class: "scroll" },
      el("table", {},
        el("thead", {}, el("tr", {}, head.map((h) => el("th", { scope: "col" }, h)))),
        el("tbody", {}, items.map((item) => {
          const r = item.record;
          const link = `${LINK_WORDS[item.edge.type] || item.edge.type} ${item.towards.identifier}` +
                       (item.edge.note ? ` (${item.edge.note})` : "");
          return el("tr", {},
            el("td", {}, item.steps),
            el("th", { scope: "row" }, codeButton(r)),
            el("td", {}, r.grade),
            el("td", { class: "text" }, r.text,
              r.subs.length ? ` [${plural(r.subs.length, "lettered part")}]` : ""),
            el("td", {}, link),
            el("td", {}, SOURCE_WORDS[item.edge.source] || item.edge.source),
            el("td", {}, reviewWords(item.edge)),
            el("td", {}, addButton(entryFor(start, r.identifier, r.grade, r.text, howReached(item, start)))));
        })))));
}

function renderStandard(id, letter) {
  const start = byId.get(id);
  const parent = start.parent === null ? null : byId.get(start.parent);
  const top = document.getElementById("standard");
  top.replaceChildren(standardCard(start, start,
    { cls: "start", how: "the starting standard", letter, title: true }));
  if (parent) {
    top.append(
      el("p", { class: "muted" }, `${start.identifier} is one part of ${parent.identifier}:`),
      standardCard(parent, start, { how: `the whole standard that ${start.identifier} is part of` }));
  }
  const parts = withParent(id).flatMap((p) => DATA.standards.filter((s) => s.parent === p && s.id !== id));
  if (parts.length) {
    top.append(el("p", { class: "muted inline" }, parent ? "Its other parts:" : "CDE records for its parts:",
      parts.map((p) => codeButton(p, p.identifier))));
  }
  document.getElementById("extras").replaceChildren(
    ...[componentsPanel(start, parent), bridgePanel(start), forwardPanel(start)].filter(Boolean));

  const { found, more } = walkBack(id, state.depth);
  document.getElementById("builds-heading").textContent = found.length
    ? `Builds on: ${plural(found.length, "earlier standard")}`
    : "Builds on";
  document.getElementById("layout").replaceChildren(
    ...[["ladder", "Ladder"], ["table", "Table"], ["both", "Both"]].map(([value, name]) =>
      el("button", {
        "aria-pressed": value === state.layout ? "true" : "false",
        onclick: () => { state.layout = value; render(); },
      }, name)));
  const box = document.getElementById("layouts");
  box.className = "layouts" + (state.layout === "both" ? " both" : "");
  const views = [];
  if (!found.length) views.push(el("p", {}, "Nothing is recorded that this standard builds on."));
  else {
    if (state.layout !== "table") views.push(ladder(found, start));
    if (state.layout !== "ladder") views.push(table(found, start));
  }
  box.replaceChildren(...views);

  // Say plainly whether the list above is complete, and offer the next step if not.
  const deeper = document.getElementById("deeper");
  const shownSteps = found.length ? found[found.length - 1].steps : 0;
  if (more) {
    deeper.replaceChildren(el("p", {},
      el("button", { onclick: () => { state.depth = shownSteps + 1; render(); } },
        "Show one more step back"), " ",
      el("button", { onclick: () => { state.depth = 99; render(); } }, "Show all the way back")));
  } else if (found.length) {
    deeper.replaceChildren(el("p", { class: "muted" },
      "That is everything: the recorded links go no further back than this."));
  } else deeper.replaceChildren();
  const select = document.getElementById("depth");
  select.value = [...select.options].some((o) => Number(o.value) === state.depth) ? String(state.depth) : "99";
}

// ---- moving between the screens ----------------------------------------

function openStandard(id, letter) {
  location.hash = `s=${id}` + (letter ? `&part=${letter}` : "");
  window.scrollTo(0, 0);
}

function render() {
  const asked = new URLSearchParams(location.hash.slice(1));
  const id = Number(asked.get("s"));
  const onStandard = asked.has("s") && byId.has(id);
  document.getElementById("view-search").hidden = onStandard;
  document.getElementById("view-standard").hidden = !onStandard;
  if (onStandard) renderStandard(id, asked.get("part"));
  else renderSearch();
  renderCollected();
}

function setUp() {
  buildIndexes();
  loadCollected();
  const reviewed = DATA.edges.filter((e) => e[5]).length;
  document.getElementById("trust").textContent =
    `Prototype. ${reviewed} of the ${DATA.edges.length} links between standards have been reviewed by a teacher. ` +
    "Every link names its source so it can be judged.";

  const grade = document.getElementById("grade");
  grade.append(el("option", { value: "" }, "Any grade"), el("option", { value: 0 }, "K"));
  for (let g = 1; g <= 12; g++) grade.append(el("option", { value: g }, g));
  const courses = [...new Set(DATA.standards.map((s) => s.course).filter(Boolean))];
  courses.sort((a, b) => (COURSE_ORDER.indexOf(a) + 99) % 99 - (COURSE_ORDER.indexOf(b) + 99) % 99 ||
    a.localeCompare(b));
  document.getElementById("course").append(el("option", { value: "" }, "Not known: search every course"),
    ...courses.map((c) => el("option", {}, c)));

  // Each control writes its value into `state` and redraws the results.
  // A search can be opened from the address: index.html#q=regroup&subject=math&grade=2
  const asked = new URLSearchParams(location.hash.slice(1));
  const bind = (elementId, key, event) => {
    const control = document.getElementById(elementId);
    if (asked.has(key) && control.type !== "checkbox") {
      control.value = asked.get(key);
      state[key] = control.value;
    }
    control.addEventListener(event, () => {
      state[key] = control.type === "checkbox" ? control.checked : control.value;
      state.shown = PAGE;
      renderSearch();
    });
  };
  bind("q", "q", "input");
  bind("subject", "subject", "change");
  bind("grade", "grade", "change");
  bind("course", "course", "change");
  bind("level", "level", "change");
  bind("in-components", "inComponents", "change");

  const depth = document.getElementById("depth");
  depth.addEventListener("change", () => { state.depth = Number(depth.value); render(); });
  document.getElementById("back").addEventListener("click", () => { location.hash = ""; });
  document.getElementById("print").addEventListener("click", () => window.print());
  document.getElementById("clear").addEventListener("click", () => {
    state.collected = [];
    saveCollected();
    render();
  });
  document.getElementById("copy").addEventListener("click", async () => {
    const box = document.getElementById("collected-text");
    try {
      await navigator.clipboard.writeText(box.value);
    } catch (error) {
      // A page opened from disk may not be allowed to use the clipboard
      // directly. Selecting the text and asking the browser to copy still works.
      box.select();
      document.execCommand("copy");
    }
    document.getElementById("copied").textContent = "Copied.";
  });
  window.addEventListener("hashchange", render);
  render();
}

if (DATA) setUp();
