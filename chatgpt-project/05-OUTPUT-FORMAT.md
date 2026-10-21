# Output format: the CLIP_PLAN contract

Claude Code reads this JSON with a program (`tools/plan.py`). It must be **valid JSON** in a single ```json block.
Field names and value formats must be exactly as below.

```json
{
  "project": "my-video",
  "mode": "clips",
  "clips": [
    {
      "id": "reel-busy-not-behind",
      "platform": "instagram",
      "format": "9:16",
      "title": "You're not behind, you're busy",
      "why": "Relatable hook + one clear reframe + very sendable",
      "hooks": [
        "Most owners I talk to think they're behind.",
        "You're not behind. You're busy.",
        "The fix wasn't another tool."
      ],
      "segments": [
        {"take": "V1", "start": "00:30.34", "end": "00:33.98", "role": "HOOK",
         "text": "Most owners I talk to think they're behind."},
        {"take": "V1", "start": "00:36.44", "end": "00:38.10", "role": "TENSION",
         "text": "They're not behind."},
        {"take": "V2", "start": "00:09.14", "end": "00:16.36", "role": "PAYOFF",
         "text": "They're doing ten jobs by hand that a simple checklist and one assistant could take off their plate this week"}
      ],
      "accents": ["not behind", "this week"],
      "explainers": [
        {"after_text": "They're not behind.", "type": "compare", "idea": "Behind versus overloaded",
         "labels": ["Behind", "Doing ten jobs by hand", "One checklist"]}
      ],
      "posting": {
        "instagram_caption": "…",
        "instagram_hashtags": ["#…"],
        "youtube_title": "… #tag #tag",
        "youtube_description": "…",
        "linkedin_post": "…"
      }
    }
  ],
  "take_report": [
    {"point": "Opening story", "take": "V2", "why": "V1 restarted the sentence twice"}
  ],
  "pickups": [
    {"say": "Exact words the creator should re-record", "why": "No take finished this thought cleanly"}
  ]
}
```

## The "cinema" block (add to every clip in modes A to C)
Each clip may carry a `cinema` object: `music` (the vibe), `broll[]` (`on_text`, `seconds`, `focus`, `still`,
`motion`), `ui[]` (kinds and fields from 10-SHOT-AND-MOTION-LIBRARY.md, each with `on_text`, and `out_text` when it
leaves), `sound[]` (`cue`, `on_text`). Every `on_text` / `out_text` must be words from that clip's segments, copied
exactly. See the full example in 10-SHOT-AND-MOTION-LIBRARY.md section F. Claude Code builds all of it and may move
a moment a few words earlier or later to fit the motion.

## Field rules

| Field | Rule |
|---|---|
| `mode` | `clips`, `assemble`, `long-form` or `posting` |
| `id` | lowercase-with-dashes, unique, short (it becomes a folder name) |
| `platform` | `instagram`, `youtube_shorts`, `linkedin`, `youtube`, `tiktok` |
| `format` | `9:16` (Reels, Shorts, TikTok, LinkedIn vertical), `16:9` (YouTube, LinkedIn landscape), `1:1`, `4:5` |
| `take` | `V1`, `V2` … exactly as the transcript headings show them |
| `start`, `end` | `MM:SS.ss` (or `H:MM:SS.ss`) copied from that take's transcript lines. Approximate is fine; exact words are not optional |
| `text` | the speaker's words **exactly** as transcribed, for that span. Claude Code matches these words, then snaps the cut to silence |
| `role` | `HOOK`, `TENSION`, `CONTEXT`, `STAKES`, `PROOF`, `MECHANISM`, `EXAMPLE`, `REVEAL`, `PAYOFF`, `CTA` |
| `accents` | 1–4 short phrases from the clip's words to highlight in the caption accent colour |
| `explainers` | optional; see SOP §6. `after_text` must be words from one of the clip's segments |
| `posting` | include only the platforms the clip is meant for |
| `take_report`, `pickups` | Mode B (and optional in C); omit or leave empty otherwise |

## Common mistakes that get a segment rejected
- Tidying the speaker's grammar or removing a repeated word **inside** the span. Change the span instead.
- Using timecodes from the wrong take.
- Joining two separate lines into one segment when they aren't consecutive in the transcript.
- Trailing commas, comments or smart quotes inside the JSON (use plain `"`).
