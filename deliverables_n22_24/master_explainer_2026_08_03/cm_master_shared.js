/* CM master knowledge base — shared render library.
   Injected into every page by cm_master_build_2026_08_03.py at the
   /*__CM_LIB__*​/ marker, after `const DATA = …` is defined.

   Contract: this file NEVER contains a measured result. Every number reaches
   the page through DATA (evidence arrays) or through DATA._numbers (named
   tokens the build script read from an evidence file). Prose in the content
   file writes a double-brace token; `P()` resolves it here against `_numbers`,
   and the build script refuses to build if a token has no backing evidence. */

/* ---------------------------------------------------------------- colour */
const S1 = "var(--series-1)", S2 = "var(--series-2)", S3 = "var(--series-3)", S4 = "var(--series-4)";

/* ---------------------------------------------------------------- dom */
const el = (t, a = {}, kids = []) => {
  const n = document.createElementNS("http://www.w3.org/2000/svg", t);
  for (const k in a) if (a[k] !== null && a[k] !== undefined) n.setAttribute(k, a[k]);
  for (const c of [].concat(kids)) n.append(c);
  return n;
};
const h = (t, a = {}, kids = []) => {
  const n = document.createElement(t);
  for (const k in a) {
    if (k === "html") n.innerHTML = a[k];
    else if (k === "text") n.textContent = a[k];
    else n.setAttribute(k, a[k]);
  }
  for (const c of [].concat(kids)) if (c) n.append(c);
  return n;
};
const frag = (kids) => { const d = document.createDocumentFragment(); [].concat(kids).forEach(c => c && d.append(c)); return d; };

/* ---------------------------------------------------------------- format */
const f = (x, d = 3) => (x === null || x === undefined) ? "—" : Number(x).toFixed(d);
const us = (x) => x === null || x === undefined ? "—"
  : x >= 100000 ? (x / 1000).toFixed(0) + " ms"
  : x >= 1000 ? (x / 1000).toFixed(x >= 10000 ? 1 : 2) + " ms"
  : x.toFixed(x < 10 ? 2 : 1) + " µs";
const commas = (x) => Number(x).toLocaleString("en-US");

const FMT = {
  ratio2: (v) => Number(v).toFixed(2),
  ratio3: (v) => Number(v).toFixed(3),
  ratio4: (v) => Number(v).toFixed(4),
  num1: (v) => Number(v).toFixed(1),
  /* Repetition counts: one decimal when it carries information, none when it
     would render a spurious tenth on a whole number ("78" not "78.0"). */
  num1s: (v) => Number(v).toFixed(1).replace(/\.0$/, ""),
  int: (v) => commas(Math.round(v)),
  big: (v) => commas(Math.round(v)),
  x0: (v) => commas(Math.round(v)) + "×",
  x1: (v) => Number(v).toFixed(1) + "×",
  x2: (v) => Number(v).toFixed(2) + "×",
  xcomma: (v) => commas(Math.round(v)) + "×",
  pct0: (v) => Math.round(v) + "%",
  pct1: (v) => Number(v).toFixed(1) + "%",
  pct2: (v) => Number(v).toFixed(2) + "%",
  pctsign2: (v) => (v >= 0 ? "+" : "") + Number(v).toFixed(2) + "%",
  us0: (v) => us(v),
  ms0: (v) => Number(v).toFixed(v < 10 ? 1 : 0) + " ms",
  usd: (v) => "$" + Number(v).toFixed(4),
  text: (v) => String(v),
};

/* Named-number lookup. Fails loudly rather than rendering a blank. */
const NUM = DATA._numbers;
function T(token) {
  const rec = NUM[token];
  if (!rec) { console.error("unknown number token:", token); return "‹?" + token + "›"; }
  return (FMT[rec.fmt] || FMT.text)(rec.value);
}
function TV(token) {
  const rec = NUM[token];
  if (!rec) { console.error("unknown number token:", token); return NaN; }
  return rec.value;
}
/* Resolve double-brace tokens in authored prose. Each resolved number is wrapped in a
   span carrying its provenance, so hovering any figure on the page shows the
   file and field it was read from. */
function P(s) {
  if (s == null) return "";
  return String(s).replace(/\{\{([a-zA-Z0-9_.]+)\}\}/g, (_, tok) => {
    const rec = NUM[tok];
    if (!rec) { console.error("unknown number token:", tok); return "‹?" + tok + "›"; }
    const val = (FMT[rec.fmt] || FMT.text)(rec.value);
    const title = (rec.prov + (rec.note ? " — " + rec.note : "")).replace(/"/g, "&quot;");
    return `<span class="num" title="${title}">${val}</span>`;
  });
}

/* ---------------------------------------------------------------- tooltip */
const tip = (() => {
  let n = document.getElementById("tip");
  if (!n) { n = h("div", { id: "tip", role: "status", "aria-live": "polite" }); document.body.prepend(n); }
  return n;
})();
function bindTip(node, html) {
  const show = (e) => {
    tip.innerHTML = html;
    tip.style.opacity = 1;
    const r = tip.getBoundingClientRect();
    let x = e.clientX + 14, y = e.clientY + 14;
    if (x + r.width > innerWidth - 8) x = e.clientX - r.width - 14;
    if (y + r.height > innerHeight - 8) y = e.clientY - r.height - 14;
    tip.style.left = x + "px"; tip.style.top = y + "px";
  };
  node.addEventListener("mousemove", show);
  node.addEventListener("mouseenter", show);
  node.addEventListener("mouseleave", () => tip.style.opacity = 0);
  node.setAttribute("tabindex", "0");
  node.addEventListener("focus", () => {
    const b = node.getBoundingClientRect();
    show({ clientX: b.left + b.width / 2, clientY: b.top });
  });
  node.addEventListener("blur", () => tip.style.opacity = 0);
}

/* ---------------------------------------------------------------- scales */
const linScale = (d0, d1, r0, r1) => (v) => r0 + (v - d0) / (d1 - d0) * (r1 - r0);
const logScale = (d0, d1, r0, r1) => {
  const l0 = Math.log10(d0), l1 = Math.log10(d1);
  return (v) => r0 + (Math.log10(v) - l0) / (l1 - l0) * (r1 - r0);
};
/* Domain helper. Hard-coded axis literals silently clip data when the evidence
   moves under them, so every ratio axis derives its domain from the values it is
   about to draw (plus any reference line). */
const pad = (vals, m) => {
  const v = vals.filter(x => x != null && isFinite(x));
  return [Math.min(...v) - m, Math.max(...v) + m];
};
function niceTicks(lo, hi, n = 5) {
  const raw = (hi - lo) / n;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= raw) || 10 * mag;
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(10));
  return out;
}
function logTicks(lo, hi) {
  const out = [];
  for (let e = Math.floor(Math.log10(lo)); e <= Math.ceil(Math.log10(hi)); e++) {
    const v = Math.pow(10, e);
    if (v >= lo * 0.999 && v <= hi * 1.001) out.push(v);
  }
  return out;
}

/* ---------------------------------------------------------------- card */
function card(o) {
  const c = h("section", { class: "card", id: o.id });
  if (o.scope) c.append(h("p", { class: "scope", text: o.scope }));
  c.append(h(o.h || "h2", { text: o.title }));
  if (o.caption) c.append(h("p", { class: "caption", html: P(o.caption) }));
  if (o.legend) {
    const lg = h("div", { class: "legend" });
    o.legend.forEach(([col, lab]) =>
      lg.append(h("span", {}, [h("i", { style: `background:${col}` }), h("span", { text: lab })])));
    c.append(lg);
  }
  if (o.svg) c.append(h("div", { class: "figwrap" }, [o.svg]));
  if (o.svg2) c.append(h("div", { class: "figwrap" }, [o.svg2]));
  if (o.visual) c.append(o.visual);
  if (o.note) c.append(h("p", { class: "claim", html: P(o.note) }));
  if (o.table) {
    const d = h("details");
    d.append(h("summary", { text: "Table view (every plotted value)" }));
    d.append(h("div", { class: "tablewrap" }, [o.table]));
    c.append(d);
  }
  if (o.prov) {
    const d = h("details", { class: "prov" });
    d.append(h("summary", { text: "Data provenance" }));
    const ul = h("ul");
    o.prov.forEach(p => ul.append(h("li", { html: `<code>${p.replace("::", "</code> :: <code>")}</code>` })));
    d.append(ul);
    c.append(d);
  }
  if (o.claim) c.append(h("p", { class: "claim", html: P(o.claim) }));
  return c;
}
function table(headers, rows, cls) {
  const t = h("table", cls ? { class: cls } : {});
  const th = h("tr");
  headers.forEach(x => th.append(h("th", { html: x })));
  t.append(h("thead", {}, [th]));
  const tb = h("tbody");
  rows.forEach(r => {
    const tr = h("tr");
    r.forEach(x => tr.append(h("td", { html: String(x) })));
    tb.append(tr);
  });
  t.append(tb);
  return t;
}

/* --------------------------------------------- forest (dot + CI, horizontal) */
function forest(rows, opt) {
  const W = opt.width || 900, padL = opt.padL || 250, padR = 92, padT = 30, rowH = 30;
  const H = padT + rows.length * rowH + 46;
  const lo = opt.domain[0], hi = opt.domain[1];
  const x = linScale(lo, hi, padL, W - padR);
  const g = el("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: "img",
                        "aria-label": opt.title || "forest plot" });

  niceTicks(lo, hi, opt.ticks || 6).forEach(t => {
    g.append(el("line", { x1: x(t), x2: x(t), y1: padT - 8, y2: padT + rows.length * rowH,
                          stroke: "var(--grid)", "stroke-width": 1 }));
    g.append(el("text", { x: x(t), y: padT + rows.length * rowH + 18, class: "tick",
                          "text-anchor": "middle" }, [document.createTextNode(f(t, 2))]));
  });
  if (opt.ref !== undefined && opt.ref >= lo && opt.ref <= hi) {
    g.append(el("line", { x1: x(opt.ref), x2: x(opt.ref), y1: padT - 12, y2: padT + rows.length * rowH,
                          stroke: "var(--ref)", "stroke-width": 1.5 }));
    g.append(el("text", { x: x(opt.ref), y: padT - 17, class: "axtitle", "text-anchor": "middle" },
                        [document.createTextNode(opt.refLabel || "parity 1.00")]));
  }
  g.append(el("text", { x: (padL + W - padR) / 2, y: H - 8, class: "axtitle", "text-anchor": "middle" },
                      [document.createTextNode(opt.xTitle)]));

  rows.forEach((r, i) => {
    const cy = padT + i * rowH + rowH / 2;
    const col = r.group === "pod" ? S3 : r.group === "external" ? S2 : S1;
    g.append(el("text", { x: padL - 12, y: cy + 4, class: "lab", "text-anchor": "end" },
                        [document.createTextNode(r.label)]));
    if (r.lo !== null && r.lo !== undefined) {
      g.append(el("line", { x1: x(r.lo), x2: x(r.hi), y1: cy, y2: cy, stroke: col, "stroke-width": 2,
                            "stroke-linecap": "round" }));
      [r.lo, r.hi].forEach(v => g.append(el("line", { x1: x(v), x2: x(v), y1: cy - 5, y2: cy + 5,
                                                      stroke: col, "stroke-width": 2 })));
    }
    g.append(el("circle", { cx: x(r.value), cy, r: 5.5, fill: col,
                            stroke: "var(--surface-1)", "stroke-width": 2 }));
    g.append(el("text", { x: W - padR + 10, y: cy + 4, class: "val" },
                        [document.createTextNode(f(r.value, 4))]));
    const hit = el("rect", { x: padL - 4, y: cy - rowH / 2, width: W - padR - padL + 8, height: rowH, class: "hit" });
    bindTip(hit, `<b>${r.label}</b><span class="r">${opt.arm}: ${f(r.value, 4)}` +
      (r.lo != null ? ` &nbsp;95% CI [${f(r.lo, 4)}, ${f(r.hi, 4)}]` : "") +
      `</span><br><span class="r">${r.scope}</span><br><span class="r">${r.basis}</span>`);
    g.append(hit);
  });
  return g;
}

