"""Explainer slide templates. Each is a content block + a GSAP timeline, dropped into one shared, brand-driven page.

Every template works in 9:16, 16:9 and 1:1, full-frame or split (speaker's face card on the left in 16:9, on top in
9:16). Labels are placeholders: Claude Code replaces them with the speaker's own words.
Animation FEEL (smooth / punchy / minimal) comes from the brand and is applied through enter()/settle() helpers.
"""

TEMPLATES = {
    'steps': {
        'about': 'Numbered points appear one by one on the words that name them. For frameworks, lists, "three reasons".',
        'html': '''
        <div id="eyebrow" class="b-eyebrow">EYEBROW</div>
        <h1 id="headline" class="b-headline">The idea in <em>their</em> words</h1>
        <div id="rule" class="b-rule"></div>
        <div class="b-steps">
          <div class="b-step" id="i1"><span class="n">1</span><span class="t">First point</span></div>
          <div class="b-step" id="i2"><span class="n">2</span><span class="t">Second point</span></div>
          <div class="b-step" id="i3"><span class="n">3</span><span class="t is-accent">The payoff</span></div>
        </div>''',
        'vars': {'t1': 1.0, 't2': 1.9, 't3': 2.8},
        'js': '''enter("#eyebrow", 0.1); enter("#headline", 0.2); grow("#rule", 0.45);
        ["#i1", "#i2", "#i3"].forEach((id, i) => enter(id, V["t" + (i + 1)]));''',
    },
    'compare': {
        'about': 'Two columns, this vs that. For "most people think X, but Y", before/after, wrong way/right way.',
        'html': '''
        <div id="eyebrow" class="b-eyebrow">EYEBROW</div>
        <div class="b-compare">
          <div class="col" id="left"><div class="lab">Most people</div><div class="big">The old way</div></div>
          <div class="vs" id="vs">vs</div>
          <div class="col win" id="right"><div class="lab">Instead</div><div class="big">The better way</div></div>
        </div>''',
        'vars': {'t1': 0.6, 't2': 1.8},
        'js': '''enter("#eyebrow", 0.1); enter("#left", V.t1); enter("#vs", V.t2 - 0.25); enter("#right", V.t2);
        dim("#left", V.t2 + 0.5);''',
    },
    'stat': {
        'about': 'One big number that counts up, with a label. Only for numbers the speaker actually says.',
        'html': '''
        <div id="eyebrow" class="b-eyebrow">EYEBROW</div>
        <div class="b-stat"><span id="num" data-to="10">0</span><span class="unit" id="unit">x</span></div>
        <div id="label" class="b-stat-label">what the number means, in their words</div>''',
        'vars': {'t1': 0.5, 't2': 1.8},
        'js': '''enter("#eyebrow", 0.1); enter("#num", V.t1); enter("#unit", V.t1 + 0.3); enter("#label", V.t2);
        countUp("#num", V.t1, 1.1);''',
    },
    'quote': {
        'about': 'A pull quote, set large, with the key phrase in the accent colour. For the line people will screenshot.',
        'html': '''
        <div class="b-quote">
          <div class="mark" id="mark">“</div>
          <blockquote id="q">The line people will <em>screenshot</em>.</blockquote>
          <div class="by" id="by">NAME</div>
        </div>''',
        'vars': {'t1': 0.3},
        'js': '''enter("#mark", 0.05); enter("#q", V.t1); enter("#by", V.t1 + 0.8);''',
    },
    'timeline': {
        'about': 'Points along a line: stages, time horizons, a journey from here to there.',
        'html': '''
        <div id="eyebrow" class="b-eyebrow">EYEBROW</div>
        <h1 id="headline" class="b-headline">From here to <em>there</em></h1>
        <div class="b-timeline">
          <div class="line" id="line"></div>
          <div class="pts">
            <div class="pt" id="p1"><span class="dot"></span><b>Stage one</b></div>
            <div class="pt" id="p2"><span class="dot"></span><b>Stage two</b></div>
            <div class="pt" id="p3"><span class="dot"></span><b>Stage three</b></div>
            <div class="pt end" id="p4"><span class="dot"></span><b>The goal</b></div>
          </div>
        </div>''',
        'vars': {'t1': 0.9, 't2': 1.6, 't3': 2.3, 't4': 3.0},
        'js': '''enter("#eyebrow", 0.1); enter("#headline", 0.2); grow("#line", 0.6, V.t4 - 0.4);
        ["#p1", "#p2", "#p3", "#p4"].forEach((id, i) => enter(id, V["t" + (i + 1)]));''',
    },
    'tiers': {
        'about': 'Stacked levels (a ladder or pyramid): Level 1 → 2 → 3, foundations, hierarchies.',
        'html': '''
        <div id="eyebrow" class="b-eyebrow">EYEBROW</div>
        <div class="b-tiers">
          <div class="tier t3" id="l3"><b>Level three</b><span>the top</span></div>
          <div class="tier t2" id="l2"><b>Level two</b><span>the middle</span></div>
          <div class="tier t1" id="l1"><b>Level one</b><span>the base</span></div>
        </div>''',
        'vars': {'t1': 0.8, 't2': 1.7, 't3': 2.6},
        'js': '''enter("#eyebrow", 0.1); enter("#l1", V.t1); enter("#l2", V.t2); enter("#l3", V.t3);''',
    },
}

