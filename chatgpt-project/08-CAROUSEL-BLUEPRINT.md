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
- The user supplies every image. You never produce images; you write the shot list for them (section 4).

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

Every slide may also carry `theme` (`dark` or `light`; vary them across the set) and `alt` (alt text, plain words).
Mix image slides with drawn slides: images are for emotion, metaphor and real proof; drawn slides are for
mechanisms and numbers. Never put a photo behind a diagram. If an image adds nothing words can't, use type and space.

## 4. Image shots (the user generates or finds these)
For every slide with an `image`, add a `shot` object: `why` (what it shows that words can't), `source` (GENERATE with
ChatGPT, Grok or Gemini / FIND a licensed photo / CAPTURE their own screen or photo), `realism` (materials, light,
setting, what makes it believable, and the AI tells to avoid), `prompt` (paste-ready, ends with "vertical 4:5, no text
in image"), `avoid`. Reserve the top or bottom third of every photo as clean space for the headline. Stills from
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