/* ---------------------------------------------------- grouped columns */
function groupedCols(cfg) {
  const W = cfg.width || 900, padL = cfg.padL || 74, padR = 22, padT = 22, padB = cfg.padB || 62;
  const H = cfg.height || 320;
  const groups = cfg.groups, series = cfg.series;
  const plotW = W - padL - padR, plotH = H - padT - padB;
  const isLog = !!cfg.log;
  const allV = groups.flatMap(g => series.map(s => g.values[s.key]).filter(v => v != null && (!isLog || v > 0)));
  const maxV = cfg.max || Math.max(...allV) * 1.12;
  const minV = isLog ? (cfg.min || Math.pow(10, Math.floor(Math.log10(Math.min(...allV))))) : 0;
  const y = isLog ? logScale(minV, maxV, padT + plotH, padT) : linScale(minV, maxV, padT + plotH, padT);
  const g = el("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: "img",
                        "aria-label": cfg.title || "grouped columns" });

  (isLog ? logTicks(minV, maxV) : niceTicks(minV, maxV, 5)).forEach(t => {
    g.append(el("line", { x1: padL, x2: W - padR, y1: y(t), y2: y(t), stroke: "var(--grid)", "stroke-width": 1 }));
    g.append(el("text", { x: padL - 10, y: y(t) + 4, class: "tick", "text-anchor": "end" },
                        [document.createTextNode(cfg.fmtTick ? cfg.fmtTick(t) : f(t, cfg.tickDigits ?? 2))]));
  });
  g.append(el("line", { x1: padL, x2: W - padR, y1: padT + plotH, y2: padT + plotH,
                        stroke: "var(--axis)", "stroke-width": 1 }));
  if (cfg.ref != null) {
    g.append(el("line", { x1: padL, x2: W - padR, y1: y(cfg.ref), y2: y(cfg.ref),
                          stroke: "var(--ref)", "stroke-width": 1.5 }));
    g.append(el("text", { x: W - padR - 2, y: y(cfg.ref) - 6, class: "axtitle", "text-anchor": "end" },
                        [document.createTextNode(cfg.refLabel || "parity 1.00")]));
  }
  g.append(el("text", { x: 16, y: padT + plotH / 2, class: "axtitle", "text-anchor": "middle",
                        transform: `rotate(-90 16 ${padT + plotH / 2})` },
                      [document.createTextNode(cfg.yTitle)]));
  g.append(el("text", { x: padL + plotW / 2, y: H - 8, class: "axtitle", "text-anchor": "middle" },
                      [document.createTextNode(cfg.xTitle)]));

  const bandW = plotW / groups.length;
  const inner = Math.min(cfg.barW || 24, (bandW - 26) / series.length);
  groups.forEach((grp, gi) => {
    const cx = padL + bandW * (gi + 0.5);
    const total = series.length * inner + (series.length - 1) * 2;
    series.forEach((s, si) => {
      const v = grp.values[s.key];
      if (v == null || (isLog && v <= 0)) return;
      const bx = cx - total / 2 + si * (inner + 2);
      const by = y(v), bh = Math.max(1, padT + plotH - by);
      const r = Math.min(4, bh / 2);
      const path = `M${bx},${by + bh} L${bx},${by + r} Q${bx},${by} ${bx + r},${by}` +
                   ` L${bx + inner - r},${by} Q${bx + inner},${by} ${bx + inner},${by + r}` +
                   ` L${bx + inner},${by + bh} Z`;
      const bar = el("path", { d: path, fill: s.color });
      bindTip(bar, `<b>${grp.label} · ${s.label}</b><span class="r">${cfg.fmtVal ? cfg.fmtVal(v) : f(v, 3)}</span>` +
        (grp.tip ? `<br><span class="r">${grp.tip}</span>` : ""));
      g.append(bar);
      if (cfg.labelBars) {
        g.append(el("text", { x: bx + inner / 2, y: by - 6, class: "val", "text-anchor": "middle",
                              "font-size": 10.5 },
                            [document.createTextNode(cfg.fmtVal ? cfg.fmtVal(v) : f(v, 2))]));
      }
    });
    g.append(el("text", { x: cx, y: padT + plotH + 18, class: "lab", "text-anchor": "middle" },
                        [document.createTextNode(grp.label)]));
    if (grp.sub) g.append(el("text", { x: cx, y: padT + plotH + 33, class: "tick", "text-anchor": "middle",
                                       "font-size": 11 }, [document.createTextNode(grp.sub)]));
  });
  return g;
}

/* ------------------------------------- dumbbell (2 series, horizontal cats) */
function dumbbell(cats, cfg) {
  const W = cfg.width || 900, padL = cfg.padL || 175, padR = 30, padT = 26, rowH = cfg.rowH || 24;
  const H = padT + cats.length * rowH + 48;
  const x = linScale(cfg.domain[0], cfg.domain[1], padL, W - padR);
  const g = el("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": cfg.title });
  niceTicks(cfg.domain[0], cfg.domain[1], 6).forEach(t => {
    g.append(el("line", { x1: x(t), x2: x(t), y1: padT - 6, y2: padT + cats.length * rowH,
                          stroke: "var(--grid)", "stroke-width": 1 }));
    g.append(el("text", { x: x(t), y: padT + cats.length * rowH + 18, class: "tick", "text-anchor": "middle" },
                        [document.createTextNode(f(t, 2))]));
  });
  if (cfg.ref != null) {
    g.append(el("line", { x1: x(cfg.ref), x2: x(cfg.ref), y1: padT - 12, y2: padT + cats.length * rowH,
                          stroke: "var(--ref)", "stroke-width": 1.5 }));
    g.append(el("text", { x: x(cfg.ref), y: padT - 17, class: "axtitle", "text-anchor": "middle" },
                        [document.createTextNode("parity 1.00")]));
  }
  g.append(el("text", { x: (padL + W - padR) / 2, y: H - 8, class: "axtitle", "text-anchor": "middle" },
                      [document.createTextNode(cfg.xTitle)]));
  cats.forEach((c, i) => {
    const cy = padT + i * rowH + rowH / 2;
    g.append(el("text", { x: padL - 12, y: cy + 4, class: "lab", "text-anchor": "end" },
                        [document.createTextNode(c.label)]));
    g.append(el("line", { x1: x(Math.min(c.a, c.b)), x2: x(Math.max(c.a, c.b)), y1: cy, y2: cy,
                          stroke: "var(--axis)", "stroke-width": 2, "stroke-linecap": "round" }));
    g.append(el("circle", { cx: x(c.b), cy, r: 4.5, fill: S2, stroke: "var(--surface-1)", "stroke-width": 2 }));
    g.append(el("circle", { cx: x(c.a), cy, r: 4.5, fill: S1, stroke: "var(--surface-1)", "stroke-width": 2 }));
    const hit = el("rect", { x: padL - 4, y: cy - rowH / 2, width: W - padR - padL + 8, height: rowH, class: "hit" });
    bindTip(hit, `<b>${c.label}</b><span class="r">${cfg.aLabel}: ${f(c.a, 4)}<br>${cfg.bLabel}: ${f(c.b, 4)}</span>` +
      (c.tip ? `<br><span class="r">${c.tip}</span>` : ""));
    g.append(hit);
  });
  return g;
}

/* ------------------------------------------------- xy scatter / lines */
function xyPlot(cfg) {
  const W = cfg.width || 900, padL = cfg.padL || 78, padR = cfg.padR || 30, padT = 24, padB = 58;
  const H = cfg.height || 320, plotW = W - padL - padR, plotH = H - padT - padB;
  const x = cfg.logX ? logScale(cfg.xDomain[0], cfg.xDomain[1], padL, W - padR)
                     : linScale(cfg.xDomain[0], cfg.xDomain[1], padL, W - padR);
  const y = cfg.logY ? logScale(cfg.yDomain[0], cfg.yDomain[1], padT + plotH, padT)
                     : linScale(cfg.yDomain[0], cfg.yDomain[1], padT + plotH, padT);
  const g = el("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": cfg.title });

  (cfg.logY ? logTicks(cfg.yDomain[0], cfg.yDomain[1]) : niceTicks(cfg.yDomain[0], cfg.yDomain[1], 5)).forEach(t => {
    g.append(el("line", { x1: padL, x2: W - padR, y1: y(t), y2: y(t), stroke: "var(--grid)", "stroke-width": 1 }));
    g.append(el("text", { x: padL - 10, y: y(t) + 4, class: "tick", "text-anchor": "end" },
                        [document.createTextNode(cfg.fmtY ? cfg.fmtY(t) : f(t, 2))]));
  });
  (cfg.xTicks || (cfg.logX ? logTicks(cfg.xDomain[0], cfg.xDomain[1]) : niceTicks(cfg.xDomain[0], cfg.xDomain[1], 6)))
    .forEach(t => {
      g.append(el("text", { x: x(t), y: padT + plotH + 18, class: "tick", "text-anchor": "middle" },
                          [document.createTextNode(cfg.fmtX ? cfg.fmtX(t) : f(t, 0))]));
    });
  g.append(el("line", { x1: padL, x2: W - padR, y1: padT + plotH, y2: padT + plotH,
                        stroke: "var(--axis)", "stroke-width": 1 }));
  if (cfg.ref != null) {
    g.append(el("line", { x1: padL, x2: W - padR, y1: y(cfg.ref), y2: y(cfg.ref),
                          stroke: "var(--ref)", "stroke-width": 1.5, "stroke-dasharray": "4 3" }));
    g.append(el("text", { x: W - padR - 2, y: y(cfg.ref) - 6, class: "axtitle", "text-anchor": "end" },
                        [document.createTextNode(cfg.refLabel || "parity 1.00")]));
  }
  g.append(el("text", { x: 16, y: padT + plotH / 2, class: "axtitle", "text-anchor": "middle",
                        transform: `rotate(-90 16 ${padT + plotH / 2})` },
                      [document.createTextNode(cfg.yTitle)]));
  g.append(el("text", { x: padL + plotW / 2, y: H - 8, class: "axtitle", "text-anchor": "middle" },
                      [document.createTextNode(cfg.xTitle)]));

  cfg.series.forEach(s => {
    if (s.line) {
      const d = s.points.map((p, i) => `${i ? "L" : "M"}${x(p.x)},${y(p.y)}`).join(" ");
      g.append(el("path", { d, fill: "none", stroke: s.color, "stroke-width": 2,
                            "stroke-dasharray": s.dash || null,
                            "stroke-linejoin": "round", "stroke-linecap": "round" }));
    }
    s.points.forEach(p => {
      g.append(el("circle", { cx: x(p.x), cy: y(p.y), r: s.r || 4.5, fill: s.color,
                              stroke: "var(--surface-1)", "stroke-width": 2 }));
      const hit = el("circle", { cx: x(p.x), cy: y(p.y), r: 13, class: "hit" });
      bindTip(hit, `<b>${p.label || s.label}</b><span class="r">${p.tip}</span>`);
      g.append(hit);
      if (p.direct) {
        g.append(el("text", { x: x(p.x) + (p.dx || 0), y: y(p.y) - 12, class: "val",
                              "text-anchor": p.anchor || "middle", "font-size": 11 },
                            [document.createTextNode(p.direct)]));
      }
    });
  });
  return g;
}

