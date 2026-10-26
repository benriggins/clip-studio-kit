# Production standards (every brand, every video)

These are the house rules for anything Clip Studio makes: produced videos, montages, clips and explainers. They
came from real feedback on real videos, so treat them as defaults for every new company. A brand's own
`my-studio/MY-STYLE.md` can override any of them. Claude Code reads this file before every edit and has the final
say on how each rule is applied.

## 1. Footage and images
- **Design first, generate when it earns it (2026-10-26).** Use as much code-built design, motion and animation as
  possible: it is free and on brand. Generated images and video are welcome, but only where they add something
  design can't (a real-world scene, emotion, a metaphor). Never generate just to fill space; reuse the media library
  before paying for a new one.
- **Vertical footage in a landscape video is never zoomed in to the face.** Put the whole vertical frame in a card
  (`render.py` plan `frame`) and fill the rest of the 16:9 screen with teaching slides and motion.
- **Never reuse footage the viewer has already seen.** Use each clip once. With few clips, hold each one longer.
  For a fast back-and-forth montage, ask the user for 10 or more clips rather than looping the same ones. If an
  ending wants to "come back" to an earlier shot, use a still photo of the same place under the end card, not the
  same clip again.
- **Watch every clip before using it** (contact sheet, `frames.py`). Reject warped buildings, melting fixtures,
  invented text or signage, extra fingers, and faces that drift. Ask for a re-roll with a corrected prompt.
- **Generated people never wear the brand's logo or uniform** unless the image came from the brand itself. Never
  imply generated people are the real team or real customers.
- **Don't slow AI clips with frame interpolation**: it warps them. Play them at normal speed and add the motion
  with a camera move (push, drift, hero) instead.
- **Be honest about images.** Never let a photo look like a specific project, sale or customer it isn't. When the
  right photo is missing, use the closest real brand photo as general context and put the specific fact on a
  stat card rather than on a misleading picture.
- **Real brand photos over flat colour.** Slides sit on the brand's own project photos, shaded dark, with a slow
  push-in. Keep a list of approved photos in `brand.json style.backdrop.photos` and use their real names in the
  ChatGPT brand profile, so blueprints can ask for them.
- **The logo is always the real file** (SVG or PNG from the brand), never generated or retyped.

## 2. Voice
- Produced videos always have a voiceover. Music alone isn't a video.
- Every brand gets **one saved voice** (ElevenLabs, auditioned once, then kept in `brand.json voice`). Choose it
  from a short brief (gender, energy, register) and a few labelled samples the user listens to.