FEELS = {
    'smooth': 'Calm and premium: elements glide up and fade in on a soft ease.',
    'punchy': 'Energetic: elements pop in with a little overshoot, faster beats.',
    'minimal': 'Quiet and editorial: slow fades only, no movement.',
}

FEEL_JS = {
    'smooth': '''const EASE = "brand"; function enter(s, at) { tl.fromTo(s, {opacity: 0, y: 22}, {opacity: 1, y: 0, duration: 0.6, ease: EASE}, at); }''',
    'punchy': '''const EASE = "back.out(2.2)"; function enter(s, at) { tl.fromTo(s, {opacity: 0, scale: 0.6}, {opacity: 1, scale: 1, duration: 0.38, ease: EASE}, at); }''',
    'minimal': '''const EASE = "power1.out"; function enter(s, at) { tl.fromTo(s, {opacity: 0}, {opacity: 1, duration: 0.9, ease: EASE}, at); }''',
}

HELPERS_JS = '''
function grow(s, at, until) { tl.fromTo(s, {scaleX: 0}, {scaleX: 1, duration: until ? Math.max(0.3, until - at) : 0.6, ease: "power2.out", transformOrigin: "0% 50%"}, at); }
function dim(s, at) { tl.to(s, {opacity: 0.38, duration: 0.5}, at); }
function countUp(s, at, dur) {
  const el = document.querySelector(s); const to = parseFloat(el.dataset.to); const dec = (el.dataset.to.split(".")[1] || "").length;
  const o = {v: 0}; tl.to(o, {v: to, duration: dur, ease: "power2.out", onUpdate: () => { el.textContent = o.v.toFixed(dec); }}, at);
}
'''

