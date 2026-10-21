# 10 · Shot, motion and sound library (everything Claude Code can build; use these names in your JSON)

## A. Generated B-roll (photoreal, 9:16, about $0.11 a shot, so use 2 to 4 per reel)
How it's made: **GPT Image 2.5** makes the first frame (it renders exact on-screen text), then **Grok Imagine
Video 1.5** animates it for 5 s at 720p. Claude Code trims 1.5 to 3 s, grades it to match his footage, adds an
eased push-in toward the subject, and cuts it on the word with a whoosh.

You write two prompts per shot:
- `still`: the first frame. **Always start with the realism plan:** "Plan for maximum realism with zero physical
  defects:" then the real materials, wear, light source, lens/depth of field, setting and believable clutter. End
  with "Vertical 9:16." and the text rule: either "No text, no logos." or "The only text in the image is '<exact
  words he said>'." Name what must be blurred ("screen content blurred and unreadable").
- `motion`: only the camera move and the natural motion, plus what must NOT change. Example: "Slow cinematic
  push-in toward the screen, dust drifts in the light; the text stays exactly the same; no new text appears."

Good B-roll subjects: a laptop screen typing his exact search; a desk with a stack of printed quotes; an hourglass or
clock (time); a busy operations floor (teams); a phone buzzing with notifications (leads); hands signing; a CRM-like
screen with blurred data. Shoot it like a film: low angles, window light, dusk, shallow focus, 35 mm look.
Avoid: people looking at camera, readable fake numbers, logos, faces of real people, sci-fi/holograms, robots.

## B. Glass UI (cream frosted cards in 3D, brand colours; transparent, laid over his footage)
| kind | what it is | best for | fields |
|---|---|---|---|
| `cards` | app-style cards (icon + title), optional strike-through | a list he rejects or names | `title`, `icon` (megaphone/play/funnel/plane), `strike`, `layer` front/back, word it lands on |
| `check` | big card: eyebrow, title (one italic word), chips that tick in | a result or process | `eyebrow`, `title`, `chips[]` each with its word |
| `timer` | iOS timer that rolls to a value with a progress ring | a time or duration he says | `label`, the value, the words where it starts/lands |
| `fan` | app cards fanned around his head with live progress bars, then thrown out | tools/brands he names | `labels[]`, the word they appear on, the word they leave on |
| `person` | statement card that lands the point + CTA pill | the payoff line / CTA | `eyebrow`, `title` |
| `bigword` | a giant serif italic word BEHIND his head (top of frame, hair overlaps it) | the punchline word | `word`, the word it fires on; max 2 per reel |
| `sticker` | an AI-generated object (transparent PNG) that pops in with a shadow | a physical thing he names | `still` prompt (transparent background), word |
`layer: back` puts a card behind his head (use for 1 to 2 upper cards; keep text readable around the head).

## C. Captions (automatic; you only choose the key words)
White, 1 to 3 words at a time, appearing as spoken. `accents` = the 2 to 4 words that go big in serif italic.
Pick nouns or verbs that carry the idea ("operations", "an hour", "tool"), never filler.

## D. Sound (Claude Code mixes it; you place the moments)
- `hit` (bass impact): the first frame of the hook and the payoff word.
- `whoosh`: every cut to or from B-roll, every card flying out.
- `pop` / `tap`: each UI card landing, each chip ticking, each key press.
- `ping`: a timer or counter landing. `notification`: the CTA pill. `chime`: the last half second.
- Music: one viral-style instrumental (punchy, modern, no vocals) clearly audible under the voice and ducked a
  little when he speaks. Describe the vibe in `music` (e.g. "confident trap beat with a phonk edge, 128 bpm").

## E. Camera and pace
- His footage: alternating wide and tight framing on every cut; graded filmic; pauses cut.
- B-roll: eased push-in toward the subject (`focus`: where on the frame the push travels to, e.g. "search bar").
- Whole reel ~12% faster than real time. Total 25 to 40 s.

## F. Example (one clip's cinema block)
```json
"cinema": {
  "music": "confident trap beat with a phonk edge, 128 bpm, punchy 808s, catchy pluck hook",
  "broll": [
    {"on_text": "the most value in AI", "seconds": 2.7, "focus": "search bar",
     "still": "Plan for maximum realism with zero physical defects: a real aluminium laptop, no logo, matte keys with faint wear, the screen showing a minimal browser search page with one search bar containing exactly 'most value in AI' and a thin cursor, dark room at night, screen glow lighting the keys, low 30-degree angle, shallow depth of field, 35 mm film look. Vertical 9:16. The only text in the image is 'most value in AI'. No logos.",
     "motion": "Slow cinematic push-in toward the screen, soft glow flicker, dust motes; the text stays exactly the same; no new text appears; no hands."}
  ],
  "ui": [
    {"kind": "cards", "strike": true, "items": [{"title": "Marketing", "icon": "megaphone", "on_text": "marketing", "layer": "back"},
                                               {"title": "Videos", "icon": "play", "on_text": "videos"}]},
    {"kind": "bigword", "word": "operations.", "on_text": "internal operations"},
    {"kind": "timer", "label": "Quote", "value": "1:00:00", "on_text": "takes an hour"},
    {"kind": "fan", "labels": ["ChatGPT", "Claude Code", "Grokbot", "Gemini"], "on_text": "tons of AIs", "out_text": "not about the tool"},
    {"kind": "person", "eyebrow": "It's not about the tool", "title": "The <em>person</em> who implements the tool", "on_text": "the person who implements"}
  ],
  "sound": [{"cue": "hit", "on_text": "The place"}, {"cue": "hit", "on_text": "an hour"}, {"cue": "chime", "on_text": "the tool."}]
}
```