/* ------------------------------------------------- horizontal bar (single) */
function hBars(rows, cfg) {
  const W = cfg.width || 880, padL = cfg.padL || 190, padR = 74, padT = 22, rowH = cfg.rowH || 26;
  const H = padT + rows.length * rowH + 44;
  const maxV = cfg.max || Math.max(...rows.map(r => r.value)) * 1.1;
  const x = linScale(0, maxV, padL, W - padR);
  const g = el("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": cfg.title });
  niceTicks(0, maxV, 5).forEach(t => {
    g.append(el("line", { x1: x(t), x2: x(t), y1: padT - 6, y2: padT + rows.length * rowH,
                          stroke: "var(--grid)", "stroke-width": 1 }));
    g.append(el("text", { x: x(t), y: padT + rows.length * rowH + 18, class: "tick", "text-anchor": "middle" },
                        [document.createTextNode(cfg.fmtTick ? cfg.fmtTick(t) : f(t, 0))]));
  });
  if (cfg.ref != null && cfg.ref >= 0 && cfg.ref <= maxV) {
    g.append(el("line", { x1: x(cfg.ref), x2: x(cfg.ref), y1: padT - 9, y2: padT + rows.length * rowH,
                          stroke: "var(--ref)", "stroke-width": 1.5 }));
    g.append(el("text", { x: x(cfg.ref), y: padT - 13, class: "axtitle", "text-anchor": "middle" },
                        [document.createTextNode(cfg.refLabel || String(cfg.ref))]));
  }
  g.append(el("text", { x: (padL + W - padR) / 2, y: H - 6, class: "axtitle", "text-anchor": "middle" },
                      [document.createTextNode(cfg.xTitle)]));
  rows.forEach((r, i) => {
    const cy = padT + i * rowH + rowH / 2, bh = Math.min(15, rowH - 9);
    g.append(el("text", { x: padL - 12, y: cy + 4, class: "lab", "text-anchor": "end" },
                        [document.createTextNode(r.label)]));
    const bar = el("rect", { x: padL, y: cy - bh / 2, width: Math.max(1, x(r.value) - padL), height: bh,
                             rx: 3, fill: r.color || cfg.color || S1 });
    bindTip(bar, `<b>${r.label}</b><span class="r">${cfg.fmtVal ? cfg.fmtVal(r.value) : f(r.value, 2)}</span>` +
      (r.tip ? `<br><span class="r">${r.tip}</span>` : ""));
    g.append(bar);
    g.append(el("text", { x: x(r.value) + 8, y: cy + 4, class: "val", "font-size": 11.5 },
                        [document.createTextNode(cfg.fmtVal ? cfg.fmtVal(r.value) : f(r.value, 2))]));
  });
  return g;
}

/* ----------------------------------- 100% stacked horizontal outcome bars */
function stackedPercentBars(rows, cfg) {
  const W = cfg.width || 900, padL = cfg.padL || 245, padR = 128, padT = 30, rowH = cfg.rowH || 46;
  const H = padT + rows.length * rowH + 46;
  const x = linScale(0, 100, padL, W - padR);
  const g = el("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": cfg.title });
  [0, 25, 50, 75, 100].forEach(t => {
    g.append(el("line", { x1: x(t), x2: x(t), y1: padT - 8, y2: padT + rows.length * rowH,
                          stroke: "var(--grid)", "stroke-width": 1 }));
    g.append(el("text", { x: x(t), y: padT + rows.length * rowH + 18, class: "tick", "text-anchor": "middle" },
                        [document.createTextNode(t + "%")]));
  });
  g.append(el("text", { x: (padL + W - padR) / 2, y: H - 7, class: "axtitle", "text-anchor": "middle" },
                      [document.createTextNode("share of expressions in the arm")]));
  rows.forEach((r, i) => {
    const cy = padT + i * rowH + rowH / 2;
    const finitePct = 100 * r.finite / r.total, neverPct = 100 - finitePct;
    g.append(el("text", { x: padL - 12, y: cy - 3, class: "lab", "text-anchor": "end" },
                        [document.createTextNode(r.label)]));
    g.append(el("text", { x: padL - 12, y: cy + 13, class: "tick", "text-anchor": "end", "font-size": 10.5 },
                        [document.createTextNode("vs " + r.baseline)]));
    const finite = el("rect", { x: x(0), y: cy - 9, width: x(finitePct) - x(0), height: 18, rx: 4, fill: S1 });
    const never = el("rect", { x: x(finitePct), y: cy - 9, width: x(100) - x(finitePct), height: 18,
                               rx: 4, fill: "var(--critical)" });
    bindTip(finite, `<b>${r.label}</b><span class="r">${r.finite}/${r.total} finite break-even (${f(finitePct, 1)}%)<br>` +
      `finite median ${FMT.num1s(r.median)} evaluations</span>`);
    bindTip(never, `<b>${r.label}</b><span class="r">${r.never}/${r.total} never break even (${f(neverPct, 1)}%)</span>`);
    g.append(finite, never);
    g.append(el("text", { x: W - padR + 10, y: cy - 2, class: "val", "font-size": 11.5 },
                        [document.createTextNode("median " + FMT.num1s(r.median) + " eval")]));
    g.append(el("text", { x: W - padR + 10, y: cy + 13, class: "tick", "font-size": 10.5 },
                        [document.createTextNode(r.never + " never")]));
  });
  return g;
}

/* -------------------------------------------- log dot plot (never log bars) */
function dotLog(rows, cfg) {
  const W = cfg.width || 880, padL = cfg.padL || 180, padR = 96, padT = 26, rowH = cfg.rowH || 26;
  const H = padT + rows.length * rowH + 46;
  const vals = rows.flatMap(r => r.points.map(p => p.v)).filter(v => v > 0);
  const lo = cfg.min || Math.pow(10, Math.floor(Math.log10(Math.min(...vals))));
  const hi = cfg.max || Math.pow(10, Math.ceil(Math.log10(Math.max(...vals))));
  const x = logScale(lo, hi, padL, W - padR);
  const g = el("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": cfg.title });
  logTicks(lo, hi).forEach(t => {
    g.append(el("line", { x1: x(t), x2: x(t), y1: padT - 6, y2: padT + rows.length * rowH,
                          stroke: "var(--grid)", "stroke-width": 1 }));
    g.append(el("text", { x: x(t), y: padT + rows.length * rowH + 18, class: "tick", "text-anchor": "middle" },
                        [document.createTextNode(cfg.fmtTick ? cfg.fmtTick(t) : String(t))]));
  });
  g.append(el("text", { x: (padL + W - padR) / 2, y: H - 6, class: "axtitle", "text-anchor": "middle" },
                      [document.createTextNode(cfg.xTitle)]));
  rows.forEach((r, i) => {
    const cy = padT + i * rowH + rowH / 2;
    g.append(el("text", { x: padL - 12, y: cy + 4, class: "lab", "text-anchor": "end" },
                        [document.createTextNode(r.label)]));
    const xs = r.points.filter(p => p.v > 0).map(p => x(p.v));
    if (xs.length > 1) {
      g.append(el("line", { x1: Math.min(...xs), x2: Math.max(...xs), y1: cy, y2: cy,
                            stroke: "var(--axis)", "stroke-width": 1.5, "stroke-linecap": "round" }));
    }
    r.points.forEach(p => {
      if (!(p.v > 0)) return;
      const c = el("circle", { cx: x(p.v), cy, r: 5, fill: p.color, stroke: "var(--surface-1)", "stroke-width": 2 });
      bindTip(c, `<b>${r.label} · ${p.label}</b><span class="r">${cfg.fmtVal ? cfg.fmtVal(p.v) : us(p.v)}</span>` +
        (p.tip ? `<br><span class="r">${p.tip}</span>` : ""));
      g.append(c);
    });
    if (r.right) {
      g.append(el("text", { x: W - padR + 10, y: cy + 4, class: "val", "font-size": 11.5 },
                          [document.createTextNode(r.right)]));
    }
  });
  return g;
}

/* -------------------------------------------------- histogram (counts) */
function histogram(cfg) {
  const W = cfg.width || 880, padL = 60, padR = 22, padT = 24, padB = 62;
  const H = cfg.height || 260, plotW = W - padL - padR, plotH = H - padT - padB;
  const maxV = Math.max(...cfg.series.flatMap(s => s.counts)) * 1.15;
  const y = linScale(0, maxV, padT + plotH, padT);
  const g = el("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": cfg.title });
  niceTicks(0, maxV, 4).forEach(t => {
    g.append(el("line", { x1: padL, x2: W - padR, y1: y(t), y2: y(t), stroke: "var(--grid)", "stroke-width": 1 }));
    g.append(el("text", { x: padL - 9, y: y(t) + 4, class: "tick", "text-anchor": "end" },
                        [document.createTextNode(f(t, 0))]));
  });
  g.append(el("line", { x1: padL, x2: W - padR, y1: padT + plotH, y2: padT + plotH,
                        stroke: "var(--axis)", "stroke-width": 1 }));
  g.append(el("text", { x: 16, y: padT + plotH / 2, class: "axtitle", "text-anchor": "middle",
                        transform: `rotate(-90 16 ${padT + plotH / 2})` },
                      [document.createTextNode(cfg.yTitle || "formulas")]));
  g.append(el("text", { x: padL + plotW / 2, y: H - 8, class: "axtitle", "text-anchor": "middle" },
                      [document.createTextNode(cfg.xTitle)]));
  const bandW = plotW / cfg.labels.length;
  const inner = Math.min(30, (bandW - 12) / cfg.series.length);
  cfg.labels.forEach((lab, li) => {
    const cx = padL + bandW * (li + 0.5);
    const total = cfg.series.length * inner + (cfg.series.length - 1) * 2;
    cfg.series.forEach((s, si) => {
      const v = s.counts[li];
      const bx = cx - total / 2 + si * (inner + 2);
      const by = y(v), bh = Math.max(0.5, padT + plotH - by);
      const bar = el("rect", { x: bx, y: by, width: inner, height: bh, rx: 2.5, fill: s.color });
      bindTip(bar, `<b>${s.label}</b><span class="r">${v} formulas break even at ${lab} evaluations</span>`);
      g.append(bar);
    });
    g.append(el("text", { x: cx, y: padT + plotH + 17, class: "tick", "text-anchor": "middle", "font-size": 11 },
                        [document.createTextNode(lab)]));
  });
  return g;
}

/* ---------------------------------------------------- heat grid (ratios) */
function heatGrid(cfg) {
  const cellW = cfg.cellW || 118, cellH = 40, padL = cfg.padL || 110, padT = 34;
  const W = padL + cfg.cols.length * cellW + 16;
  const H = padT + cfg.rows.length * cellH + 16;
  const g = el("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": cfg.title });
  const vals = cfg.cells.map(c => c.value);
  const lo = Math.min(...vals), hi = Math.max(...vals);
  cfg.cols.forEach((c, ci) =>
    g.append(el("text", { x: padL + cellW * (ci + 0.5), y: padT - 12, class: "lab", "text-anchor": "middle" },
                        [document.createTextNode(c)])));
  cfg.rows.forEach((r, ri) =>
    g.append(el("text", { x: padL - 10, y: padT + cellH * (ri + 0.5) + 4, class: "lab", "text-anchor": "end" },
                        [document.createTextNode(r)])));
  cfg.cells.forEach(cell => {
    const ci = cfg.cols.indexOf(cell.col), ri = cfg.rows.indexOf(cell.row);
    if (ci < 0 || ri < 0) return;
    const t = hi === lo ? 0.5 : (cell.value - lo) / (hi - lo);
    const x0 = padL + ci * cellW + 3, y0 = padT + ri * cellH + 3;
    const rect = el("rect", { x: x0, y: y0, width: cellW - 6, height: cellH - 6, rx: 5,
                              fill: S1, "fill-opacity": (0.13 + 0.42 * (1 - t)).toFixed(3),
                              stroke: "var(--border)" });
    bindTip(rect, `<b>${cell.row} × ${cell.col}</b><span class="r">${cfg.arm} ${f(cell.value, 4)}` +
      (cell.lo != null ? `<br>95% CI [${f(cell.lo, 4)}, ${f(cell.hi, 4)}]` : "") +
      (cell.n != null ? `<br>${cell.n} formulas` : "") + `</span>` +
      (cell.basis ? `<br><span class="r">${cell.basis}</span>` : ""));
    g.append(rect);
    g.append(el("text", { x: x0 + (cellW - 6) / 2, y: y0 + (cellH - 6) / 2 + 4, class: "val",
                          "text-anchor": "middle", "font-size": 12.5 },
                        [document.createTextNode(f(cell.value, 3))]));
  });
  return g;
}

