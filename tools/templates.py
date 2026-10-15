"""Explainer slide templates. Each is a content block + a GSAP timeline, dropped into one shared, brand-driven page.

Every template works in 9:16, 16:9 and 1:1, full-frame or split (speaker's face card on the left in 16:9, on top in
9:16). Labels are placeholders: Claude Code replaces them with the speaker's own words.
Animation FEEL (smooth / punchy / minimal) comes from the brand and is applied through the enter()/reveal() helpers.

Building blocks shared by every template (all styled from brand.css):
  .b-pill            eyebrow label in a filled pill (draws open from the centre)
  .b-headline.split  headline revealed word by word from behind a mask
  .swash             a word inside a headline gets a hand-drawn underline that draws itself on
Backdrop (photo, push-in, tone) is set per graphic: explainer.py new … --tone dark|light --backdrop <photo>.
"""

TEMPLATES = {
    'steps': {
        'about': 'Numbered cards build one by one on the words that name them; each finished step gets a tick. '
                 'For processes, frameworks, "three reasons".',
        'html': '''
        <div id="eyebrow" class="b-pill">EYEBROW</div>
        <h1 id="headline" class="b-headline split">The idea in <span class="swash">their</span> words</h1>
        <div class="b-steps">
          <div class="b-step" id="i1"><div class="num"><svg viewBox="0 0 100 100"><circle class="ring" cx="50" cy="50" r="45" pathLength="1"/><path class="tick" d="M31 52 L44 65 L70 37" pathLength="1"/></svg><span>01</span></div>
            <div class="txt"><b>First point</b><small>a short detail, in their words</small></div></div>
          <div class="b-step" id="i2"><div class="num"><svg viewBox="0 0 100 100"><circle class="ring" cx="50" cy="50" r="45" pathLength="1"/><path class="tick" d="M31 52 L44 65 L70 37" pathLength="1"/></svg><span>02</span></div>
            <div class="txt"><b>Second point</b><small>second detail, in their words</small></div></div>
          <div class="b-step last" id="i3"><div class="num"><svg viewBox="0 0 100 100"><circle class="ring" cx="50" cy="50" r="45" pathLength="1"/><path class="tick" d="M31 52 L44 65 L70 37" pathLength="1"/></svg><span>03</span></div>
            <div class="txt"><b>The payoff</b><small>the result, in their words</small></div></div>
        </div>''',
        'vars': {'t1': 1.1, 't2': 2.0, 't3': 2.9},
        'js': '''pill("#eyebrow", 0.05); reveal("#headline", 0.2);
        stepsBuild(["#i1", "#i2", "#i3"], [V.t1, V.t2, V.t3]);''',
    },
    'compare': {
        'about': 'Two cards, this vs that. For "most people think X, but Y", before/after, wrong way/right way.',
        'html': '''
        <div id="eyebrow" class="b-pill">EYEBROW</div>
        <div class="b-compare">
          <div class="col" id="left"><div class="lab">Most people</div><div class="big">The old way</div></div>
          <div class="vs" id="vs">vs</div>
          <div class="col win" id="right"><div class="lab">Instead</div><div class="big">The better way</div></div>
        </div>''',
        'vars': {'t1': 0.6, 't2': 1.8},
        'js': '''pill("#eyebrow", 0.05); enter("#left", V.t1); enter("#vs", V.t2 - 0.25); enter("#right", V.t2);
        dim("#left", V.t2 + 0.5);''',
    },
    'stat': {
        'about': 'One big number that rolls into place like an odometer, underlined, with its label. Only for '
                 'numbers the speaker actually says. Set data-value (digits and commas), data-prefix, data-suffix.',
        'html': '''
        <div class="b-statcard" id="card">
          <div id="eyebrow" class="b-pill">EYEBROW</div>
          <div class="b-stat" id="stat"><span class="pre" id="pre"></span><span class="odo" id="num" data-value="10"></span><span class="unit" id="unit">x</span></div>
          <svg class="b-statline" viewBox="0 0 600 40" preserveAspectRatio="none"><path id="statline" d="M8 28 C 120 10, 300 4, 470 14 S 585 12, 594 6" pathLength="1"/></svg>
          <div class="rule" id="rule"></div>
          <div id="label" class="b-stat-label split">what the number means, in their words</div>
        </div>''',
        'vars': {'t1': 0.5, 't2': 1.9},
        'js': '''enter("#card", 0.0); pill("#eyebrow", 0.15); prefix("#pre"); roll("#num", V.t1, 1.3);
        enter("#pre", V.t1); enter("#unit", V.t1 + 1.0); draw("#statline", V.t1 + 0.9, 0.8);
        grow("#rule", V.t2 - 0.3); reveal("#label", V.t2);''',
    },
    'quote': {
        'about': 'A pull quote, set large, with the key phrase underlined. For the line people will screenshot.',
        'html': '''
        <div class="b-quote">
          <div class="mark" id="mark">“</div>
          <blockquote id="q" class="split">The line people will <span class="swash">screenshot</span>.</blockquote>
          <div class="by" id="by">NAME</div>
        </div>''',
        'vars': {'t1': 0.3},
        'js': '''enter("#mark", 0.05); reveal("#q", V.t1); enter("#by", V.t1 + 1.0);''',
    },
    'timeline': {
        'about': 'Stages along a rail that fills as the speaker moves through them, ending on the goal. '
                 'For stages, time horizons, a journey from here to there.',
        'html': '''
        <div id="eyebrow" class="b-pill">EYEBROW</div>
        <h1 id="headline" class="b-headline split">From here to <span class="swash">there</span></h1>
        <div class="b-tl" id="tl">
          <div class="rail"><div class="fill" id="railfill"></div></div>
          <div class="node" id="p1"><div class="dot"><i></i></div><div class="lab"><span class="tag">Stage 1</span><b>Stage one</b></div></div>
          <div class="node" id="p2"><div class="dot"><i></i></div><div class="lab"><span class="tag">Stage 2</span><b>Stage two</b></div></div>
          <div class="node" id="p3"><div class="dot"><i></i></div><div class="lab"><span class="tag">Stage 3</span><b>Stage three</b></div></div>
          <div class="node end" id="p4"><div class="dot"><svg viewBox="0 0 48 48"><path d="M8 23 L24 9 L40 23 M13 19 V39 H35 V19 M21 39 V29 H27 V39" pathLength="1"/></svg></div>
            <div class="lab"><span class="tag">Finish</span><b>The goal</b></div></div>
        </div>''',
        'vars': {'t1': 1.1, 't2': 1.8, 't3': 2.5, 't4': 3.2},
        'js': '''pill("#eyebrow", 0.05); reveal("#headline", 0.2);
        timelineBuild(["#p1", "#p2", "#p3", "#p4"], [V.t1, V.t2, V.t3, V.t4]);''',
    },
    'tiers': {
        'about': 'A staircase: each level builds up from the floor on the words that name it, and a marker hops '
                 'up to the top step. For levels, ladders, foundations, "good / better / best", sizes.',
        'html': '''
        <div id="eyebrow" class="b-pill">EYEBROW</div>
        <h1 id="headline" class="b-headline split">Up, one <span class="swash">step</span> at a time</h1>
        <div class="b-stairs" id="stairs">
          <div class="stair" id="l1"><div class="blk" style="height:46%"><div class="cap"><b>Level one</b><small>the base</small></div><span>01</span></div></div>
          <div class="stair" id="l2"><div class="blk" style="height:70%"><div class="cap"><b>Level two</b><small>the middle</small></div><span>02</span></div></div>
          <div class="stair top" id="l3"><div class="blk" style="height:94%"><div class="cap"><b>Level three</b><small>the top</small></div><span>03</span></div></div>
          <div class="hopper" id="hopper"></div>
        </div>''',
        'vars': {'t1': 1.1, 't2': 2.0, 't3': 2.9},
        'js': '''pill("#eyebrow", 0.05); reveal("#headline", 0.2);
        stairsBuild(["#l1", "#l2", "#l3"], [V.t1, V.t2, V.t3]);''',
    },
}
TEMPLATES['stairs'] = TEMPLATES['tiers']     # same template, friendlier name

