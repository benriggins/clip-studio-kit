# Mode F: transcript or write-up → carousel plan (the CAROUSEL_PLAN contract)

Use this when the user wants a **carousel** (Instagram 4:5, a LinkedIn document, 1:1 or 9:16). The source is a
transcript from one of their videos, or a write-up. You decide what the carousel says and in what order. Claude Code
builds every slide from your JSON in the brand's own colours and fonts, and has the final say on layout and looks.

## 1. Rules that never bend
- **Real words only.** Quotes are verbatim from the transcript or write-up. Every number and claim comes from the
  source. A personal result is labelled as theirs ("their own target, not a client result"). Anything that needs a
  check goes in `verify`.
- **5 to 10 slides. Never pad.** One claim per slide, with one reason to believe it.
- **Slide 2 must stand on its own** (people land there from the feed). The last slide is **one action**.
- Don't promote a resource that doesn't exist yet. End on "save this" or "send it" instead.
- You never produce images yourself; you write a GPT Image 2.5 prompt per image slide (section 4). Claude Code generates them, or the user supplies their own.

## 2. Think in gates (answer the first three briefly, before the JSON)
1. **Source.** One reader, one pain, one finished insight. Name where it comes from (take + timecode).
2. **Packaging tournament.** Write 10 cover hooks, one per angle: benefit, mistake, contrast, confession,
   experiment, outcome, number, warning, diagnostic, framework. Keep 3, pick 1, and say in one line why the others
   lost. The cover is 3 to 10 words and promises an answer the slides pay off.
3. **Storyboard.** Pick a flow: **A** correct the mistake (Don't X / Do Y), **B** reframe a belief (contradiction →
   hidden cost → evidence → principle → today), **C** show it working (result first → old way → 2 to 4 steps →
   outcome and its limit → resource). Give each slide a role: attention, recognition, proof, mechanism, example,
   reframe, save, action. Include one slide people will want to screenshot or save.

## 3. The slide recipes (use these names exactly)
`*word*` makes the one emphasis word (italic, accent colour). `\n` is a line break. One emphasis word per slide.

| recipe | fields | use it for |
|---|---|---|
| `cover` | `eyebrow`, `headline`, `sub`, optional `image`, `pos` | the hook. Type only, or a full-bleed photo with the type over it |
| `statement` | `eyebrow`, `headline`, `text` | one claim and its reason |
| `quote` | `quote`, `by`, `source` | a verbatim line worth keeping |
| `list` | `eyebrow`, `title`, `items` (2 to 5) | numbered rows |
| `compare` | `title`, `left {label,text}`, `right {label,text}` | Don't / Do, before / after |
| `steps` | `eyebrow`, `title`, `steps [{t,d}]` (2 to 5) | an ordered process |
| `stat` | `eyebrow`, `pre`, `number`, `unit`, `text`, `note` | one number, labelled honestly |
| `photo` | `kicker`, `headline`, `lede`, `position` top or bottom, `image`, `pos` | a photo carries the slide |
| `paper` | `eyebrow`, `title`, `rows [{k,v}]`, `close`, optional `image` | a worksheet or "save this" card |
| `cta` | `headline`, `action`, `url`, `logo` | the one last action |
| `bigword` | `kicker`, `word`, `line`, `sub`, `image`, `pos`, `timecode` | **CINEMATIC COVER:** a giant serif word (3 to 6 letters is best, e.g. "more.", "hour.") sits BEHIND the subject's head; small heavy line above, serif line below, letterbox bars, REC timecode |
| `slate` | `kicker`, `number`, `line`, `timecode`, `scrub_label`, `image` | a film still: letterbox bars, REC timecode, ONE giant accent word or number, an over-run video scrubber |
| `callout` | `kicker`, `headline`, `sub`, `note`, `at {x,y}`, `image` | a field note: thin leader line from a detail in the photo to a two-line serif note |
| `monument` | `number`, `horizon` (px), `kicker`, `headline`, `lede`, `image` | a huge outlined number standing behind the horizon of a wide photo |
| `scoreboard` | `kicker`, `headline`, `cells [{label,value,sub,on}]`, `note`, `image` | a two-cell HUD over the photo (before/after, work/reward, do/teach) |
| `chat` | `contact`, `status`, `messages [{who them/me, text, time}]`, `typing`, `headline`, `sub`, `image` | **OPENER:** a real-looking text thread (the client waiting, the boss asking), headline under it |
| `notif` | `clock`, `date`, `notes [{app, icon, title, text, ago}]` (3 to 4), `headline`, `image` | **OPENER:** a lock screen piling up with notifications |
| `receipt` | `store`, `meta`, `rows [{k,v}]` (3 to 5), `total {k,v}`, `foot`, `kicker`, `headline`, `image` | **OPENER:** a thermal receipt itemising what the problem costs (time, money, leads) |
| `knockout` | `kicker`, `word`, `line`, `sub`, `image`, `pos` | **OPENER:** one giant word with a vivid photo showing through the letters (sunsets, city light) |
| `split` | `image`, `pos`, `image2`, `pos2`, `label`, `label2`, `headline`, `sub` | **OPENER:** before/after diptych, timestamps on each half, the headline on a strip across the seam |
| `lowerthird` | `bug`, `place`, `timecode`, `headline`, `sub`, `ticker`, `ticker_label`, `image` | **OPENER:** a live-broadcast lower third with a crawling ticker |

