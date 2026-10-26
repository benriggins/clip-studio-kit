# Prompts for your ChatGPT Project

**How to use one:** open your Clip Studio project in ChatGPT → **new chat** → attach `transcript.txt` → paste the
prompt → send. Copy ChatGPT's **whole** answer and paste it back into Claude Code.

Claude Code normally fills in the `[brackets]` and copies the right prompt to your clipboard for you. You can
also copy one yourself and edit the brackets.

---

## 1. Clips (the default)
```
Mode A: clips. Find the [3] strongest short-form clips in the attached transcript.
Platforms: [Instagram Reels, YouTube Shorts, LinkedIn].
Assign each clip the platform it fits best, with the right format. Build each one as the minimum complete argument (lines may come from anywhere in the transcript). Give 3 hook options per clip and say which you chose. Include explainer ideas and posting copy for each clip's platform.
Return the CLIP_PLAN JSON exactly as 05-OUTPUT-FORMAT.md specifies.
```

## 2. The one best Reel (exact words)
```
Mode A: clips. I want the single best Instagram Reel from the attached transcript: 30 to 60 seconds, 9:16.
Before choosing, run head-to-head tournaments on hooks and payoffs (02-CLIP-SELECTION.md). Open on the strongest truthful line, land on a real resolution, and use the speaker's exact words only.
Give me the runner-up too, as a second clip, and tell me in one line why the winner beat it.
Return the CLIP_PLAN JSON.
```

## 3. Assemble my takes into one video
```
Mode B: assemble takes. The attached transcript has [3] takes of the same video (V1, V2, V3). Build ONE finished video from the best parts.
My notes on the takes:
- V1: [e.g. the opening was great; I stumbled from the part about pricing onwards]
- V2: [e.g. the middle was good; the ending was weak]
- V3: [e.g. only the ending was good]
Format: [16:9 for YouTube / 9:16 for Reels and Shorts].
Follow my notes first. Map the script spine, choose the best delivery of every point, keep the seams on clean sentence boundaries, and cover every point exactly once.
Return the CLIP_PLAN JSON with one clip, plus the take_report and any pickups (exact words for me to re-record).
```

## 4. Full YouTube video (long-form)
```
Mode C: long-form. Plan the full YouTube edit of the attached transcript (16:9).
Cut repetition, tangents and dead air; keep personality and caveats. Build a first 30 seconds from the strongest truthful lines (04-YOUTUBE-LONG-FORM-PLAYBOOK.md), with no generic intro.
Return the CLIP_PLAN JSON for the full cut, then LONG_FORM_NOTES: 3 title + thumbnail pairs (recommend one), chapters, explainer ideas, pickup lines, and 3 to 8 Shorts candidates.
```

## 5. LinkedIn cut
```
Mode A: clips. One LinkedIn video from the attached transcript: a little over 60 seconds (about 62 to 75), 16:9.
LinkedIn rewards a professional takeaway, clear reasoning and a first line that stands alone. It is a cinematic
teaching video: my footage sits in a card on one side (if it was filmed vertically, the whole vertical frame, never
zoomed into my face) and teaching slides, diagrams and motion design build on the rest of the screen as I talk. Plan
an explainer for almost every idea. Write the LinkedIn post with the link for the first comment.
Return the CLIP_PLAN JSON.
```

## 6. Three hooks for a clip
```
For clip "[clip id]" in the plan you already made, give me 3 different opening hooks, each built from the speaker's exact words somewhere in the transcript (a claim, a question, a surprising result). Rank them and say why. Return the updated CLIP_PLAN JSON with your top choice as the HOOK segment.
```

## 7. Posting copy only
```
Mode D: posting copy. For these clips: [paste the clip ids, or "all the clips above"], write the posting block for each one's platform: Instagram caption + 3 to 5 hashtags, YouTube Shorts title (under 70 characters) + description, and the LinkedIn post. Quote the speaker word-for-word wherever you quote. Use my brand profile's call to action and words-to-avoid list.
Return the CLIP_PLAN JSON with the updated posting blocks.
```

## 8. Revise a clip
```
Revise clip "[clip id]": [what to change, e.g. "it's too long, get it under 45 seconds", "the ending doesn't land", "start with the story instead"].
Keep everything else the same. Use the exact transcript words. Return the full corrected CLIP_PLAN JSON.
```