FEELS = {
    'smooth': 'Calm and premium: elements glide up out of a soft blur on a gentle ease.',
    'punchy': 'Energetic: elements pop in with a little overshoot, faster beats.',
    'minimal': 'Quiet and editorial: slow fades only, no movement.',
}

FEEL_JS = {
    'smooth': '''const F = {dur: 0.75, ease: "brand", y: 34, scale: 1, blur: 10, word: 0.07};''',
    'punchy': '''const F = {dur: 0.45, ease: "back.out(2)", y: 0, scale: 0.72, blur: 0, word: 0.05};''',
    'minimal': '''const F = {dur: 0.9, ease: "power1.out", y: 0, scale: 1, blur: 0, word: 0.09};''',
}

HELPERS_JS = '''
const $ = (s) => typeof s === "string" ? document.querySelector(s) : s;
const $$ = (s, root) => [...(root || document).querySelectorAll(s)];
const VERTICAL = $("#root").classList.contains("vertical");
function enter(s, at) {
  tl.fromTo(s, {opacity: 0, y: F.y, scale: F.scale, filter: "blur(" + F.blur + "px)"},
               {opacity: 1, y: 0, scale: 1, filter: "blur(0px)", duration: F.dur, ease: F.ease}, at);
}
function pill(s, at) {
  tl.fromTo(s, {opacity: 0, clipPath: "inset(0% 50% 0% 50% round 999px)"},
               {opacity: 1, clipPath: "inset(0% 0% 0% 0% round 999px)", duration: 0.7, ease: "power3.out"}, at);
}
function draw(s, at, dur) { tl.fromTo(s, {strokeDashoffset: 1}, {strokeDashoffset: 0, duration: dur || 0.7, ease: "power2.inOut"}, at); }
function grow(s, at, until) { tl.fromTo(s, {scaleX: 0}, {scaleX: 1, duration: until ? Math.max(0.3, until - at) : 0.7, ease: "power3.out", transformOrigin: "0% 50%"}, at); }
function dim(s, at) { tl.to(s, {opacity: 0.4, duration: 0.5}, at); }
const SWASH = '<svg class="swash-svg" viewBox="0 0 300 34" preserveAspectRatio="none"><path d="M5 26 C 60 12, 150 7, 236 13 S 288 10, 295 4" pathLength="1"/></svg>';
function splitWords(el) {
  const out = [];
  const word = (child) => { const w = document.createElement("span"); w.className = "w"; const i = document.createElement("span");
    i.className = "wi"; i.appendChild(child); w.appendChild(i); out.push(w); return w; };
  [...el.childNodes].forEach((n) => {
    if (n.nodeType === 3) {
      n.textContent.split(/(\\s+)/).forEach((p) => { if (!p) return;
        if (/^\\s+$/.test(p)) out.push(document.createTextNode(" ")); else word(document.createTextNode(p)); });
    } else {
      const w = word(n.cloneNode(true));
      if (n.classList && n.classList.contains("swash")) { w.classList.add("has-swash"); w.querySelector(".swash").insertAdjacentHTML("beforeend", SWASH); }
    }
  });
  el.innerHTML = ""; out.forEach((x) => el.appendChild(x));
}
function reveal(s, at) {
  const el = $(s); if (!el.querySelector(".wi")) splitWords(el);
  const words = $$(".wi", el);
  if (F.y || F.blur) tl.fromTo(words, {yPercent: 105, opacity: 0}, {yPercent: 0, opacity: 1, duration: F.dur, ease: F.ease, stagger: F.word}, at);
  else tl.fromTo(words, {opacity: 0, scale: F.scale}, {opacity: 1, scale: 1, duration: F.dur, ease: F.ease, stagger: F.word}, at);
  $$(".swash-svg path", el).forEach((p) => draw(p, at + 0.35 + words.length * F.word, 0.75));
}
function prefix(s) { const el = $(s), odo = el.parentElement.querySelector(".odo"); el.textContent = odo.dataset.prefix || ""; }
function roll(s, at, dur) {
  const el = $(s); const v = String(el.dataset.value); el.innerHTML = "";
  [...v].forEach((ch) => {
    if (/[0-9]/.test(ch)) {
      const col = document.createElement("span"); col.className = "dg"; const strip = document.createElement("span"); strip.className = "strip";
      for (let k = 0; k < 30; k++) { const d = document.createElement("span"); d.textContent = k % 10; strip.appendChild(d); }
      col.appendChild(strip); col.dataset.d = ch; el.appendChild(col);
    } else { const sp = document.createElement("span"); sp.className = "sep"; sp.textContent = ch; el.appendChild(sp); }
  });
  const stat = el.parentElement, card = el.closest(".b-statcard");
  if (card) {   // long numbers (141,827) shrink to fit the card
    const chars = v.length + (el.dataset.prefix || "").length * 0.5 + (el.dataset.suffix || "").length * 0.5;
    const avail = card.clientWidth - 120, now = parseFloat(getComputedStyle(stat).fontSize);
    stat.style.fontSize = Math.min(now, avail / (chars * 0.7)) + "px";
  }
  const unit = el.parentElement.querySelector(".unit"); if (unit && el.dataset.suffix !== undefined) unit.textContent = el.dataset.suffix;
  const cols = $$(".dg", el);
  tl.fromTo(el, {opacity: 0}, {opacity: 1, duration: 0.25}, at);
  cols.forEach((c, i) => {
    const target = 20 + parseInt(c.dataset.d, 10);
    tl.fromTo(c.querySelector(".strip"), {yPercent: -((i * 3) % 10) / 30 * 100},
      {yPercent: -target / 30 * 100, duration: dur + i * 0.14, ease: "power4.out"}, at);
  });
}
function stepsBuild(ids, times) {
  ids.forEach((id, i) => {
    const el = $(id), at = times[i];
    tl.fromTo(el, {opacity: 0, y: 40, filter: "blur(8px)"}, {opacity: 1, y: 0, filter: "blur(0px)", duration: F.dur, ease: F.ease}, at);
    draw(el.querySelector(".ring"), at + 0.1, 0.6);
    tl.fromTo(el.querySelector(".num span"), {scale: 0.4, opacity: 0}, {scale: 1, opacity: 1, duration: 0.45, ease: "back.out(2.4)"}, at + 0.2);
    if (i > 0) {   // the previous step is done: tick it and step it back a little
      const prev = $(ids[i - 1]);
      tl.to(prev.querySelector(".num span"), {opacity: 0, scale: 0.5, duration: 0.25}, at);
      tl.to(prev.querySelector(".num"), {backgroundColor: "var(--fill)", duration: 0.3}, at);
      draw(prev.querySelector(".tick"), at + 0.1, 0.4);
      tl.to(prev, {opacity: 0.62, scale: 0.97, duration: 0.5, ease: "power2.out"}, at + 0.1);
    }
  });
}
function timelineBuild(ids, times) {
  const n = ids.length, fill = $("#railfill");
  tl.set(fill, VERTICAL ? {scaleY: 0, transformOrigin: "50% 0%"} : {scaleX: 0, transformOrigin: "0% 50%"}, 0);
  tl.fromTo(".b-tl .rail", {opacity: 0}, {opacity: 1, duration: 0.5}, times[0] - 0.3);
  ids.forEach((id, i) => {
    const el = $(id), at = times[i];
    if (i > 0) tl.to(fill, VERTICAL ? {scaleY: i / (n - 1), duration: 0.55, ease: "power2.inOut"} : {scaleX: i / (n - 1), duration: 0.55, ease: "power2.inOut"}, at - 0.5);
    tl.fromTo(el.querySelector(".dot"), {scale: 0.3, opacity: 0}, {scale: 1, opacity: 1, duration: 0.5, ease: "back.out(2.2)"}, at);
    const inner = el.querySelector(".dot i"); if (inner) tl.fromTo(inner, {scale: 0}, {scale: 1, duration: 0.4, ease: "back.out(3)"}, at + 0.15);
    const house = el.querySelector(".dot path"); if (house) draw(house, at + 0.1, 0.8);
    tl.fromTo(el.querySelector(".lab"), {opacity: 0, x: VERTICAL ? 34 : 0, y: VERTICAL ? 0 : 24, filter: "blur(6px)"},
      {opacity: 1, x: 0, y: 0, filter: "blur(0px)", duration: F.dur, ease: F.ease}, at + 0.08);
    if (i > 0) tl.to($(ids[i - 1]).querySelector(".lab"), {opacity: 0.6, duration: 0.4}, at + 0.1);
  });
}
function stairsBuild(ids, times) {
  const box = $("#stairs").getBoundingClientRect(), hop = $("#hopper");
  const pts = ids.map((id) => { const r = $(id).querySelector(".blk").getBoundingClientRect();
    return {x: r.left - box.left + r.width / 2, y: r.top - box.top}; });
  tl.set(hop, {x: pts[0].x, y: pts[0].y, xPercent: -50, yPercent: -100, scale: 0, opacity: 0}, 0);
  ids.forEach((id, i) => {
    const el = $(id), at = times[i];
    tl.fromTo(el.querySelector(".blk"), {scaleY: 0, transformOrigin: "50% 100%"}, {scaleY: 1, duration: 0.7, ease: "power4.out"}, at);
    tl.fromTo(el.querySelector(".blk > span"), {opacity: 0, y: 20}, {opacity: 1, y: 0, duration: 0.5, ease: "power3.out"}, at + 0.3);
    tl.fromTo(el.querySelector(".cap"), {opacity: 0, y: 26, filter: "blur(6px)"}, {opacity: 1, y: 0, filter: "blur(0px)", duration: F.dur, ease: F.ease}, at + 0.2);
    if (i === 0) tl.to(hop, {scale: 1, opacity: 1, duration: 0.4, ease: "back.out(3)"}, at + 0.55);
    else {   // hop up onto the new step: across on an even pace, up then down on gravity
      tl.to(hop, {x: pts[i].x, duration: 0.5, ease: "power1.inOut"}, at + 0.45);
      tl.to(hop, {y: Math.min(pts[i - 1].y, pts[i].y) - 70, duration: 0.25, ease: "power2.out"}, at + 0.45);
      tl.to(hop, {y: pts[i].y, duration: 0.25, ease: "power2.in"}, at + 0.7);
      tl.to(hop, {scaleY: 0.8, scaleX: 1.15, duration: 0.08, yoyo: true, repeat: 1}, at + 0.95);
    }
  });
}
'''