Every slide may also carry `theme` (`dark` or `light`; vary them across the set) and `alt` (alt text, plain words).
Mix image slides with drawn slides: images are for emotion, metaphor and real proof; drawn slides are for
mechanisms and numbers. Never put a photo behind a diagram. If an image adds nothing words can't, use type and space.

## 3b. The cinematic standard (a template, never a copy)
- **Never the same carousel twice.** Rotate the opener across posts: `bigword`, `slate`, `chat`, `notif`, `receipt`,
  `knockout`, `split`, `lowerthird`, `cover`. Pick the one that matches the hook (a waiting client → `chat`; a cost →
  `receipt`; overload → `notif`; a before/after → `split`; urgency → `lowerthird`; one word → `bigword` or `knockout`).
  Say which opener you chose and why, and name a second option.
- Give every slide a `motion` style for the video version, and vary them: `push` (slow push-in, calm), `whip` (fast
  whip-pan, FYP pace), `type` (messages pop in one by one, the headline types itself; best on `chat` / `notif`),
  `rack` (rack focus soft → sharp), `cinemagraph` (the photo itself moves: a Grok clip, ~$0.11 a slide; add
  `shot.motion` = what moves and what must not, e.g. "he breathes, the lamp flickers, nothing else moves").
- Open on a strong opener over a real, cinematic photo. Mix image slides (emotion, metaphor, proof) with drawn
  slides (`statement`, `steps`, `paper`) for mechanisms. Cream only ever appears as a `paper` card on a blurred photo.
- One giant word per slide at most; one emphasis word in the accent colour. Page count top right, no brand on top.
- Every carousel also ships as **video slides** (each slide animates for 6 s: photo push-in, the word slides in
  behind the head, type cascades) and as **one 9:16 Reel** for the Reels tab / For You feed. Write copy that works
  for both: every slide readable in under 2.5 seconds.

## 4. Image shots (generated with GPT Image 2.5, or supplied by the user)
For every slide with an `image`, add a `shot` object: `why` (what it shows that words can't), `source` (GENERATE / FIND a licensed photo / CAPTURE their own screen or photo), `realism` (materials, light,
setting, what makes it believable, and the AI tells to avoid), `prompt` (paste-ready for GPT Image 2.5: start "Plan for maximum realism with zero physical defects:", then
materials, light, lens, believable clutter, where the subject sits and which third stays empty for type; end "Portrait
4:5. No text, no logos."), `avoid`. Reserve the top or bottom third of every photo as clean space for the headline. Stills from
the user's own video are fine too: say the take and the time.

## 5. Output
One short paragraph (the gates above), then ONE ```json block:

```json
{
  "title": "working title",
  "series": "short series label shown in every footer",
  "format": "4:5",
  "source": "V1 00:25 to 01:33 (take + timecodes)",
  "verify": ["the one claim the carousel rests on, and where it came from"],
  "caption": "the post caption. Extends the post; doesn't transcribe it. Ends on the one action.",
  "slides": [
    {"recipe": "cover", "headline": "…", "sub": "…", "image": "images/s01.jpg", "pos": "center 40%",
     "alt": "…", "shot": {"why": "…", "source": "CAPTURE", "realism": "…", "prompt": "…", "avoid": "…"}},
    {"recipe": "quote", "quote": "…verbatim…", "by": "the speaker", "source": "V1 00:25", "alt": "…"}
  ]
}
```
Then stop.

For a `bigword` cover, the subject's head must sit in the middle third with clear space above it, so the word can
stand behind the head and the hair overlaps its bottom edge.
