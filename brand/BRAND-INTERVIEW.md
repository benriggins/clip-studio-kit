# Brand interview and Style Lab (Claude Code runs this; a few questions at a time)

Offer a sensible default for every question so the user can just say "yes". If they have a website, YouTube
channel or Instagram, offer to read it first and propose the answers for them to confirm.

## Part 1: who you are (about 5 minutes)
1. **Name and handle:** the name viewers know you by, and your main handle.
2. **What you teach or talk about:** one sentence.
3. **Who it's for:** describe the one person you most want to reach.
4. **Your promise:** what changes for that person after watching you?
5. **Voice** (saved as `voice.tone`; the ElevenLabs voice is picked later, by ear): three words for how you sound (for example: direct, warm, funny). Anything you never want to sound
   like?
6. **Your offer or call to action:** a free download, a newsletter, a product, a booking link? Its name and URL.
   (It's fine to say "none yet".)
7. **Platforms:** Instagram Reels, YouTube Shorts, YouTube long-form, LinkedIn, TikTok. Which ones, and which
   matters most?
8. **Words and claims to avoid:** anything you never say, or never want implied (results, guarantees, topics).
9. **What you film:** talking to camera, screen recordings, podcasts or interviews, walking and talking? One
   person or several?

## Part 2: the look (colours and fonts)
10. **Colours:** do you have brand colours? If yes, get the hex codes, or read them from their website or logo.
    If not, offer three palettes that suit their voice:
    - **dark premium:** near-black, warm cream text, gold accent;
    - **clean light:** off-white, ink text, one bold colour;
    - **bold:** deep colour background, white text, bright accent.

    Five values are needed: background, surface (cards), text, muted text and accent. Check the contrast.
11. **Fonts:** suggest pairings from Google Fonts that match the voice:
    - **display (headlines):** DM Serif Display, Playfair Display, Fraunces, Archivo Black or Space Grotesk;
    - **body (labels):** Inter, Manrope or DM Sans;
    - **captions (must be a static, heavy font):** Anton, Bebas Neue, Archivo Black or Oswald.

    Write `my-studio/brand.json`, run `tools/fetch_fonts.py`, then continue.

## Part 3: Style Lab, part one (they choose by looking)
Run `tools/stylelab.py looks`. It renders a gallery in **their** colours and fonts and opens it in the browser.
Ask them to pick:
12. **Slide templates:** which explainer layouts they like. Pick any number of steps, compare, stat, quote,
    timeline and tiers. Every video can mix them; these become their defaults.
13. **Animation feel:** one of smooth, punchy or minimal.
14. **Caption style:** one of rise, karaoke or pop. Also ask: UPPERCASE or normal case?

Save these choices to `my-studio/brand.json`: `style.templates`, `style.feel`, `captions.style` and
`captions.uppercase`. If they want changes ("the gold is too bright", "bigger captions"), adjust and re-render
before moving on.

## Part 4: Style Lab, part two (on their first real video, after the first ChatGPT plan)
Run `tools/stylelab.py clip <clip-plan.json> <clip-id>` on the first clip. It renders the same clip three ways
from their footage and opens a comparison page:
- **A:** natural pace · wide/tight framing · rising captions
- **B:** tight pace (pauses cut out) · punch-in on hooks and payoffs · pop captions
- **C:** natural pace · one locked framing · karaoke captions

Then ask:
15. **Pace:** natural (keep the breaths) or tight (cut the pauses)?
16. **Framing:** alternate wide/tight, locked, or punch-in on key lines?
17. **Splice style** (this goes to ChatGPT): **argument** (build the strongest point from lines across the whole
    video; the default), **moment** (the single best continuous stretch, lightly trimmed), or **mixed** (decide per
    clip).
18. Anything else from what they just watched: caption size, music (none by default), graphics density
    (light / medium / heavy).

Save to `my-studio/brand.json` (`style.pace`, `style.crop`, `style.splice`, `style.graphics_density`) and update
`my-studio/MY-STYLE.md`.

## After the interview
1. Write `my-studio/MY-STYLE.md` from `brand/MY-STYLE.template.md`. It is **their** editing SOP, in plain
   language, with every choice and the reason they gave.
2. Write `chatgpt-project/06-BRAND-PROFILE.md` from `brand/BRAND-PROFILE.template.md`, then ask them to upload or
   replace it in their ChatGPT Project.
3. Commit in their studio repo: `git -C my-studio add -A && git -C my-studio commit -m "Brand and style"`.
4. Whenever they change their mind later ("I want bigger captions from now on"), update `brand.json`,
   `MY-STYLE.md` and, if it affects ChatGPT, `06-BRAND-PROFILE.md`. Then commit.
