# Output format: the CLIP_PLAN contract

Claude Code reads this JSON with a program (`tools/plan.py`). It must be **valid JSON** in a single ```json block.
Field names and value formats must be exactly as below.

```json
{
  "project": "my-video",
  "mode": "clips",
  "clips": [
    {
      "id": "reel-good-things",
      "platform": "instagram",
      "format": "9:16",
      "title": "The devil's best tool is good things",
      "why": "Contrarian hook + clean payoff + very sendable",
      "hooks": [
        "The devil's best tool to use on you is this.",
        "Good things.",
        "You have to have a North Star."
      ],
      "segments": [
        {"take": "V1", "start": "00:30.34", "end": "00:33.98", "role": "HOOK",
         "text": "The devil's best tool to use on you is this."},
        {"take": "V1", "start": "00:36.44", "end": "00:38.10", "role": "TENSION",
         "text": "Good things."},
        {"take": "V2", "start": "00:09.14", "end": "00:16.36", "role": "PAYOFF",
         "text": "We call ourselves all these different things and we look in the mirror and we see ourselves in a way that God does not see us"}
      ],
      "accents": ["good things", "North Star"],
      "explainers": [
        {"after_text": "Good things.", "type": "compare", "idea": "Good things versus the right thing",
         "labels": ["Good things", "The right thing", "Points to the North Star"]}
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