/* ================================================== page furniture */
function topbar(cfg) {
  const bar = h("div", { class: "topbar" });
  const inner = h("div", { class: "inner" });
  inner.append(h("div", { class: "brand", html: cfg.brand }));
  if (cfg.links && cfg.links.length) {
    const nav = h("nav", { id: "site-nav", "aria-label": "Page navigation" });
    const menu = h("button", {
      class: "menutog", type: "button", "aria-controls": "site-nav",
      "aria-expanded": "false", text: "☰ menu",
    });
    const closeMenu = () => {
      nav.removeAttribute("data-open");
      menu.setAttribute("aria-expanded", "false");
    };
    menu.addEventListener("click", () => {
      const open = nav.getAttribute("data-open") === "true";
      if (open) closeMenu();
      else {
        nav.setAttribute("data-open", "true");
        menu.setAttribute("aria-expanded", "true");
      }
    });
    cfg.links.forEach(([href, lab]) => {
      const link = h("a", { href, text: lab });
      link.addEventListener("click", closeMenu);
      nav.append(link);
    });
    document.addEventListener("keydown", e => {
      if (e.key === "Escape" && nav.getAttribute("data-open") === "true") {
        closeMenu();
        menu.focus();
      }
    });
    inner.append(menu);
    inner.append(nav);
  }
  const tog = h("button", { class: "themetog", type: "button", "aria-label": "Toggle light or dark theme", text: "◑ theme" });
  tog.addEventListener("click", () => {
    const root = document.documentElement;
    const dark = root.getAttribute("data-theme") === "dark" ||
      (!root.getAttribute("data-theme") && matchMedia("(prefers-color-scheme: dark)").matches);
    root.setAttribute("data-theme", dark ? "light" : "dark");
  });
  if (!cfg.links || !cfg.links.length) tog.style.marginLeft = "auto";
  inner.append(tog);
  bar.append(inner);
  return bar;
}

function section(id, eyebrow, title, lede) {
  const s = h("section", { class: "sec", id });
  if (eyebrow) s.append(h("p", { class: "eyebrow", text: eyebrow }));
  if (title) s.append(h("h2", { text: title }));
  if (lede) s.append(h("p", { class: "sectionlede", html: P(lede) }));
  return s;
}
function layBlock(paras, tag) {
  const d = h("div", { class: "lay" });
  d.append(h("span", { class: "tag", text: tag || "In plain language" }));
  [].concat(paras).forEach(p => d.append(h("p", { html: P(p) })));
  return d;
}
function techBlock(paras, tag) {
  const d = h("div", { class: "tech" });
  if (tag !== null) d.append(h("span", { class: "tag", text: tag || "The technical layer" }));
  [].concat(paras).forEach(p => d.append(h("p", { html: P(p) })));
  return d;
}
function banner(kind, title, bodyHtml) {
  const b = h("div", { class: "banner " + (kind || "") });
  if (title) b.append(h("h3", { text: title }));
  [].concat(bodyHtml).forEach(x => b.append(h("p", { html: P(x) })));
  return b;
}
function tiles(items) {
  const g = h("div", { class: "tiles" });
  items.forEach(([k, v, n]) => g.append(h("div", { class: "tile" }, [
    h("div", { class: "k", text: k }),
    h("div", { class: "v", html: v }),
    h("div", { class: "n", html: P(n) }),
  ])));
  return g;
}

/* ------------------------------------------------------ content blocks */
function domainGrid(domains) {
  const g = h("div", { class: "grid2" });
  domains.forEach(d => g.append(h("div", { class: "dom" }, [
    h("h4", { text: d.name }),
    h("p", { class: "q", html: "“" + P(d.question) + "”" }),
    h("p", { class: "t", html: P(d.lay) }),
    h("p", { class: "why", html: P(d.technical) }),
  ])));
  return g;
}

function toolCards(tools) {
  const g = h("div", { class: "grid2" });
  tools.forEach(t => {
    const c = h("div", { class: "toolcard" });
    c.append(h("h4", { text: t.name }));
    c.append(h("p", { class: "role", text: t.role }));
    const dl = h("dl");
    dl.append(h("dt", { text: "Question it answers" }));
    dl.append(h("dd", { html: P(t.question) }));
    dl.append(h("dt", { text: "Superpower" }));
    dl.append(h("dd", { html: P(t.superpower) }));
    dl.append(h("dt", { text: "What it costs you" }));
    dl.append(h("dd", { html: P(t.cost) }));
    dl.append(h("dt", { text: "Analogy" }));
    dl.append(h("dd", { class: "analogy", html: P(t.analogy) }));
    if (t.measured) {
      dl.append(h("dt", { text: "Measured here" }));
      dl.append(h("dd", { html: P(t.measured) }));
    }
    c.append(dl);
    g.append(c);
  });
  return g;
}

function decisionFlow(nodes) {
  const wrap = h("div", { class: "flow" });
  nodes.forEach(n => {
    const box = h("div", { class: "flownode" });
    box.append(h("p", { class: "ask", html: P(n.ask) }));
    n.arms.forEach(a => {
      const row = h("div", { class: "flowarm" });
      row.append(h("div", { class: "cond", html: P(a.cond) }));
      row.append(h("div", { class: "then", html: "<b>" + P(a.then) + "</b>" + (a.why ? " <em>— " + P(a.why) + "</em>" : "") }));
      box.append(row);
    });
    wrap.append(box);
  });
  return wrap;
}

function decisionAtlasVisual(items) {
  const wrap = h("div", { class: "decision-atlas" });
  items.forEach(it => {
    const c = h("div", { class: "decision-mini" });
    c.append(h("div", { class: "decision-num", text: it.n }));
    c.append(h("h4", { text: it.question }));
    c.append(h("div", { class: "decision-answer", text: it.answer }));
    c.append(h("p", { html: it.evidence }));
    wrap.append(c);
  });
  return wrap;
}

function metricComparisons(rows) {
  const wrap = h("div", { class: "metric-comparisons" });
  rows.forEach(r => {
    const fmtMetric = v => r.format === "multiple" ? f(v, 2) + "×"
      : r.format === "evaluations" ? FMT.num1s(v) + " evaluations"
      : Math.round(v) + " of " + r.total;
    const d = h("div", { class: "metric-diff" });
    d.append(h("h4", { text: r.metric }));
    d.append(h("div", { class: "metric-pair" }, [
      h("div", {}, [h("span", { text: "archive" }), h("b", { text: fmtMetric(r.archived) })]),
      h("div", { class: "metric-arrow", text: "→" }),
      h("div", {}, [h("span", { text: "fresh replay" }), h("b", { text: fmtMetric(r.replay) })]),
    ]));
    wrap.append(d);
  });
  return wrap;
}

function frontierLanes(items) {
  const defs = [
    ["ranked-next-test", "Next measurements", "Cheap questions that change the decision"],
    ["partially-answered", "Partial or negative evidence", "Some evidence exists; the success criterion is unmet"],
    ["formal-not-demonstrated", "Formal or capability gaps", "Implemented ideas without demonstrated practical value"],
    ["open", "Boundary not mapped", "The current evidence stops here"],
  ];
  const wrap = h("div", { class: "frontier-lanes" });
  defs.forEach(([status, title, sub]) => {
    const lane = h("div", { class: "frontier-lane" });
    lane.append(h("div", { class: "lane-head" }, [h("b", { text: title }), h("span", { text: sub })]));
    const chips = h("div", { class: "lane-chips" });
    items.filter(it => it.status === status).forEach(it =>
      chips.append(h("span", { text: it.visual_label || it.title })));
    lane.append(chips);
    wrap.append(lane);
  });
  return wrap;
}

function auditLadder(chain) {
  const wrap = h("div", { class: "audit-ladder" });
  chain.forEach((step, i) => {
    const row = h("div", { class: "audit-step" });
    row.append(h("div", { class: "audit-mark", text: String(i + 1).padStart(2, "0") }));
    row.append(h("div", { class: "audit-copy" }, [
      h("span", { class: "audit-date", text: step.date }),
      h("b", { text: step.stage.split(" — ")[0] }),
    ]));
    wrap.append(row);
  });
  return wrap;
}

function glossary(terms, mountId) {
  const wrap = h("div");
  const controls = h("div", { class: "glosscontrols" });
  const input = h("input", { type: "search", placeholder: "Filter terms…", "aria-label": "Filter glossary terms" });
  const sel = h("select", { "aria-label": "Filter by group" });
  const groups = ["all", ...Array.from(new Set(terms.map(t => t.group)))];
  const GLABEL = {
    all: "All groups",
    "boolean-basics": "Boolean basics",
    "workload-and-timing": "Workload & timing",
    representations: "Representations",
    "statistics-and-protocol": "Statistics & protocol",
  };
  groups.forEach(g => sel.append(h("option", { value: g, text: GLABEL[g] || g })));
  const count = h("span", { class: "empty", style: "padding:0" });
  controls.append(input, sel, count);
  const list = h("div", { class: "gloss", id: mountId });
  const sorted = terms.slice().sort((a, b) => a.term.localeCompare(b.term));

  function render() {
    const q = input.value.trim().toLowerCase();
    const g = sel.value;
    list.textContent = "";
    const hits = sorted.filter(t =>
      (g === "all" || t.group === g) &&
      (!q || t.term.toLowerCase().includes(q) || t.lay.toLowerCase().includes(q) ||
        (t.technical || "").toLowerCase().includes(q)));
    count.textContent = hits.length + " of " + sorted.length + " terms";
    if (!hits.length) { list.append(h("p", { class: "empty", text: "No terms match that filter." })); return; }
    hits.forEach(t => list.append(h("div", { class: "gterm" }, [
      h("div", {}, [h("span", { class: "t", text: t.term }), h("span", { class: "g", text: GLABEL[t.group] || t.group })]),
      h("p", { class: "l", html: P(t.lay) }),
      t.technical ? h("p", { class: "x", html: P(t.technical) }) : null,
    ])));
  }
  input.addEventListener("input", render);
  sel.addEventListener("change", render);
  render();
  wrap.append(controls, list);
  return wrap;
}

/* ------------------------------------------------------ shared figures
   Every figure below reads only from DATA. They are defined once here so the
   master page and the audience cuts render identical charts from identical
   numbers — a derived page can never drift from the master. */

const FIG = {};

FIG.decisionAtlas = () => {
  const wrapRows = DATA.e6_wrapper_ratio.rows;
  const be = DATA.e11_breakeven;
  const engines = DATA.e15_engines.rows;
  const extract = DATA.e12_cudd.extract_vs_kernel.map(r => r.factor);
  const flatExternal = DATA.e2_kernel_vs_cse_flat.rows.find(r => r.group === "external");
  const flatWins = engines.filter(r => r.fastest === "flat_bigint").length;
  const wordsWins = engines.filter(r => r.fastest === "words").length;
  const items = [
    { n: "01", question: "One answer", answer: "Use BitSet",
      evidence: `BitSet led at all ${wrapRows.length} measured supports; even cached CM took ` +
        `${f(Math.min(...wrapRows.map(r => r.cached_median)), 2)}–${f(Math.max(...wrapRows.map(r => r.cached_median)), 2)}× as long.` },
    { n: "02", question: "The same answer repeatedly", answer: "Measure reuse first",
      evidence: `Against the matched plain-CSE baseline, the finite median moves from ` +
        `${FMT.num1s(be.synthetic.median_finite)} synthetic to ${FMT.num1s(be.epfl_vs_plain_cse.median_finite)} real-circuit evaluations.` },
    { n: "03", question: "Choosing an internal engine", answer: "Use workload evidence",
      evidence: `Flat big-integer won ${flatWins} of ${engines.length} measured supports; word-packed won ` +
        `${wordsWins}, at live_k=${engines.find(r => r.fastest === "words").live_k}.` },
    { n: "04", question: "Canonical symbolic questions", answer: "Use CUDD",
      evidence: `It builds a compact graph; producing the complete explicit answer vector cost ` +
        `${FMT.x0(Math.min(...extract))}–${FMT.xcomma(Math.max(...extract))} the CM kernel.` },
    { n: "05", question: "Real AND/INV circuits", answer: "Expect parity with a strong compiler",
      evidence: `External CM ÷ CSE-flat was ${f(flatExternal.value, 4)}, with its circuit-clustered interval spanning parity.` },
  ];
  return card({
    id: "fig-decision-atlas",
    scope: "five common decisions · each signal comes from the matched result named in the card",
    title: "The decision atlas: five questions, five evidence-backed answers",
    caption: "The answer changes with the artifact you need and where you draw the timing boundary. This is the " +
      "shortest honest version of section 4; the full charts immediately below show the underlying measurements.",
    visual: decisionAtlasVisual(items),
    table: table(["situation", "answer", "evidence signal"],
      items.map(it => [it.question, it.answer, it.evidence])),
    prov: [
      ...DATA.e6_wrapper_ratio.provenance,
      ...DATA.e11_breakeven.provenance,
      ...DATA.e15_engines.provenance,
      ...DATA.e12_cudd.provenance,
      ...DATA.e2_kernel_vs_cse_flat.provenance,
    ],
  });
};