## 9. Claude Code rejected a segment
Claude Code writes this one for you when it happens. It looks like:
```
Claude Code couldn't find these words in the transcript: [segment]. The transcript actually says: "[exact words]" at [take, time]. Fix only that segment with the exact words, and return the full corrected CLIP_PLAN JSON.
```

## 10. LinkedIn write-up → full video (mode E)
Paste the write-up under the prompt instead of attaching a transcript.
```
Mode E: video blueprint. Turn the LinkedIn write-up below into a [60]-second [16:9 LinkedIn] video, following 07-VIDEO-BLUEPRINT.md and my brand profile.
Script for the voiceover from the write-up's own facts. Plan [8 to 12] shots: use image-to-video from my real brand photos for anything showing our work, with a realism plan before every Grok Imagine prompt. Add explainers where they teach, music direction, and the LinkedIn post with the link for the first comment.
Return the VIDEO_BLUEPRINT JSON, then the GROK SHOT LIST.

WRITE-UP:
[paste the write-up here]
```

## 11. Transcript or write-up → carousel (mode F)
Attach `transcript.txt` (or paste a write-up under the prompt).
```
Mode F: carousel plan. Turn [the strongest idea in this video / the write-up below] into a [9]-slide [Instagram 4:5] carousel for [Instagram and a LinkedIn document], following 08-CAROUSEL-BLUEPRINT.md and my brand profile.
Quote me word for word. Run the cover-hook tournament and the storyboard briefly, mark which slides need my images (with a shot list for each), and flag any claim I should check.
Return the CAROUSEL_PLAN JSON.
```

## 11b. LinkedIn document carousel (PDF)
```
Mode F: carousel plan. Turn [the strongest idea in this video / the write-up below] into a [8]-slide LinkedIn
document carousel (PDF, 4:5), following 08-CAROUSEL-BLUEPRINT.md section 3c and my brand profile: simple, clean,
premium, value stated plainly on slide 1, one idea per slide, at most two photos. Quote me word for word and flag any
claim I should check. Write the LinkedIn post to go with it. Return the CAROUSEL_PLAN JSON.
```

---

**Tips**
- One video per chat keeps ChatGPT focused. Use the same project every time, so it always has your files.
- You can mix: "Do prompt 3, then also give me 2 Reels from the finished video."
- Change your mind about your style ("tighter cuts from now on")? Tell Claude Code. It updates your brand profile
  and tells you to re-upload `06-BRAND-PROFILE.md`.


## 12. Cinema reel (the default for footage-led brands)
Attach `transcript.txt`, then paste:
```
Plan the 2 or 3 strongest reels in this video, directed per 09-CINEMA-PLAYBOOK.md. For each clip: the CLIP_PLAN
segments (exact words, tight pace, hook in the first 3 seconds, payoff answers the hook, CTA from the brand
profile), 2 to 4 accents, and a full "cinema" block from 10-SHOT-AND-MOTION-LIBRARY.md: 2 to 4 B-roll shots with
GPT Image 2.5 still prompts (realism plan first) and Grok Imagine motion prompts, the glass UI and big-word moments,
sound cues and the music vibe, every one tied to the exact words it fires on. Something new on screen every 1.5
to 3 seconds. One JSON block, then stop.
```


## 13. Cinematic carousel + video carousel (the default carousel)
Attach `transcript.txt` (or paste a write-up), then paste:
```
Plan an FYP carousel from this, per 08-CAROUSEL-BLUEPRINT.md sections 3a and 3b: pick the framework and the look
that fit this idea (different from our last carousels; say why), 3:4 format, 5 to 10 slides, the opener that fits
this hook best (not the one we used last time; name a second option), slide 2 written as a second hook, a motion
style on every slide, image slides mixed with drawn slides, verbatim quotes only, and a last slide that asks for one
interaction (comment a keyword, share or save; the offer comes from the brand profile). Write the caption too.
Give every image slide a shot with a GPT Image 2.5 prompt (realism plan first, portrait 3:4, no text). Copy must
read in under 2.5 seconds a slide, because it also ships as video slides and a 9:16 Reel. Return the CAROUSEL_PLAN
JSON, then stop.
```
