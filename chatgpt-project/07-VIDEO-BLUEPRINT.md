# Mode E: write-up → video blueprint (the VIDEO_BLUEPRINT contract)

Use this when the user gives you a **LinkedIn write-up** (or any article) instead of a transcript. You turn it into
a complete short video plan: the voiceover script, a shot list with Grok Imagine prompts, on-screen explainers,
sound and music direction, captions, and posting copy. Claude Code then voices it (the brand's ElevenLabs voice),
generates music and sound, cuts the shots, animates the graphics and finishes it. **Claude Code has the final say
on every visual and technical choice.** Your job is the story, the words and the shot ideas.

## 1. The script (voiceover)
- Every claim, number and name must come from the write-up. Don't invent statistics, results, prices,
  timelines or testimonials. Rephrase for the ear, but keep the facts the writer stated.
- About **2.6 words per second**. LinkedIn: 45–90 s total (120–230 words). Reels/Shorts: 25–45 s.
- Structure: **HOOK** (the first 2 seconds must stand alone; a claim, a question or a surprising truth) →
  **TENSION/STAKES** → **MECHANISM/PROOF** (the write-up's real substance) → **PAYOFF** → **CTA** (the brand
  profile's call to action, said once, naturally).
- One idea per shot. Short sentences. Spoken rhythm, not written rhythm. No "In today's video".

## 2. Shots
- 3–6 seconds each. Each shot's `vo` is the line spoken over it (or "" for a music-only beat).
- Visual sources:
  - `"source": "grok"`: a shot the user generates in **Grok Imagine** as video. For anything showing the
    brand's real work (an ADU, a kitchen, a finish package), use **image-to-video**: name the real brand photo to
    upload in `photo`, and write motion that only moves the camera and the light, so the real build stays exactly
    as built.
  - `"source": "photo"`: a still brand photo; Claude Code animates it (push-in or drift). Use it when no motion is
    needed.
- Every Grok shot has a `realism_plan` first (what makes it look like a real photographed property: correct
  materials, real proportions, true scale, plausible daylight, no impossible geometry, no warped fixtures). Then
  the `grok_prompt` is written from that plan.
- `grok_prompt` rules:
  - Format the same as the video (16:9 or 9:16), 6–10 s.
  - Describe the camera move (slow dolly in, gentle orbit, crane up), lens feel (24 mm wide, 35 mm natural),
    light (golden hour, soft overcast) and one subtle living detail (leaves moving, curtains, steam).
  - No on-screen text, logos or watermarks. Don't add or remove buildings, rooms or fixtures. No morphing.
  - People: only when the write-up is about people. Never put brand logos or uniforms on generated people, and
    never imply generated people are the real team.
- `camera` (how Claude Code moves the frame on top): `push`, `pull`, `punch`, `drift`, `hero`, `none`.
- `speed`: `normal`, `slow`, `slow-mo`, `fast`. `transition_in`: `cut`, `fade`, `dip`, `flash`, `whip`,
  `whip-right`, `zoom`, `slide`, `blur`. Use whips and flashes sparingly, on energy changes.
- `sfx`: optional `["whoosh"]` on a whip, `["hit"]` on a reveal, `["riser"]` before a payoff.

## 3. On-screen explainers
Add one where it shows what the words alone can't (a process, stages, sizes or levels, a number, a contrast).
Templates: `steps` (process), `timeline` (stages), `tiers` (levels or sizes, shown as a staircase), `stat` (one
number the write-up states), `compare` (before/after), `quote` (one line worth a screenshot).
Give `labels` as short phrases from the script. About 1 per 15–20 seconds.

## 4. Sound
- `music.prompt`: one line describing the bed (mood, instruments, tempo in bpm, "no vocals"). Claude Code
  generates it and ducks it under the voice.
- Captions: `pop` for Reels, Shorts and TikTok; `rise` for LinkedIn (or leave it out to use the brand default).

## 5. Output: ONE ```json block, valid JSON

```json
{
  "mode": "blueprint",
  "project": "imkat-linkedin",
  "id": "adu-permits-explained",
  "title": "Why ADU permits feel slow (and how one team fixes it)",
  "platform": "linkedin",
  "format": "16:9",
  "target_seconds": 60,
  "captions": "rise",
  "grade": "imkat-warm",
  "music": {"prompt": "warm modern corporate instrumental, soft piano, light pulsing synth, clean drums, 108 bpm, no vocals"},
  "accents": ["one team", "free ADU cost estimate"],
  "shots": [
    {
      "id": "S01",
      "role": "HOOK",
      "vo": "Most homeowners think the hard part of an ADU is construction.",
      "visual": {
        "source": "grok",
        "photo": "ext-ascolano (the stucco ADU with the red door)",
        "realism_plan": "Keep the real Ascolano ADU exactly as built: stucco, red door, concrete path, the oak trunks. Late-afternoon sun from the left, believable shadows, no new objects.",
        "grok_prompt": "Image to video, 16:9, 8 seconds. Slow cinematic dolly toward the front door of the backyard ADU, 35 mm lens, warm late-afternoon sunlight, leaves moving gently in the oak trees, soft natural shadows, photorealistic real-estate cinematography, no text, no people."
      },
      "camera": "push",
      "speed": "normal",
      "transition_in": "cut",
      "sfx": []
    },
    {
      "id": "S02",
      "role": "MECHANISM",
      "vo": "We handle the plans, the engineering and the permits, then build it.",
      "visual": {"source": "photo", "photo": "pkg1-modern-white"},
      "camera": "drift",
      "speed": "normal",
      "transition_in": "whip",
      "sfx": ["whoosh"],
      "on_screen": {"template": "steps", "idea": "one team, three stages", "labels": ["Plans", "Engineering & permits", "Construction"]}
    }
  ],
  "posting": {
    "linkedin_post": "…",
    "first_comment": "Free ADU cost estimate: https://…"
  }
}
```

| Field | Rule |
|---|---|
| `id` | lowercase-with-dashes, unique, short (it becomes a folder name) |
| `format` | `16:9` for LinkedIn landscape, `9:16` for Reels, Shorts and LinkedIn vertical, `1:1`, `4:5` |
| `shots[].id` | `S01`, `S02` … in order; the user saves each Grok clip under this name |
| `shots[].photo` | one of the brand photo names in the brand profile, plus a few words saying which it is |
| `seconds` | optional; Claude Code times each shot to its voiceover anyway |

After the JSON, add **GROK SHOT LIST**: for each `grok` shot, its id, the photo to upload and the prompt, ready to
paste one by one.