FIG.assignmentGrowth = () => {
  const d = DATA.e18_assignment_growth;
  return card({
    id: "fig-assignment-growth",
    scope: "definition of an explicit truth vector · assignments = 2^live_k",
    title: "Four more live inputs means sixteen times as many answers",
    caption: "The work grows with inputs that actually change the result, not with names sitting unused in the " +
      "namespace. The log axis makes the repeated sixteen-fold jumps visible without letting the largest bar " +
      "erase the smaller ones.",
    svg: dotLog(d.rows.map(r => ({
      label: "live_k = " + r.live_k,
      points: [{ label: commas(r.assignments) + " assignments", v: r.assignments, color: S1 }],
      right: commas(r.assignments),
    })), {
      min: 10, max: 100000, title: "Explicit answer-vector growth",
      xTitle: "explicit assignments (log scale)", fmtTick: commas, fmtVal: commas,
    }),
    table: table(["live_k", "explicit assignments"], d.rows.map(r => [r.live_k, commas(r.assignments)])),
    prov: d.provenance,
    note: `The current guard stops at live_k=${d.guard_limit}. The graph explains why that is a capability ` +
      "boundary rather than an arbitrary benchmark cutoff.",
  });
};

FIG.kernelForest = () => {
  const d = DATA.e1_kernel_vs_cse;
  return card({
    id: "fig-kernel",
    scope: "3 independent scopes · never pooled · CM kernel ÷ plain structural CSE kernel",
    title: "CM's kernel advantage over plain structural CSE, replicated three ways",
    caption: "Below 1.00 means the CM kernel finished faster. Each row is its own experiment with its own " +
      "clustering basis; they are shown together for comparison and are never averaged into one figure.",
    legend: [[S1, "local synthetic corpus"], [S2, "external EPFL circuits"], [S3, "Linux pods (EPYC)"]],
    svg: forest(d.rows, {
      domain: pad(d.rows.flatMap(r => [r.value, r.lo, r.hi]).concat([1.0]), 0.01), ref: 1.0,
      xTitle: "CM kernel ÷ plain-CSE kernel (blocked schedule, geometric mean)",
      arm: "CM / plain CSE", title: "CM versus plain CSE across three scopes",
    }),
    table: table(["scope", "geomean", "95% CI", "clustering basis"],
      d.rows.map(r => [r.label, f(r.value, 4), r.lo == null ? "—" : `[${f(r.lo, 4)}, ${f(r.hi, 4)}]`, r.basis])),
    prov: d.provenance,
    note: "All five pod intervals exclude parity, and the external interval excludes parity, so the direction " +
      "is not a local-machine artifact. The size of the effect is modest and corpus-dependent.",
  });
};

FIG.flatForest = () => {
  const d = DATA.e2_kernel_vs_cse_flat;
  const m = d.materiality;
  return card({
    id: "fig-flat",
    scope: "3 independent scopes · CM kernel ÷ (CSE + sharing-aware flattening) kernel",
    title: "Against a properly flattened CSE baseline, CM is kernel-equivalent",
    caption: "This is the comparison that decided the project's direction. The residual straddles parity: " +
      "it is above 1.00 locally, at 1.00 externally, and below 1.00 on pods. A quantity whose sign is not " +
      "stable across scopes is not a win in either direction.",
    legend: [[S1, "local synthetic corpus"], [S2, "external EPFL circuits"], [S3, "Linux pods (EPYC)"]],
    svg: forest(d.rows, {
      domain: pad(d.rows.flatMap(r => [r.value, r.lo, r.hi]).concat([1.0]), 0.01), ref: 1.0,
      xTitle: "CM kernel ÷ CSE-flat kernel (geometric mean)",
      arm: "CM / CSE-flat", title: "CM versus CSE-flat across three scopes",
    }),
    table: table(["scope", "geomean", "95% CI", "clustering basis"],
      d.rows.map(r => [r.label, f(r.value, 4), r.lo == null ? "—" : `[${f(r.lo, 4)}, ${f(r.hi, 4)}]`, r.basis])),
    prov: d.provenance,
    note: "<b>Pre-registered materiality rule, evaluated on the external corpus:</b> " +
      `geomean ≤ 0.95 → <span class="pill ${m["cond1_geomean_le_0.95"] ? "ok" : "bad"}">${m["cond1_geomean_le_0.95"]}</span> · ` +
      `clustered CI excludes parity → <span class="pill ${m.cond2_clustered_ci_excludes_parity ? "ok" : "bad"}">${m.cond2_clustered_ci_excludes_parity}</span> · ` +
      `median break-even ≤ 1000 → <span class="pill ${m.cond3_median_breakeven_le_1000 ? "ok" : "bad"}">${m.cond3_median_breakeven_le_1000}</span>. ` +
      `Overall <code>optimization_worthy = ${m.optimization_worthy}</code>. The rule was written down before any ` +
      "external number existed, and it failed — which is what converts “treat CM and CSE-flat as kernel-equivalent” " +
      "from a provisional posture into a final one.",
  });
};

FIG.wrapperRatio = () => {
  const d = DATA.e6_wrapper_ratio;
  const rows = d.rows;
  return card({
    id: "fig-wrapper",
    scope: "local synthetic exact-support corpus · 32 formulas per stratum · CM end-to-end call ÷ bare BitSet call",
    title: "At the whole-call boundary, BitSet leads at every measured support size",
    caption: "Above 1.00 means BitSet finished first. The cached line is the friendliest case for CM — its " +
      "compiled program is already built and in cache. Even then it never reaches parity through the guard limit.",
    legend: [[S1, "cached (CM program already compiled)"], [S2, "uncached, warm environment"]],
    svg: xyPlot({
      height: 330, xDomain: [3, 17], yDomain: [0.8, 9], logY: true,
      xTicks: rows.map(r => r.live_k), fmtX: (v) => String(v),
      fmtY: (v) => v + "×", ref: 1.0, refLabel: "parity 1.00 (BitSet = CM)",
      xTitle: "live_k — semantic support (variables that actually change the answer)",
      yTitle: "CM wrapper ÷ BitSet (median, log scale)",
      title: "Wrapper ratio by live_k",
      series: [
        {
          label: "cached", color: S1, line: true,
          points: rows.map(r => ({
            x: r.live_k, y: r.cached_median,
            direct: FMT.x2(r.cached_median), anchor: "middle",
            tip: `live_k ${r.live_k} · median ${f(r.cached_median, 2)}× · geomean ${f(r.cached_geomean, 2)}× · ` +
              `p10–p90 ${f(r.cached_p10, 2)}–${f(r.cached_p90, 2)} · ${r.n} formulas`,
          })),
        },
        {
          label: "uncached (warm env)", color: S2, line: true,
          points: rows.filter(r => r.uncached_median != null).map(r => ({
            x: r.live_k, y: r.uncached_median,
            tip: `live_k ${r.live_k} · median ${f(r.uncached_median, 2)}× · geomean ${f(r.uncached_geomean, 2)}×`,
          })),
        },
      ],
    }),
    table: table(["live_k", "formulas", "cached median", "cached geomean", "cached p10–p90", "uncached median"],
      rows.map(r => [r.live_k, r.n, FMT.x2(r.cached_median), FMT.x2(r.cached_geomean),
        `${f(r.cached_p10, 2)}–${f(r.cached_p90, 2)}`, r.uncached_median == null ? "—" : FMT.x2(r.uncached_median)])),
    prov: d.provenance,
    note: d.engine_note + " The pre-repair claim that CM was “modestly ahead at controlled live_k 12 and 16” " +
      "does not survive this measurement and appears on this site only in the corrections ledger.",
  });
};

FIG.wrapperCost = () => {
  const d = DATA.e7_wrapper_cost;
  return card({
    id: "fig-wrapper-cost",
    scope: "local synthetic exact-support corpus · medians per stratum",
    title: "Where the wrapper time actually goes",
    caption: "The gap is not kernel speed — it is the fixed cost of the end-to-end call: argument binding, " +
      "environment setup, cache lookup, and result extraction. That fixed cost is roughly constant, so it " +
      "dominates completely when the useful work is small.",
    legend: [[S1, "CM end-to-end call"], [S2, "bare BitSet call"], [S3, "CM wrapper overhead (call minus kernel)"]],
    svg: groupedCols({
      height: 320, labelBars: true, fmtVal: (v) => us(v), yTitle: "microseconds (median)",
      xTitle: "live_k — semantic support", tickDigits: 0,
      groups: d.rows.map(r => ({
        label: "k=" + r.live_k, values: { cm: r.cm_wrapper_us, bs: r.bitset_us, ov: r.overhead_us },
        tip: `live_k ${r.live_k}`,
      })),
      series: [
        { key: "cm", label: "CM end-to-end", color: S1 },
        { key: "bs", label: "BitSet", color: S2 },
        { key: "ov", label: "CM wrapper overhead", color: S3 },
      ],
    }),
    table: table(["live_k", "CM end-to-end", "BitSet", "CM wrapper overhead"],
      d.rows.map(r => [r.live_k, us(r.cm_wrapper_us), us(r.bitset_us),
        r.overhead_us == null ? "not separable" : us(r.overhead_us)])),
    prov: d.provenance,
    note: "Overhead is not separable at live_k=4, where the corpus runs the bigint/BitSet fallback rather than " +
      "the word-packed engine, so that cell is recorded as skipped rather than estimated.",
  });
};

FIG.breakevenSummary = () => {
  const d = DATA.e11_breakeven;
  const arms = [
    ["Synthetic corpus (B1 replay)", d.synthetic, S1],
    ["EPFL real circuits (B7)", d.epfl_vs_plain_cse, S2],
    ["EPFL real circuits (B7)", d.epfl, S3],
  ];
  return card({
    id: "fig-breakeven",
    scope: "192 synthetic formulas and 129 EPFL cones · three arms, each against its named baseline",
    title: "Matched baselines make the economics legible",
    caption: `Against plain CSE, the finite median moves from ${FMT.num1s(d.synthetic.median_finite)} ` +
      `evaluations on synthetic formulas to ${FMT.num1s(d.epfl_vs_plain_cse.median_finite)} on real circuits, ` +
      `while the never-break-even share moves from ${f(100*d.synthetic.n_never/d.synthetic.n_total, 1)}% to ` +
      `${f(100*d.epfl_vs_plain_cse.n_never/d.epfl_vs_plain_cse.n_total, 1)}%. Against CSE-flat, parity makes ` +
      `${f(100*d.epfl.n_never/d.epfl.n_total, 1)}% of cones never break even at any reuse count.`,
    legend: [[S1, "finite break-even"], ["var(--critical)", "never breaks even"]],
    svg: stackedPercentBars(arms.map(([name, a]) => ({
      label: name, baseline: a.baseline, finite: a.n_finite, never: a.n_never,
      total: a.n_total, median: a.median_finite,
    })), { title: "Finite versus never-break-even shares" }),
    table: table(["corpus", "baseline", "median of finite", "breaks even", "never breaks even", "prep multiple"],
      arms.map(([name, a]) => [name, a.baseline, f(a.median_finite, 1),
        `${a.n_finite}/${a.n_total}`, `${a.n_never}/${a.n_total}`, FMT.x2(a.prep_multiple_geomean)])),
    prov: d.provenance,
    note: "Only the first two rows are a cross-corpus comparison: both use plain CSE. The third row answers a " +
      "different and stricter question against CSE-flat.",
  });
};