TEMPLATE_CSS = '''
/* steps: "how it works" cards */
.b-steps { margin-top: 52px; display: flex; flex-direction: column; gap: 24px; }
.landscape .b-steps { display: grid; grid-template-columns: repeat(3, 1fr); }
.b-step { display: flex; align-items: center; gap: 34px; padding: 34px 38px; border-radius: 30px; background: var(--card);
  border: 1.5px solid var(--card-line); box-shadow: var(--card-shadow); }
.landscape .b-step { flex-direction: column; align-items: flex-start; }
.b-step .num { position: relative; flex: none; width: 120px; height: 120px; border-radius: 50%; display: grid; place-items: center;
  background: color-mix(in srgb, var(--fill) 26%, transparent); }
.b-step .num svg { position: absolute; inset: 0; width: 100%; height: 100%; }
.b-step .ring { fill: none; stroke: var(--fill); stroke-width: 4; stroke-dasharray: 1; transform: rotate(-90deg); transform-origin: 50% 50%; }
.b-step .tick { fill: none; stroke: var(--on-fill); stroke-width: 8; stroke-linecap: round; stroke-linejoin: round; stroke-dasharray: 1; stroke-dashoffset: 1; }
.b-step .num span { font: 600 46px/1 var(--font-display); color: var(--text); letter-spacing: .02em; }
.b-step .txt b { display: block; font: 700 var(--step)/1.12 var(--font-body); color: var(--text); letter-spacing: -.01em; }
.b-step .txt small { display: block; margin-top: 8px; font: 500 calc(var(--step) * .58)/1.3 var(--font-body); color: var(--muted); }
.b-step.last { border-color: var(--fill); }
/* compare */
.b-compare { margin-top: 44px; display: grid; grid-template-columns: 1fr auto 1fr; gap: 28px; align-items: stretch; }
.vertical .b-compare { grid-template-columns: 1fr; }
.b-compare .col { padding: 38px; border-radius: 26px; background: var(--card); border: 1.5px solid var(--card-line); box-shadow: var(--card-shadow); }
.b-compare .col.win { border: 3px solid var(--fill); }
.b-compare .lab { font: 700 22px/1 var(--font-body); letter-spacing: .2em; text-transform: uppercase; color: var(--muted); }
.b-compare .win .lab { color: var(--accent); }
.b-compare .big { margin-top: 16px; font: 600 calc(var(--h1) * .6)/1.08 var(--font-display); letter-spacing: -.02em; color: var(--text); }
.b-compare .vs { align-self: center; justify-self: center; font: 700 30px/1 var(--font-body); letter-spacing: .2em; text-transform: uppercase;
  color: var(--on-fill); background: var(--fill); padding: 14px 22px; border-radius: 999px; }
/* stat: the calculator card */
.b-statcard { padding: 64px 58px 68px; border-radius: 40px; background: var(--card); border: 1.5px solid var(--card-line); box-shadow: var(--card-shadow); }
.b-stat { margin-top: 34px; display: flex; align-items: flex-start; font: 600 calc(var(--h1) * 2.4)/1 var(--font-display);
  letter-spacing: -.04em; color: var(--text); font-variant-numeric: tabular-nums; white-space: nowrap; }
.b-stat .pre { font-size: .5em; margin: .12em .06em 0 0; color: var(--accent); }
.b-stat .unit { font-size: .5em; margin: .12em 0 0 .08em; color: var(--accent); }
.b-stat .odo { display: inline-flex; }
.b-stat .dg { display: inline-block; height: 1em; overflow: hidden; -webkit-mask-image: linear-gradient(transparent, #000 18%, #000 82%, transparent);
  mask-image: linear-gradient(transparent, #000 18%, #000 82%, transparent); }
.b-stat .strip { display: flex; flex-direction: column; }
.b-stat .strip span { display: block; height: 1em; line-height: 1; text-align: center; }
.b-stat .sep { display: inline-block; line-height: 1; }
.b-statline { display: block; width: 78%; height: 46px; margin-top: 4px; overflow: visible; }
.b-statline path { fill: none; stroke: var(--fill); stroke-width: 7; stroke-linecap: round; stroke-dasharray: 1; stroke-dashoffset: 1; }
.b-statcard .rule { margin-top: 30px; height: 2px; background: var(--card-line); }
.b-stat-label { margin-top: 28px; font: 600 var(--step)/1.25 var(--font-body); color: var(--text); max-width: 16em; }
/* quote */
.b-quote .mark { font: 700 calc(var(--h1) * 2)/0.7 var(--font-display); color: var(--fill); }
.b-quote blockquote { margin-top: 14px; font: 600 calc(var(--h1) * .86)/1.14 var(--font-display); letter-spacing: -.02em; color: var(--text); }
.b-quote .by { margin-top: 34px; font: 700 22px/1 var(--font-body); letter-spacing: .26em; color: var(--muted); }
/* timeline: a rail that fills */
.b-tl { position: relative; margin-top: 60px; display: flex; flex-direction: column; gap: 58px; }
.b-tl .rail { position: absolute; left: 49px; top: 50px; bottom: 60px; width: 8px; border-radius: 3px; background: var(--rail); }
.b-tl .rail .fill { position: absolute; inset: 0; border-radius: 3px; background: var(--fill); box-shadow: 0 0 22px color-mix(in srgb, var(--fill) 60%, transparent); }
.b-tl .node { position: relative; display: flex; align-items: center; gap: 34px; }
.b-tl .dot { flex: none; width: 104px; height: 104px; border-radius: 50%; display: grid; place-items: center; background: var(--card-solid);
  border: 5px solid var(--fill); box-shadow: var(--card-shadow); }
.b-tl .dot i { width: 36px; height: 36px; border-radius: 50%; background: var(--fill); }
.b-tl .end .dot { width: 128px; height: 128px; margin-left: -12px; background: var(--fill); }
.b-tl .end .dot svg { width: 68px; height: 68px; }
.b-tl .end .dot path { fill: none; stroke: var(--on-fill); stroke-width: 3.4; stroke-linecap: round; stroke-linejoin: round; stroke-dasharray: 1; stroke-dashoffset: 1; }
.b-tl .tag { display: inline-block; font: 700 24px/1 var(--font-body); letter-spacing: .2em; text-transform: uppercase; color: var(--accent); }
.b-tl b { display: block; margin-top: 10px; font: 700 var(--step)/1.1 var(--font-body); color: var(--text); letter-spacing: -.01em; }
.b-tl .end b { font-size: calc(var(--step) * 1.15); }
.landscape .b-tl { flex-direction: row; justify-content: space-between; gap: 20px; }
.landscape .b-tl .rail { left: 44px; right: 56px; top: 41px; bottom: auto; width: auto; height: 6px; }
.landscape .b-tl .node { flex-direction: column; align-items: flex-start; gap: 24px; max-width: 9em; }
/* tiers / stairs */
.b-stairs { position: relative; margin-top: 60px; height: 640px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; align-items: end; }
.landscape .b-stairs { height: 560px; }
.b-stairs .stair { height: 100%; display: flex; flex-direction: column; justify-content: flex-end; }
.b-stairs .cap b { display: block; font: 700 calc(var(--step) * .62)/1.12 var(--font-body); color: var(--text); letter-spacing: -.01em; }
.b-stairs .cap small { display: block; margin-top: 8px; font: 500 calc(var(--step) * .44)/1.3 var(--font-body); color: var(--muted); }
.b-stairs .blk { position: relative; border-radius: 22px 22px 8px 8px; background: var(--card); border: 1.5px solid var(--card-line);
  border-top: 8px solid var(--fill); box-shadow: var(--card-shadow); display: flex; flex-direction: column; justify-content: space-between; padding: 26px 24px; }
.b-stairs .blk span { font: 700 64px/1 var(--font-display); color: color-mix(in srgb, var(--text) 22%, transparent); }
.b-stairs .top .blk { background: var(--fill); border-color: var(--fill); }
.b-stairs .top .blk span { color: color-mix(in srgb, var(--on-fill) 40%, transparent); }
.b-stairs .top .cap b, .b-stairs .top .cap small { color: var(--on-fill); }
.b-stairs .hopper { position: absolute; left: 0; top: 0; width: 46px; height: 46px; border-radius: 50%; background: var(--on-fill);
  border: 7px solid var(--fill); box-shadow: 0 10px 24px rgba(0,0,0,.28); margin-top: -10px; }
'''


