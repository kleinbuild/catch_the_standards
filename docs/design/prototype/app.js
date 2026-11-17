// app.js - draws the prototype page from window.PROTOTYPE_DATA (data.js).
//
// Plain JavaScript, no libraries. The page is rebuilt from scratch by render()
// whenever a control changes; with this little data that is instant and keeps
// the code short.

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

// What the teacher has chosen on screen. Nothing here is saved anywhere.
const state = { example: 0, depth: 1, layout: "both", collected: [] };

// el("p", {class: "muted"}, "text", childNode) builds one element. Text is
// always added as text, never as HTML, so nothing in the data can break the page.
function el(tag, attrs, ...children) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs || {})) {
    if (name === "onclick") node.addEventListener("click", value);
    else if (value !== null && value !== undefined && value !== false) node.setAttribute(name, value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return node;
}

function plural(n, word) { return `${n} ${word}${n === 1 ? "" : "s"}`; }

function whereFrom(record) {
  return record.origin === "cde"
    ? `CDE record ${record.id}`
    : "CDE has no record for the whole standard; text from Learning Commons";
}

// The sentence describing one link, e.g. "builds towards 4.NF.3; source: Learning Commons".
function linkSentence(item, start) {
  const isStart = item.towards_id === start.record.id;
  let words = LINK_WORDS[item.type] || item.type;
  if (item.type === "builds_towards") words += ` ${item.towards}`;
  else if (!isStart) words += ` (towards ${item.towards})`;
  let text = `${words}; source: ${SOURCE_WORDS[item.source] || item.source}`;
  if (item.note) text += `; ${item.note}`;
  return text;
}

function reviewChip(reviewed) {
  return el("span", { class: reviewed ? "chip" : "chip no" }, reviewed ? "Reviewed" : "Not reviewed");
}

// ---- collected list ----------------------------------------------------

function addButton(entry) {
  const have = state.collected.some((c) => c.code === entry.code && c.start === entry.start);
  return el("button", {
    class: "small add", "aria-pressed": have ? "true" : "false",
    "aria-label": `${have ? "Remove" : "Add"} ${entry.code}`,
    onclick: () => {
      const at = state.collected.findIndex((c) => c.code === entry.code && c.start === entry.start);
      if (at >= 0) state.collected.splice(at, 1); else state.collected.push(entry);
      render();
    },
  }, have ? "Added" : "Add");
}

function collectedText() {
  const lines = [];
  const starts = [...new Set(state.collected.map((c) => c.start))];
  for (const start of starts) {
    lines.push(`Started from ${start}`);
    for (const c of state.collected.filter((x) => x.start === start)) {
      lines.push(`- ${c.code}${c.grade ? ` (${c.grade})` : ""}: ${c.text}`);
      lines.push(`  How it was reached: ${c.how}`);
    }
    lines.push("");
  }
  return lines.join("\n").trim();
}

function renderCollected() {
  const list = document.getElementById("collected-list");
  list.replaceChildren(state.collected.length
    ? el("p", {}, plural(state.collected.length, "item") + " collected.")
    : el("p", { class: "muted" }, "Nothing collected yet."));
  document.getElementById("collected-text").value = collectedText();
}

// ---- the chosen standard -----------------------------------------------

function standardCard(record, start, options) {
  // options: {cls, link (item from `back`), how, letter}
  const o = options || {};
  const entry = (code, text) => ({
    start: `${start.record.identifier} (${start.record.grade})`,
    code, grade: record.grade, text, how: o.how,
  });
  return el("div", { class: `card ${o.cls || ""}` },
    el("div", { class: "head" },
      el("span", { class: "code" }, record.label),
      el("span", {}, record.grade),
      record.url
        ? el("a", { href: record.url, target: "_blank", rel: "noopener" }, whereFrom(record))
        : el("span", { class: "muted" }, whereFrom(record)),
      addButton(entry(record.identifier, record.text))),
    el("p", {}, record.text),
    record.parts.length
      ? el("p", { class: "muted" }, "CDE records for its parts: " + record.parts.join(", "))
      : null,
    record.subs.length
      ? el("ol", { class: "subs" }, record.subs.map((s) =>
          el("li", { class: s.letter === o.letter ? "marked" : null },
            el("span", {}, `${s.letter}. ${s.text}`),
            addButton(entry(`${record.identifier}${s.letter}`, s.text)))))
      : null,
    o.link
      ? el("p", { class: "link" }, linkSentence(o.link, start), " ", reviewChip(o.link.reviewed))
      : null);
}

function renderStandard(start) {
  const box = document.getElementById("standard");
  box.replaceChildren(
    standardCard(start.record, start, { cls: "start", how: "the starting standard", letter: start.letter }));
  if (start.parent) {
    box.append(
      el("p", { class: "muted" }, `${start.record.identifier} is one part of ${start.parent.identifier}:`),
      standardCard(start.parent, start, { how: `the whole standard that ${start.record.identifier} is part of` }));
  }
}

function componentList(items, start, owner) {
  return el("ul", { class: "plain" }, items.map((c) =>
    el("li", {},
      c.letter ? el("strong", {}, `${c.letter}. `) : null, c.text, " ",
      addButton({
        start: `${start.record.identifier} (${start.record.grade})`,
        code: `Learning component of ${owner}${c.letter || ""}`, grade: "", text: c.text,
        how: `listed by Learning Commons for ${owner}; written by ${c.author}; ` +
             (c.reviewed ? "reviewed" : "not reviewed"),
      }))));
}

function renderExtras(start) {
  const box = document.getElementById("extras");
  const parts = [];

  const own = start.components, fromParent = start.parent_components;
  if (own.length || fromParent.length) {
    const authors = [...new Set([...own, ...fromParent].map((c) => c.author))].join(", ");
    parts.push(el("details", {},
      el("summary", {}, `Learning components (${own.length + fromParent.length})`),
      el("p", { class: "muted" },
        `The teachable pieces of the standard, written by ${authors}. Not reviewed.`),
      own.length ? [el("h3", {}, `For ${start.record.identifier}`),
                    componentList(own, start, start.record.identifier)] : null,
      fromParent.length ? [el("h3", {}, `For the whole standard ${start.parent.identifier}`),
                           componentList(fromParent, start, start.parent.identifier)] : null));
  } else {
    parts.push(el("p", { class: "muted" }, "No learning components are listed for this standard. " +
      "The data has them for math, and for ELA in grades K–2 only."));
  }

  if (start.bridge) {
    const b = start.bridge;
    parts.push(el("details", {},
      el("summary", {}, `ELA and ELD together (${b.count})`),
      el("p", {}, b.title),
      el("p", { class: "muted" },
        `Source: notes on Learning Commons' California ELD items. ` +
        `${b.reviewed} of ${b.count} reviewed.`),
      el("ul", { class: "plain" }, b.groups.map((g) =>
        el("li", {}, el("strong", {}, g.name + ": "), g.items.join(", "))))));
  }
  box.replaceChildren(...parts);
}

// ---- the two layouts ---------------------------------------------------

function howReached(item, start) {
  return `${plural(item.steps, "step")} back from ${start.record.identifier}; ` +
         `${linkSentence(item, start)}; ${item.reviewed ? "reviewed" : "not reviewed"}`;
}

function ladder(items, start) {
  const box = el("section", { "aria-label": "Ladder layout" }, el("h3", {}, "Ladder"));
  const steps = [...new Set(items.map((i) => i.steps))];
  for (const n of steps) {
    const level = items.filter((i) => i.steps === n);
    box.append(el("h3", {}, `${plural(n, "step")} back (${level.length})`));
    for (const item of level) {
      box.append(standardCard(item.record, start, { link: item, how: howReached(item, start) }));
    }
  }
  return box;
}

function table(items, start) {
  const head = ["Steps back", "Standard", "Grade", "Text", "Link", "Source", "Reviewed", ""];
  return el("section", { "aria-label": "Table layout" },
    el("h3", {}, "Table"),
    el("div", { class: "scroll" },
      el("table", {},
        el("thead", {}, el("tr", {}, head.map((h) => el("th", { scope: "col" }, h)))),
        el("tbody", {}, items.map((item) => {
          const r = item.record;
          const link = (LINK_WORDS[item.type] || item.type) + " " + item.towards +
                       (item.note ? ` (${item.note})` : "");
          const text = r.text + (r.subs.length ? ` [${plural(r.subs.length, "lettered part")}]` : "");
          return el("tr", {},
            el("td", {}, item.steps),
            el("th", { scope: "row" },
              r.url ? el("a", { href: r.url, target: "_blank", rel: "noopener" }, r.label) : r.label),
            el("td", {}, r.grade),
            el("td", { class: "text" }, text),
            el("td", {}, link),
            el("td", {}, SOURCE_WORDS[item.source] || item.source),
            el("td", {}, item.reviewed ? "Yes" : "No"),
            el("td", {}, addButton({
              start: `${start.record.identifier} (${start.record.grade})`,
              code: r.identifier, grade: r.grade, text: r.text, how: howReached(item, start),
            })));
        })))));
}

function renderLayouts(start) {
  const items = start.back.filter((i) => i.steps <= state.depth);
  const box = document.getElementById("layouts");
  box.className = "layouts" + (state.layout === "both" ? " both" : "");
  document.getElementById("builds-heading").textContent =
    `Builds on: ${plural(items.length, "earlier standard")} within ${plural(state.depth, "step")}`;
  if (!items.length) {
    box.replaceChildren(el("p", {}, "Nothing is recorded that this standard builds on."));
    return;
  }
  const parts = [];
  if (state.layout !== "table") parts.push(ladder(items, start));
  if (state.layout !== "ladder") parts.push(table(items, start));
  const deeper = start.back.some((i) => i.steps > state.depth) || start.more;
  if (deeper) parts.push(el("p", { class: "muted" }, "More lies further back."));
  box.replaceChildren(...parts);
}

// ---- controls ----------------------------------------------------------

function renderControls() {
  document.getElementById("pick").replaceChildren(...DATA.examples.map((e, i) =>
    el("button", {
      "aria-pressed": i === state.example ? "true" : "false",
      onclick: () => { state.example = i; render(); },
    }, e.key)));
  document.getElementById("layout").replaceChildren(
    ...[["ladder", "Ladder"], ["table", "Table"], ["both", "Both"]].map(([value, name]) =>
      el("button", {
        "aria-pressed": value === state.layout ? "true" : "false",
        onclick: () => { state.layout = value; render(); },
      }, name)));
}

function render() {
  const start = DATA.examples[state.example];
  renderControls();
  renderStandard(start);
  renderExtras(start);
  renderLayouts(start);
  renderCollected();
}

function setUp() {
  const all = DATA.examples.flatMap((e) => e.back);
  const reviewed = all.filter((i) => i.reviewed).length;
  document.getElementById("trust").textContent =
    `${reviewed} of the ${all.length} links shown on this page have been reviewed. ` +
    "Each link names its source so it can be judged. The data holds no confidence rating yet, so none is shown.";

  // A view can be opened directly: index.html#example=1&depth=2&layout=ladder
  const asked = new URLSearchParams(location.hash.slice(1));
  if (DATA.examples[Number(asked.get("example"))]) state.example = Number(asked.get("example"));
  if (Number(asked.get("depth")) >= 1 && Number(asked.get("depth")) <= DATA.depth) state.depth = Number(asked.get("depth"));
  if (["ladder", "table", "both"].includes(asked.get("layout"))) state.layout = asked.get("layout");

  const depth = document.getElementById("depth");
  for (let n = 1; n <= DATA.depth; n++) depth.append(el("option", { value: n }, plural(n, "step")));
  depth.value = String(state.depth);
  depth.addEventListener("change", () => { state.depth = Number(depth.value); render(); });

  document.getElementById("print").addEventListener("click", () => window.print());
  document.getElementById("clear").addEventListener("click", () => { state.collected = []; render(); });
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
  render();
}

setUp();