FIG.breakeven = () => {
  const d = DATA.e11_breakeven;
  const distribution = card({
    id: "fig-breakeven-distribution",
    scope: "finite break-even cases only · the never-break-even population is shown in the summary above",
    title: "Among formulas that do break even, the distribution is broad and right-skewed",
    caption: "Each bar counts formulas whose finite break-even lands in that band. The median alone hides a long " +
      "tail, so the complete distribution is shown; never-break-even cases are not smuggled into an artificial " +
      "final bin.",
    legend: [[S1, "synthetic, vs plain CSE"], [S2, "EPFL circuits, vs plain CSE (matched)"],
             [S3, "EPFL circuits, vs CSE-flat"]],
    svg: histogram({
      labels: d.bin_labels, xTitle: "evaluations of the same expression needed to break even",
      yTitle: "formulas", title: "Break-even distributions",
      series: [
        { label: "synthetic vs plain CSE", color: S1, counts: d.synthetic.hist },
        { label: "EPFL vs plain CSE (matched baseline)", color: S2, counts: d.epfl_vs_plain_cse.hist },
        { label: "EPFL vs CSE-flat", color: S3, counts: d.epfl.hist },
      ],
    }),
    table: table(["break-even band", "synthetic vs plain CSE", "EPFL vs plain CSE", "EPFL vs CSE-flat"],
      d.bin_labels.map((label, i) => [label, d.synthetic.hist[i], d.epfl_vs_plain_cse.hist[i], d.epfl.hist[i]])),
    prov: d.provenance,
    note: "<b>Baseline warning.</b> " + d.baseline_warning + " Read that way, real circuits are moderately worse " +
      `than synthetic ones on the matched arm (median ${f(d.epfl_vs_plain_cse.median_finite, 1)} against ` +
      `${f(d.synthetic.median_finite, 1)}) — not catastrophically so. The third arm is different in kind: against ` +
      `CSE-flat the per-evaluation gain is already ~zero, so ${d.epfl.n_never} of ${d.epfl.n_total} cones never ` +
      "break even at any reuse count. That is arithmetic about a parity comparison, not a property of real circuits. " +
      "A formula is classified never-break-even exactly when its per-evaluation gain is not positive; preparation " +
      "cost sets how large the finite counts are, but plays no part in that classification.",
  });
  return frag([FIG.breakevenSummary(), distribution]);
};

FIG.engines = () => {
  const d = DATA.e15_engines;
  const rows = d.rows;
  const labelAt = new Set([2, 8, 16]);
  return card({
    id: "fig-engines",
    scope: "local · BX1 crossover corpus · steady-state kernels, environments and programs prebuilt",
    title: "Which evaluation engine is fastest depends on the workload, not on a fixed variable count",
    caption: "Three kernels over the same expressions. Flat big-integer evaluation beats the recursive one " +
      "everywhere. The word-packed engine pays a fixed dispatch cost first, so on these expressions it only " +
      "wins once the packed work is large enough to absorb it.",
    legend: [[S1, "recursive big-integer"], [S2, "flat big-integer"], [S3, "word-packed"]],
    svg: xyPlot({
      height: 340, xDomain: [2, 16.6], yDomain: [1.8, 80], logY: true,
      xTicks: rows.map(r => r.live_k), fmtX: (v) => String(v), fmtY: (v) => v + " µs",
      xTitle: "live_k — semantic support", yTitle: "kernel time, median (log scale)",
      title: "Engine crossover by live_k",
      series: [
        { label: "recursive bigint", color: S1, line: true,
          points: rows.map(r => ({ x: r.live_k, y: r.recursive_us,
            direct: labelAt.has(r.live_k) ? us(r.recursive_us) : null,
            tip: `live_k ${r.live_k} · ${us(r.recursive_us)} · ${r.n} formulas` })) },
        { label: "flat bigint", color: S2, line: true,
          points: rows.map(r => ({ x: r.live_k, y: r.flat_us,
            direct: labelAt.has(r.live_k) ? us(r.flat_us) : null,
            tip: `live_k ${r.live_k} · ${us(r.flat_us)} · flat ÷ recursive ${f(r.flat_vs_recursive, 2)}` })) },
        { label: "word-packed", color: S3, line: true,
          points: rows.filter(r => r.words_us != null).map(r => ({ x: r.live_k, y: r.words_us,
            direct: labelAt.has(r.live_k) ? us(r.words_us) : null,
            tip: `live_k ${r.live_k} · ${us(r.words_us)} · words ÷ flat ${f(r.words_vs_flat, 2)}` })) },
      ],
    }),
    table: table(["live_k", "formulas", "recursive", "flat", "word-packed", "flat ÷ recursive", "words ÷ flat", "fastest"],
      rows.map(r => [r.live_k, r.n, us(r.recursive_us), us(r.flat_us),
        r.words_us == null ? "not engaged" : us(r.words_us),
        f(r.flat_vs_recursive, 2), r.words_vs_flat == null ? "—" : f(r.words_vs_flat, 2),
        r.fastest.replace("_bigint", " bigint")])),
    prov: d.provenance,
    note: "Read as a rule about work, not about variable count: the word-packed engine wins when the packed " +
      "operation count is large enough to amortize its fixed dispatch cost. On larger-operation corpora that " +
      "happens at smaller supports. Both statements are corpus-scoped and neither is a universal threshold.",
  });
};

FIG.cudd = () => {
  const d = DATA.e12_cudd;
  const rows = d.rows;
  const build = card({
    id: "fig-cudd-build",
    scope: "matched pod run · Linux / AMD EPYC · CUDD 3.0.0 via dd.cudd · fixed natural order, single build",
    title: "Panel 1 — building the symbolic object",
    caption: "What it costs to construct each representation once. These are construction costs only. They are " +
      "never combined with the evaluation costs in panel 2, because the two answer different questions.",
    legend: [[S1, "CM preparation"], [S2, "CSE-flat preparation"], [S3, "CUDD build (manager-inclusive)"]],
    svg: groupedCols({
      height: 300, log: true, labelBars: true, fmtVal: (v) => us(v),
      yTitle: "microseconds, median (log scale)", xTitle: "live_k — semantic support",
      fmtTick: (v) => us(v),
      groups: rows.map(r => ({ label: "k=" + r.live_k,
        values: { cm: r.cm_prep_us, cse: r.cse_flat_prep_us, cudd: r.cudd_build_us },
        tip: `${r.n} rows · resulting BDD ${r.cudd_dag_size} nodes` })),
      series: [
        { key: "cm", label: "CM prep", color: S1 },
        { key: "cse", label: "CSE-flat prep", color: S2 },
        { key: "cudd", label: "CUDD build", color: S3 },
      ],
    }),
    table: table(["live_k", "rows", "CM prep", "CSE-flat prep", "CUDD build (manager-inclusive)", "resulting BDD nodes"],
      rows.map(r => [r.live_k, r.n, us(r.cm_prep_us), us(r.cse_flat_prep_us), us(r.cudd_build_us),
        f(r.cudd_dag_size, 0)])),
    prov: d.provenance,
    note: "CUDD's build window here includes creating a fresh manager and declaring variables, which is the " +
      "honest cost of getting a usable BDD from nothing. The resulting graphs are tiny — " +
      `${f(rows[rows.length - 1].cudd_dag_size, 0)} nodes at live_k=16 — which is exactly CUDD's point.`,
  });
  const evalCard = card({
    id: "fig-cudd-eval",
    scope: "same matched pod run · full-extraction packed equality verified on every row",
    title: "Panel 2 — getting answers out",
    caption: "What it costs to produce the complete packed truth vector. The CM and CSE-flat kernels produce it " +
      "directly. CUDD has to walk its graph once per assignment, and that cost grows with the number of " +
      "assignments — which doubles with every added variable.",
    legend: [[S1, "CM kernel"], [S2, "CSE-flat kernel"], [S3, "CUDD full extraction"], [S4, "CUDD 256-sample evaluation"]],
    svg: dotLog(rows.map(r => ({
      label: "live_k = " + r.live_k,
      right: FMT.xcomma(r.cudd_extract_full_us / r.cm_kernel_us) + " slower",
      points: [
        { v: r.cm_kernel_us, label: "CM kernel", color: S1 },
        { v: r.cse_flat_kernel_us, label: "CSE-flat kernel", color: S2 },
        { v: r.cudd_eval256_us, label: "CUDD, 256 sampled assignments", color: S4 },
        { v: r.cudd_extract_full_us, label: "CUDD, full extraction", color: S3 },
      ],
    })), {
      padL: 130, rowH: 34, fmtTick: (v) => us(v), fmtVal: (v) => us(v),
      xTitle: "microseconds, median (log scale) — right-hand label is CUDD full extraction ÷ CM kernel",
      title: "Evaluation and extraction costs",
    }),
    table: table(["live_k", "CM kernel", "CSE-flat kernel", "CUDD 256 samples", "CUDD full extraction", "extraction ÷ CM kernel"],
      rows.map(r => [r.live_k, us(r.cm_kernel_us), us(r.cse_flat_kernel_us), us(r.cudd_eval256_us),
        us(r.cudd_extract_full_us), FMT.xcomma(r.cudd_extract_full_us / r.cm_kernel_us)])),
    prov: d.provenance,
    note: `Integrity: <code>robdd_is_cudd</code> true on all ${d.integrity.n_rows} rows, and CUDD's full ` +
      "extraction matched the CM packed bits exactly on every row — so this is a like-for-like comparison of " +
      "the same answer produced two ways, not a comparison of different outputs. " +
      "<b>This is not a ranking of CUDD against CM.</b> It is the price of asking a compact symbolic object for " +
      "an explicit truth vector, which is not what a BDD is for.",
  });
  return frag([build, evalCard]);
};

FIG.cuddOrders = () => {
  const d = DATA.e16_cudd_orders;
  const rows = d.rows;
  return card({
    id: "fig-cudd-orders",
    scope: "pod run · build window = expression-to-BDD conversion only (Audit V4 convention)",
    title: "Variable ordering: a real BDD-size win, at a real search cost",
    caption: "A BDD's size depends on the order its variables are tested in. Trying ten seeded orders and " +
      "keeping the smallest graph does shrink it — and costs about ten builds to find out.",
    legend: [[S1, "fixed natural order"], [S2, "best of 10 seeded orders"], [S3, "CUDD dynamic reordering"]],
    svg: groupedCols({
      height: 280, labelBars: true, fmtVal: (v) => f(v, 0), tickDigits: 0,
      yTitle: "BDD nodes (median)", xTitle: "live_k — semantic support",
      groups: rows.map(r => ({ label: "k=" + r.live_k,
        values: { fx: r.fixed_nodes, b10: r.best10_nodes, ro: r.reorder_nodes },
        tip: `best-of-10 ÷ fixed = ${f(r.node_ratio_best10, 3)} · reordering ÷ fixed = ${f(r.node_ratio_reorder, 3)}` })),
      series: [
        { key: "fx", label: "fixed order", color: S1 },
        { key: "b10", label: "best of 10", color: S2 },
        { key: "ro", label: "dynamic reordering", color: S3 },
      ],
    }),
    svg2: dotLog(rows.map(r => ({
      label: "live_k = " + r.live_k,
      right: FMT.x1(r.pure_10build_sum_us / r.fixed_build_us) + " the build cost",
      points: [
        { v: r.fixed_build_us, label: "one build, fixed order", color: S1 },
        { v: r.pure_10build_sum_us, label: "ten builds (the search itself)", color: S2 },
      ],
    })), {
      padL: 130, rowH: 32, fmtTick: (v) => us(v), fmtVal: (v) => us(v),
      xTitle: "microseconds, median (log scale) — build time only, excluding harness bookkeeping",
      title: "Order-search cost",
    }),
    table: table(["live_k", "fixed nodes", "best-of-10 nodes", "reorder nodes", "best-10 ÷ fixed", "reorder ÷ fixed", "one build", "ten builds"],
      rows.map(r => [r.live_k, f(r.fixed_nodes, 0), f(r.best10_nodes, 0), f(r.reorder_nodes, 0),
        f(r.node_ratio_best10, 3), f(r.node_ratio_reorder, 3), us(r.fixed_build_us), us(r.pure_10build_sum_us)])),
    prov: d.provenance,
    note: "<b>Axis warning:</b> " + d.build_window_note + " Dynamic reordering never fires on these graphs — at " +
      `${f(Math.max(...rows.map(r => r.fixed_nodes)), 0)} nodes and below, CUDD's trigger threshold is never ` +
      "reached, so its node ratio is exactly 1.00. That is a statement about this corpus being small for CUDD, " +
      "not about reordering being ineffective.",
  });
};