TEMPLATE_CSS = '''
.b-steps { margin-top: 40px; display: flex; flex-direction: column; gap: 22px; }
.b-step { display: flex; align-items: baseline; gap: 22px; font: 600 var(--step)/1.2 var(--font-body); color: var(--text); }
.b-step .n { font: 400 calc(var(--step) * 1.1)/1 var(--font-display); color: var(--accent); min-width: 1.2em; }
.b-compare { margin-top: 38px; display: grid; grid-template-columns: 1fr auto 1fr; gap: 28px; align-items: stretch; }
.vertical .b-compare { grid-template-columns: 1fr; }
.b-compare .col { padding: 34px; border: 2px solid color-mix(in srgb, var(--text) 18%, transparent); border-radius: 18px; background: var(--surface); }
.b-compare .col.win { border-color: var(--accent); }
.b-compare .lab { font: 700 22px/1 var(--font-body); letter-spacing: .22em; text-transform: uppercase; color: var(--muted); }
.b-compare .win .lab { color: var(--accent); }
.b-compare .big { margin-top: 16px; font: 400 calc(var(--h1) * .62)/1.08 var(--font-display); color: var(--text); }
.b-compare .vs { align-self: center; justify-self: center; font: italic 400 40px/1 var(--font-display); color: var(--accent); }
.b-stat { margin-top: 20px; display: flex; align-items: baseline; gap: 10px; font: 400 calc(var(--h1) * 3)/0.9 var(--font-display); color: var(--text); }
.b-stat .unit { font-size: .45em; color: var(--accent); }
.b-stat-label { margin-top: 26px; font: 600 var(--step)/1.3 var(--font-body); color: var(--muted); max-width: 18em; }
.b-quote .mark { font: 400 calc(var(--h1) * 2.2)/0.7 var(--font-display); color: var(--accent); }
.b-quote blockquote { margin-top: 10px; font: italic 400 calc(var(--h1) * .9)/1.12 var(--font-display); color: var(--text); }
.b-quote blockquote em { color: var(--accent); }
.b-quote .by { margin-top: 30px; font: 700 22px/1 var(--font-body); letter-spacing: .26em; color: var(--muted); }
.b-timeline { position: relative; margin-top: 70px; }
.b-timeline .line { position: absolute; left: 0; right: 0; top: 22px; height: 4px; background: var(--accent); }
.b-timeline .pts { position: relative; display: flex; justify-content: space-between; }
.vertical .b-timeline .line { left: 22px; right: auto; top: 0; bottom: 0; width: 4px; height: auto; transform-origin: 50% 0%; }
.vertical .b-timeline .pts { flex-direction: column; gap: 46px; }
.b-timeline .pt { display: flex; flex-direction: column; align-items: center; gap: 18px; text-align: center; max-width: 9em; }
.vertical .b-timeline .pt { flex-direction: row; text-align: left; max-width: none; }
.b-timeline .dot { width: 48px; height: 48px; border-radius: 50%; border: 4px solid var(--accent); background: var(--bg); flex: none; }
.b-timeline .end .dot { background: var(--accent); }
.b-timeline b { font: 600 var(--step)/1.15 var(--font-body); color: var(--text); }
.b-tiers { margin-top: 40px; display: flex; flex-direction: column; align-items: center; gap: 16px; }
.b-tiers .tier { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; padding: 26px 20px; border-radius: 16px; border: 2px solid var(--accent); background: var(--surface); }
.b-tiers .t3 { width: 56%; background: color-mix(in srgb, var(--accent) 22%, var(--surface)); }
.b-tiers .t2 { width: 78%; } .b-tiers .t1 { width: 100%; }
.b-tiers b { font: 400 calc(var(--h1) * .52)/1 var(--font-display); color: var(--text); }
.b-tiers span { font: 600 22px/1 var(--font-body); letter-spacing: .18em; text-transform: uppercase; color: var(--accent); }
'''


def page(name, template, W, H, duration, feel, split=False):
    t = TEMPLATES[template]
    vars_ = {**t['vars'], 'tOut': round(duration - 0.45, 2)}
    vertical = H > W
    layout = 'vertical' if vertical else 'landscape'
    import json
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
      /* template: {template} · feel: {feel} · {"split (face card area left empty)" if split else "full frame"} */
    </style>
  </head>
  <body>
    <div id="root" class="b-root {layout}{' split' if split else ''}" data-composition-id="{name}" data-start="0"
         data-duration="{duration}" data-width="{W}" data-height="{H}"
         data-composition-variables='{json.dumps(vars_)}'>
      <div class="b-grid fill"></div>
      <div id="content">
        <!-- EVERY label must be the speaker's own words from the transcript. Never invent claims or numbers. -->{t['html']}
      </div>
      <div class="b-vignette fill"></div>
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
      {t['js']}
      tl.to("#content", {{ opacity: 0, y: -10, duration: 0.35, ease: "power2.in" }}, V.tOut);
      window.__timelines["{name}"] = tl;
    </script>
  </body>
</html>
'''