def page(name, template, W, H, duration, feel, split=False, tone='light', photo=None):
    t = TEMPLATES[template]
    vars_ = {**t['vars'], 'tOut': round(duration - 0.45, 2)}
    vertical = H > W
    layout = 'vertical' if vertical else 'landscape'
    import json
    backdrop = (f'<div class="bd-photo-wrap fill"><img class="bd-photo" id="bdphoto" src="{photo}" alt="" /></div>'
                if photo else '')
    return f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <!-- Local copies only: a render must never depend on the network. -->
    <script src="assets/js/gsap.min.js"></script>
    <script src="assets/js/CustomEase.min.js"></script>
    <!-- Brand tokens generated from my-studio/brand.json. Change the brand there, never here. -->
    <link rel="stylesheet" href="brand.css" />
    <style>
      html, body {{ width: {W}px; height: {H}px; }}
      #root {{ width: {W}px; height: {H}px; }}
      /* template: {template} · feel: {feel} · tone: {tone} · {"split (face card area left empty)" if split else "full frame"} */
    </style>
  </head>
  <body>
    <div id="root" class="b-root {layout} tone-{tone}{' split' if split else ''}{' has-photo' if photo else ''}"
         data-composition-id="{name}" data-start="0" data-duration="{duration}" data-width="{W}" data-height="{H}"
         data-composition-variables='{json.dumps(vars_)}'>
      {backdrop}
      <div class="bd-shade fill"></div>
      <div class="bd-grain fill"></div>
      <div id="content">
        <!-- EVERY label must be the speaker's own words from the transcript. Never invent claims or numbers. -->{t['html']}
      </div>
    </div>
    <script>
      gsap.registerPlugin(CustomEase);
      CustomEase.create("brand", "M0,0 C0.22,0.68 0.24,1 1,1");
      // Beat times = seconds from the graphic's start, on the moment the speaker SAYS that word in the cut.
      const V = Object.assign({json.dumps(vars_)},
        (window.__hyperframes && window.__hyperframes.getVariables && window.__hyperframes.getVariables()) || {{}});
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      {FEEL_JS[feel]}
      {HELPERS_JS}
      // slow push-in on the backdrop photo for the whole graphic
      if (document.querySelector("#bdphoto")) tl.fromTo("#bdphoto", {{scale: 1.14, xPercent: -1.5}}, {{scale: 1.0, xPercent: 1.5, duration: {duration}, ease: "none"}}, 0);
      tl.fromTo(".bd-shade", {{opacity: 0.6}}, {{opacity: 1, duration: 0.8, ease: "power2.out"}}, 0);
      {t['js']}
      tl.to("#content", {{ opacity: 0, y: -14, filter: "blur(6px)", duration: 0.38, ease: "power2.in" }}, V.tOut);
      window.__timelines["{name}"] = tl;
    </script>
  </body>
</html>
'''