FIG.epflCircuits = () => {
  const d = DATA.e4_epfl_per_circuit;
  const cats = d.circuits.slice().sort((a, b) => a.cm_cse_flat - b.cm_cse_flat).map(c => ({
    label: `${c.circuit.replace(".aig", "")} (${c.n})`,
    a: c.cm_cse_flat, b: c.cm_cse,
    tip: `${c.category} · ${c.n} cones`,
  }));
  return card({
    id: "fig-epfl",
    scope: `EPFL combinational benchmark suite · ${d.n_ok} AND/INV cones from ${d.n_circuits} circuits · ${d.n_guard_skipped} guard skips`,
    title: "The same two comparisons, circuit by circuit, on real hardware designs",
    caption: "Each row is one published circuit. The blue dot is CM against a properly flattened CSE; the " +
      "orange dot is CM against a plain CSE. The blue dots scatter around parity in both directions; the " +
      "orange dots sit consistently below it.",
    legend: [[S1, "CM ÷ CSE-flat"], [S2, "CM ÷ plain CSE"]],
    svg: dumbbell(cats, {
      domain: pad(d.circuits.flatMap(c => [c.cm_cse_flat, c.cm_cse]).concat([1.0]), 0.02),
      ref: 1.0, padL: 150,
      aLabel: "CM ÷ CSE-flat", bLabel: "CM ÷ plain CSE",
      xTitle: "geometric mean ratio within circuit (blocked schedule)",
      title: "EPFL per-circuit ratios",
    }),
    table: table(["circuit", "category", "cones", "CM ÷ CSE-flat", "CM ÷ plain CSE"],
      d.circuits.map(c => [c.circuit, c.category, c.n, f(c.cm_cse_flat, 4), f(c.cm_cse, 4)])),
    prov: d.provenance,
    note: "<b>Why the two arms differ so cleanly here.</b> On AND/INV circuits every gate has two inputs, so " +
      "there are no long same-operator chains for CM to merge that flattening has not already merged. The " +
      `instruction-count ratio and the executed-operation ratio against CSE-flat are both exactly ` +
      `${f(d.mechanism.instr_ratio_cm_cse_flat, 3)}. The mechanism predicted parity on this corpus and parity ` +
      "is what was measured — which is stronger evidence than a favourable number would have been.",
  });
};

FIG.pods = () => {
  const d = DATA.e5_pods;
  return card({
    id: "fig-pods",
    scope: "5 independent Linux pods · AMD EPYC · frozen corpus, SHA-256 verified on each pod",
    title: "The same experiment, five different machines",
    caption: "Each pod ran the identical frozen corpus and driver. Identity fields matched exactly, so any " +
      "difference between pods is timing, not a different workload.",
    svg: forest(d.pods.map(p => ({
      label: p.label, value: p.blocked, lo: p.lo, hi: p.hi, group: "pod",
      scope: `${p.platform.split("-x86_64")[0]} · numpy ${p.numpy} · ${p.n_formulas} formulas`,
      basis: `per-pod stratified bootstrap · identity exact ${p.identity_exact} · corpus SHA ok ${p.corpus_sha_ok} · CI excludes parity ${p.ci_excludes_parity}`,
    })), {
      domain: pad(d.pods.flatMap(p => [p.blocked, p.lo, p.hi]).concat([1.0]), 0.01), ref: 1.0, padL: 120,
      xTitle: "CM kernel ÷ plain-CSE kernel (blocked, geometric mean)", arm: "CM / plain CSE",
      title: "Per-pod replication",
    }),
    table: table(["pod", "blocked", "95% CI", "round-robin", "CM ÷ CSE-flat", "identity exact", "corpus SHA ok", "CI excludes parity"],
      d.pods.map(p => [p.label, f(p.blocked, 4), `[${f(p.lo, 4)}, ${f(p.hi, 4)}]`, f(p.rr, 4),
        f(p.cm_cse_flat, 4), String(p.identity_exact), String(p.corpus_sha_ok), String(p.ci_excludes_parity)])),
    prov: d.provenance,
    note: `Verdict: <b>${d.verdict}</b>. Pod-to-pod spread ${f(d.spread.geomean_spread, 4)}, ` +
      `standard deviation ${f(d.spread.sigma_across_pods, 4)}, against a local reference of ${f(d.local_reference, 4)}. ` +
      "Pods are reported individually and never pooled into a single cross-machine figure.",
  });
};

FIG.ambientN = () => {
  const d = DATA.e8_ambient_n;
  const ks = Array.from(new Set(d.rows.map(r => r.live_k)));
  return card({
    id: "fig-ambient",
    scope: "local synthetic · same protocol as the superseded V4 wrapper experiment · 8 formulas per cell",
    title: "Adding unused variables to the namespace changes nothing",
    caption: "Each group holds semantic support fixed and varies only how many variables exist in the " +
      "surrounding namespace. If nominal variable count drove cost, these bars would climb. They do not — " +
      `the spread at live_k=16 is ${T("b4.k16.spread")}. This is why every axis on this site is live_k.`,
    legend: [[S1, "ambient n = 16"], [S2, "ambient n = 20"], [S3, "ambient n = 24"]],
    svg: groupedCols({
      height: 290, labelBars: true, fmtVal: (v) => FMT.x2(v), ref: 1.0,
      yTitle: "CM ÷ BitSet (paired geometric mean)", xTitle: "live_k — semantic support (held fixed within group)",
      groups: ks.map(k => {
        const cells = d.rows.filter(r => r.live_k === k);
        const v = {};
        cells.forEach(c => { v["n" + c.ambient_n] = c.geomean; });
        return { label: "live_k = " + k, values: v, tip: `${cells[0].n} formulas per cell` };
      }),
      series: [
        { key: "n16", label: "n = 16", color: S1 },
        { key: "n20", label: "n = 20", color: S2 },
        { key: "n24", label: "n = 24", color: S3 },
      ],
    }),
    table: table(["live_k", "ambient n", "formulas", "paired geomean", "median", "p10–p90", "CM µs", "BitSet µs"],
      d.rows.map(r => [r.live_k, r.ambient_n, r.n, f(r.geomean, 3), f(r.median, 3),
        `${f(r.p10, 2)}–${f(r.p90, 2)}`, us(r.cm_us), us(r.bitset_us)])),
    prov: d.provenance,
    note: "Note what carries nominal n here: it is the <em>series</em>, not the axis. The axis is live_k, " +
      "as everywhere else on this site — which is what makes the comparison within each group a " +
      "controlled one.",
  });
};

FIG.guard = () => {
  const d = DATA.e9_guard;
  const byDepth = {};
  d.rows.forEach(r => { (byDepth[r.depth] = byDepth[r.depth] || []).push(r); });
  const depths = Object.keys(byDepth).map(Number).sort((a, b) => a - b);
  const ns = Array.from(new Set(d.rows.map(r => r.n))).sort((a, b) => a - b);
  return card({
    id: "fig-guard",
    scope: `local synthetic · ${commas(d.totals.trials)} fresh post-repair trials across 15 cells`,
    title: "The safety rail: when the system refuses to answer, and whether it is ever wrong to",
    caption: "Explicit truth vectors double in size with every added live variable, so the system declines to " +
      "produce one above the guard limit. The bars show how often it declined; the counters below show whether " +
      "it ever declined incorrectly or leaked an oversized result. This is the one chart whose x axis is " +
      "nominal n rather than live_k, because the question it answers — how often is a randomly drawn " +
      "expression from a namespace of this size declined — is genuinely about the namespace.",
    legend: depths.map((dep, i) => [[S1, S2, S3][i % 3], "expression depth " + dep]),
    svg: groupedCols({
      height: 290, labelBars: true, fmtVal: (v) => Math.round(v * 100) + "%", max: 1.05, tickDigits: 1,
      fmtTick: (v) => Math.round(v * 100) + "%",
      yTitle: "share of trials declined", xTitle: "nominal n (variables available in the namespace)",
      groups: ns.map(n => {
        const v = {};
        depths.forEach(dep => {
          const cell = d.rows.find(r => r.n === n && r.depth === dep);
          if (cell) v["d" + dep] = cell.declined_rate;
        });
        const cells = d.rows.filter(r => r.n === n);
        return { label: "n = " + n, values: v,
          tip: "median live_k " + cells.map(c => `d${c.depth}:${f(c.median_live_k, 1)}`).join(" · ") };
      }),
      series: depths.map((dep, i) => ({ key: "d" + dep, label: "depth " + dep, color: [S1, S2, S3][i % 3] })),
    }),
    table: table(["nominal n", "depth", "trials", "median live_k", "live_k range", "declined", "wrong guards", "oversized outputs"],
      d.rows.map(r => [r.n, r.depth, r.trials, f(r.median_live_k, 1), `${r.min_live_k}–${r.max_live_k}`,
        FMT.pct0(100 * r.declined_rate), r.wrong_guard, r.oversized])),
    prov: d.provenance,
    note: `Across all ${commas(d.totals.trials)} trials: <b>${d.totals.wrong_guard} wrong guard decisions</b> and ` +
      `<b>${d.totals.oversized} oversized outputs</b>. Note also that at depth 4 the median semantic support is ` +
      `${T("guard.depth4.medk.min")}–${T("guard.depth4.medk.max")} regardless of how many variables exist — ` +
      "shallow expressions simply do not use many of them.",
  });
};

FIG.compileScaling = () => {
  const d = DATA.e10_compile_scaling;
  const ladder = d.cases.filter(c => c.family === "shared_ladder").sort((a, b) => a.unfolded - b.unfolded);
  const others = d.cases.filter(c => c.family !== "shared_ladder");
  return card({
    id: "fig-compile",
    scope: `local synthetic · ${d.n_cases} constructed cases across ${d.families.length} families`,
    title: "Compilation tracks the shared graph, not the expanded tree",
    caption: "The controlled ladder family (blue line) is the money plot: every step doubles what a naive " +
      "tree-walking compiler would have to touch, while the shared graph grows by a constant. Preparation time " +
      "follows the graph. The grey cloud is the other families, which vary in several ways at once.",
    legend: [[S1, "controlled shared-ladder family"], [S2, "other case families (confounded)"]],
    svg: xyPlot({
      height: 330, logX: true, logY: true,
      xDomain: [8, Math.max(...d.cases.map(c => Math.max(c.unfolded, 8))) * 2.5],
      yDomain: [Math.min(...d.cases.map(c => c.cm_prep_us)) * 0.7,
                Math.max(...d.cases.map(c => c.cm_prep_us)) * 1.6],
      fmtX: (v) => v >= 1e6 ? (v / 1e6) + "M" : v >= 1000 ? (v / 1000) + "k" : String(v),
      fmtY: (v) => us(v),
      xTitle: "occurrences a tree-unfolding compiler would visit (log scale)",
      yTitle: "CM preparation time, µs (log scale)",
      title: "Preparation versus unfolded size",
      series: [
        { label: "other families", color: S2, r: 3.5,
          points: others.map(c => ({ x: Math.max(c.unfolded, 8), y: c.cm_prep_us,
            label: c.id, tip: `${c.family} · ${commas(c.structural_nodes)} shared nodes · ${commas(c.unfolded)} unfolded · prep ${us(c.cm_prep_us)}` })) },
        { label: "shared ladder", color: S1, line: true,
          points: ladder.map(c => ({ x: Math.max(c.unfolded, 8), y: c.cm_prep_us,
            label: c.id, tip: `${commas(c.structural_nodes)} shared nodes · ${commas(c.unfolded)} unfolded · sharing factor ${commas(Math.round(c.sharing_factor))}× · prep ${us(c.cm_prep_us)}` })) },
      ],
    }),
    table: table(["case", "family", "shared nodes", "unfolded occurrences", "sharing factor", "CM prep", "CSE-flat prep", "prep ratio"],
      d.cases.map(c => [c.id, c.family, commas(c.structural_nodes), commas(c.unfolded),
        commas(Math.round(c.sharing_factor)) + "×", us(c.cm_prep_us), us(c.cse_flat_prep_us),
        FMT.x2(c.prep_ratio_cm_vs_cse)])),
    prov: d.provenance,
    note: `The extreme case compiles an expression whose unfolded form has ${T("b3.ladder.unfolded")} ` +
      `occurrences — but only ${T("b3.ladder.nodes")} distinct shared nodes — in ${T("b3.ladder.prep_us")}. ` +
      `Packed outputs agreed across all arms on all ${d.n_cases} cases, so the fast path is not a shortcut ` +
      "past correctness. The grey cloud drifts because those families vary operator mix and depth together; " +
      "only the ladder isolates sharing.",
  });
};

