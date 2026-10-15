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
Mode A: clips. One LinkedIn video from the attached transcript: [60 to 105] seconds, [16:9 / 9:16].
LinkedIn rewards a professional takeaway, clear reasoning and a first line that stands alone. Lean on explainers that teach the idea (the split-screen look). Write the LinkedIn post with the link for the first comment.
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

---

**Tips**
- One video per chat keeps ChatGPT focused. Use the same project every time, so it always has your files.
- You can mix: "Do prompt 3, then also give me 2 Reels from the finished video."
- Change your mind about your style ("tighter cuts from now on")? Tell Claude Code. It updates your brand profile
  and tells you to re-upload `06-BRAND-PROFILE.md`.