- **Pronunciation is checked on every video.** Transcribe every voice line back with Whisper and compare. Fix
  anything wrong with `voice.say` aliases; captions still show the real spelling. Things that commonly break:
  - the brand name (ask the user how it's said, on day one);
  - bill and law numbers ("AB 1033" → `A.B.` + `ten-thirty-three`);
  - numbers joined to units ("1,200-square-foot" → `twelve-hundred-square-foot`);
  - initialisms, street names and city names with accents.
- Natural pace wins over the target length. A 65-second plan that needs 75 seconds to sound human runs 75 seconds.

## 3. Music and sound
- **No stock whooshes, hits or risers**, and no sound on slide entrances. They sound cheap. Keep `sfx` empty and
  graphics `sfx: false` unless the user asks for one.
- Generate a **fresh music bed per video** from the brand's palette (`brand.json music.palette`), and give the
  user one alternate bed with every delivery.
- **Never:** corporate elevator music, dramatic trailer swells, EDM drops, vocals, stock ukulele. A warm
  cinematic piano bed reads as generic too; prefer modern pulse, elegant minimal, warm groove or modern chill
  unless the brand chose otherwise.
- Music is ducked under the voice. The master lands at −14 LUFS, true peak ≤ −1 dBTP.

- **We do the audio for Reels, always (2026-10-22).** Every Reel ships with its music already in the file.
- **Instagram carousels are the exception (2026-10-24):** they post as still images with no audio, because a video
  slide blocks adding music in the app; the user adds the music in Instagram when posting.

## 4. Scripts
- Every fact, number and name comes from the user's own source (the transcript or the write-up). Never add one.
- **Flag the claim the whole video rests on** (usually the hook's number or sale) and ask the user to check it
  against a primary source before posting. Don't silently cut it.
- About 2.6 spoken words per second. One idea per shot, short spoken sentences, no "in today's video".
- Hook → tension → mechanism/proof → payoff → one call to action, said once, naturally.

## 5. Captions
- `pop` (word by word, active word in a box) for Reels, Shorts and TikTok; `rise` (words brighten as spoken) for
  LinkedIn and YouTube.
- A **static** heavy font (an ExtraBold cut, not a variable file), wrapped by measured pixel width, never by
  character count.
- A soft dark halo behind the text so it reads over bright footage. Check it on the brightest frame.
- Captions stay above the platform's bottom UI band and clear of slide text.

## 6. Slides (explainers)
- **Slides must move.** Every label builds on the word that says it; nothing sits there static.
- **Split layout for footage-heavy videos:** live footage in a rounded card on the left, the slide on the right.
  The card shows the whole shot, cropped only to the card's shape, never punched in so far that it hides what
  the shot is.
- **One idea per slide, and no repeats.** If a blueprint asks for the same comparison twice, merge them, or
  change the second one so it adds something.
- **Readable at phone size.** Big labels; cards stack vertically in the split layout instead of squeezing side
  by side. Use non-breaking hyphens and spaces (`&#8209;`, `&nbsp;`) so "1-Bedroom" or "749 sq ft" never wraps
  mid-term.
- **When two options are both valid, don't dim one.** Dimming says "wrong way". Use "or", not "vs", and mark the
  conditional option honestly ("where eligible").
- **The end card:** the real logo, the call to action as the headline, and the URL in a readable size (≥ 32 px
  on 1080p).
- About one slide per 10–15 seconds on LinkedIn; never two back to back without footage between them, unless
  they make one continuous idea.
- Look at the frames of every rendered slide before placing it.

## 7. Editing
- Mostly hard cuts. Fade into and out of slides and photos; whips and flashes only on a real energy change.
- Grade every clip with the brand grade so AI clips and real photos match. Keep the grain light (heavy grain
  bloats the file).
- Sync slide beats to the voice's own word timestamps, not to estimates.

## 7b. Audio (every brand, standing rule 2026-10-21)
- **Every take is cleaned before anything else.** Noise and background sound are removed on ingest
  (`transcribe.py` → `cleantake.py`), so the user never has to ask. Phone audio is typically −23 to −26 LUFS with a
  −45 dB noise floor and a haze under every word; the clean take lands at about −16 LUFS with the floor near −67 dB.
- Cut, caption and render from the clean take only. Raw camera audio is never used.
- Phrase-level dips (the speaker turning or leaning back) are a separate fix; measure with `ebur128=S`, not per word.

## 8. Delivery
- QC every export: loudness, true peak, black frames, contact sheet, one frame per shot.
- Deliver the finished MP4, the alternate music bed, and the posting copy (post plus first comment) together, with
  a short note on what Claude Code changed from the plan and why, plus anything the user must check before
  posting.
- Files bigger than about 30 MB can't be previewed on a phone, so say so.

## 8b. Carousels (every brand)
- Real words only, verbatim quotes, every number traceable. Personal results are labelled as the speaker's own.
- The user supplies every image; Claude Code writes the shot list and does everything else. Images are for emotion,
  metaphor and real proof; drawn slides are for mechanisms and numbers. Never a photo behind a diagram.
- 5 to 10 slides, never padded. Slide 2 stands alone. Last slide is one action. Mix dark and light slides.
- Masthead is the page count only (no name on top). Alt text on every slide. No emojis on art. Don't promote a
  resource that doesn't exist yet.
- Faces sit centred in their frame; use a frame where the speaker looks at the camera, never mid-blink.

## 9. When the user gives new feedback
Decide whether it's about **this brand** (put it in `my-studio/MY-STYLE.md` and `brand.json`) or about **taste
in general** (put it here, in the kit, so every future company gets it). Most "I hate X" feedback is general.