FIG.strata = () => {
  const d = DATA.e3_local_strata;
  return card({
    id: "fig-strata",
    scope: "local synthetic corpus · blocked schedule · CM kernel ÷ plain-CSE kernel",
    title: "Where the kernel advantage comes from — and where it does not",
    caption: "The same headline ratio broken out by expression family and shape. Darker means a larger CM " +
      "advantage. The pattern is mechanistic: the advantage lives where there are long same-operator chains " +
      "to merge, and thins out where there are not.",
    svg: heatGrid({
      rows: d.families, cols: d.shapes, arm: "CM ÷ plain CSE",
      cells: d.by_family_shape.map(c => ({ row: c.family, col: c.shape, value: c.geomean,
        lo: c.lo, hi: c.hi, n: c.n, basis: c.basis })),
      title: "Family × shape interaction grid", cellW: 140, padL: 130,
    }),
    svg2: forest(d.by_live_k.map(r => ({
      label: "live_k = " + r.live_k, value: r.geomean, lo: r.lo, hi: r.hi, group: "local",
      scope: `${r.n} formulas`, basis: r.basis,
    })), { domain: pad(d.by_live_k.flatMap(r => [r.geomean, r.lo, r.hi]).concat([1.0]), 0.01), ref: 1.0, padL: 140,
      xTitle: "CM kernel ÷ plain-CSE kernel by semantic support", arm: "CM / plain CSE",
      title: "Local strata by live_k" }),
    table: table(["cell", "formulas", "geomean", "95% CI", "clustering basis"],
      d.by_family_shape.concat(d.by_live_k).map(r => [r.group, r.n, f(r.geomean, 4),
        `[${f(r.lo, 4)}, ${f(r.hi, 4)}]`, r.basis])),
    prov: d.provenance,
    note: "These are the cells the summary actually reports — the family × shape interaction, not invented " +
      "family-only marginals. Identity fields matched the archived run exactly " +
      `(${T("b1.identity_mismatches")} mismatches over ${T("b1.n_formulas")} formulas), so this is a replay of ` +
      "the same workload, not a re-generated one.",
  });
};

FIG.schedule = () => {
  const d = DATA.e14_schedule;
  return card({
    id: "fig-schedule",
    scope: "every source in the campaign · blocked and round-robin measured separately",
    title: "Two measurement orders, always reported apart",
    caption: "“Blocked” times all of one method then all of the other; “round-robin” alternates. They stress " +
      "caches and CPU state differently, so they are two different measurements of the same thing — and they " +
      "are never averaged together.",
    legend: [[S1, "blocked"], [S2, "round-robin"]],
    svg: dumbbell(d.rows.map(r => ({
      label: r.source, a: r.blocked, b: r.rr,
      tip: `${r.arm} · round-robin is ${r.delta_pct >= 0 ? "+" : ""}${f(r.delta_pct, 2)}% versus blocked`,
    })), {
      // Domain derived from the data plus the parity reference, so no row and no
      // reference line can ever be clipped out of the viewport by a stale literal.
      domain: pad(d.rows.flatMap(r => [r.blocked, r.rr]).concat([1.0]), 0.01),
      ref: 1.0, padL: 235, aLabel: "blocked", bLabel: "round-robin",
      xTitle: "geometric mean ratio (arm differs by row — see table)", title: "Schedule comparison",
    }),
    table: table(["source", "arm", "blocked", "round-robin", "difference"],
      d.rows.map(r => [r.source, r.arm, f(r.blocked, 4), f(r.rr, 4), FMT.pctsign2(r.delta_pct)])),
    prov: d.provenance,
    note: "The rows use two different arms — the local and pod rows compare CM against plain CSE, the EPFL row " +
      "against CSE-flat — because each source's primary comparison is the one that source was designed to make. " +
      "They share an axis only because both are ratios near parity; they are not a single series.",
  });
};

FIG.discrepancies = () => {
  const d = DATA.e17_discrepancies;
  return card({
    id: "fig-discrepancies",
    scope: "the two open claim-map discrepancies · visualised from the raw files that exposed them",
    title: "The discrepancies change wording, not the campaign verdict",
    caption: "The old “within about 1–2%” schedule sentence holds for the archive, EPFL and pods, but not for " +
      "the fresh B1 replay. The replay-versus-archive economics moved only slightly, which is why the site uses " +
      "fresh values and keeps the workload-dependent conclusion.",
    svg: hBars(d.schedule_rows.map(r => ({
      label: r.label, value: r.delta_pct, color: r.delta_pct > 2 ? "var(--critical)" : S2, tip: r.scope,
    })), {
      max: 15, ref: 2, refLabel: "old ≈2% wording", title: "Absolute schedule shift",
      xTitle: "absolute blocked-to-round-robin shift", fmtTick: v => f(v, 0) + "%",
      fmtVal: v => f(v, 2) + "%",
    }),
    visual: metricComparisons(d.replay_vs_archive),
    table: table(["scope", "absolute schedule shift", "what it represents"],
      d.schedule_rows.map(r => [r.label, f(r.delta_pct, 2) + "%", r.scope])),
    prov: d.provenance,
    note: "Red means the scope exceeds the sentence's old ~2% shorthand; it does not mean the benchmark failed. " +
      "Blocked and round-robin remain separate everywhere, so the protocol rule itself is intact.",
  });
};

FIG.frontierMap = () => {
  const items = DATA._content.frontier.items;
  return card({
    id: "fig-frontier-map",
    scope: "10 open questions · grouped by evidence state, not ranked by optimism",
    title: "The frontier is mostly measurement work, with two formal gaps and one unmapped boundary",
    caption: "Four questions already have partial or negative evidence; three cheap measurements are explicitly " +
      "next; two capabilities exist without demonstrated practical value; one boundary has not been explored. " +
      "That is a sharper research programme than a generic list of future work.",
    visual: frontierLanes(items),
    table: table(["question", "evidence state", "downside case"],
      items.map(it => [it.visual_label || it.title, it.status.replace(/-/g, " "), P(it.downside)]), "wrap"),
    prov: ["deliverables_n22_24/cm_master_content_2026_08_03.json :: frontier.items[]"],
  });
};

FIG.roadmap = () => {
  const rows = DATA._content.frontier.roadmap;
  const costName = v => ({1: "low", 2: "medium", 3: "high"})[Math.round(v)] || "";
  return card({
    id: "fig-roadmap",
    scope: "publication roadmap · priority order and qualitative effort category",
    title: "The first four decisions are low-cost measurements; formal proof comes last",
    caption: "The order is deliberate: measure whether reuse exists, find where setup time goes, validate routing, " +
      "and study cache behaviour before funding heavier workload implementations or formal equivalence work. " +
      "The graph encodes authored effort categories, not benchmark timings.",
    svg: hBars(rows.map(r => ({
      label: r.priority + " · " + r.experiment, value: r.cost_level, color: r.cost_level === 1 ? S1 : r.cost_level === 2 ? S2 : S3,
      tip: `${r.decision} · ${r.what_it_settles}`,
    })), {
      max: 3.25, padL: 285, rowH: 34, title: "Roadmap effort by priority",
      xTitle: "qualitative effort category", fmtTick: costName, fmtVal: costName,
    }),
    table: table(["priority", "experiment", "decision unlocked", "effort", "what it settles"],
      rows.map(r => [r.priority, r.experiment, r.decision, r.cost_label, r.what_it_settles]), "wrap"),
    prov: [
      "deliverables_n22_24/cm_master_content_2026_08_03.json :: frontier.roadmap[]",
      "deliverables_n22_24/CM_GAP_POST_ACCEPTANCE_OPTIMIZATION_DECISION_2026-08-03.md :: ranked next tests and optimisations",
    ],
  });
};

FIG.auditLadder = () => {
  const chain = DATA._content.chain;
  return card({
    id: "fig-audit-ladder",
    scope: "14 audit, repair, replication and external-validation passes · July–August 2026",
    title: "The evidence chain repeatedly narrowed claims before it strengthened them",
    caption: "The sequence did not merely accumulate confirmations. It exposed unfair comparisons, retracted the " +
      "largest headline, repaired the baseline, fixed the pass mark in advance, and only then added independent, " +
      "cross-machine and external evidence.",
    visual: auditLadder(chain),
    table: table(["pass", "date", "stage", "outcome"],
      chain.map((step, i) => [i + 1, step.date, step.stage, P(step.outcome)]), "wrap"),
    prov: ["deliverables_n22_24/cm_master_content_2026_08_03.json :: chain[] and each chain entry's cited audit artifact"],
  });
};

FIG.correctionsTable = () => {
  const rows = DATA._superseded;
  return h("div", { class: "tablewrap" }, [
    table(["superseded figure", "what it claimed", "why it was wrong", "what replaced it", "corrected"],
      rows.map(c => [
        `<span class="strike">${c.superseded_number}</span>`,
        P(c.what_it_claimed), P(c.why_wrong), P(c.replaced_by), c.date_or_pass,
      ]), "wrap"),
  ]);
};

FIG.flagsBlock = () => {
  const wrap = h("div");
  DATA._flags.forEach(fl => {
    wrap.append(banner("warn", "Claim-map row " + fl.claim_row,
      [fl.finding, "<b>Consequence:</b> " + fl.consequence]));
  });
  return wrap;
};

/* ------------------------------------------------------------ footer */
function pageFooter(extra, minimal) {
  const M = DATA._campaign;
  const foot = h("footer");
  if (minimal) {
    foot.append(h("p", {
      html: "Generated from the project's own measurement files, not retyped from any summary. " +
        "Every figure quoted here is stated with its source, its uncertainty and its limits in the " +
        '<a href="index.html">full knowledge base</a>.',
    }));
    if (extra) foot.append(h("p", { html: P(extra) }));
    return foot;
  }
  foot.append(h("p", {
    html:
      `Built from evidence revision <code>${M.evidence_revision.slice(0, 7)}</code> (campaign revision <code>${M.campaign_revision.slice(0, 7)}</code>) ` +
      `by <code>cm_master_build_2026_08_03.py</code>, which reads every number from the evidence files listed under each figure. ` +
      `No benchmark was re-run and no committed evidence file was modified to produce this site.`,
  }));
  foot.append(h("p", {
    html:
      `Local measurements: ${M.local_env.platform}, ${M.local_env.cpu}, Python ${M.local_env.python}, numpy ${M.local_env.numpy}. ` +
      `Pod measurements: Linux / AMD EPYC, cpu3c flavour, all pods terminated (${M.all_pods_terminated}). ` +
      `Total cloud spend for the whole campaign ${FMT.usd(M.cost_usd)} against a $${M.cost_cap_usd.toFixed(2)} cap. ` +
      `Test suite: ${M.tests}.`,
  }));
  if (extra) foot.append(h("p", { html: P(extra) }));
  return foot;
}
