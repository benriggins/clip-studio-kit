# Clip Studio: edit videos with Claude Code + ChatGPT

Turn your raw recordings (one video, or several takes of the same video) into finished **Instagram Reels,
YouTube Shorts, LinkedIn videos and full YouTube edits**. You get clean cuts, captions on every line, framing that
follows your face, and animated explainer slides in your own brand.

All the tools are free, and your videos never leave your computer. ChatGPT only ever sees the transcript text,
and only when you send it.

## Install
1. Open **Claude Code** (the desktop app or the terminal).
2. Paste this and press Enter:

```
Install Clip Studio from https://github.com/benriggins/clip-studio-kit and set me up. Clone it into a folder called "Clip Studio" in my home folder, then follow its CLAUDE.md step by step.
```

Claude Code downloads everything (5–15 minutes, mostly downloads), then:
- **asks about your brand:** who you are, your audience, your colours and fonts;
- **opens your Style Lab:** a gallery of slide templates, animation feels and caption styles, all rendered in
  your brand, so you choose by watching;
- **sets up your ChatGPT Project** with you, step by step (ChatGPT Plus required).

On your first real video, it edits one clip three ways (pace, framing, captions) so you can pick your editing
style from your own footage. Your choices become **your own editing SOP** (`my-studio/MY-STYLE.md`), which
Claude Code follows on every video and updates whenever you change your mind.

## How it works

```
You record ──► Claude Code transcribes (on your computer)
           ──► ChatGPT picks the best moments and the order   (you paste one prompt)
           ──► Claude Code cuts, frames, captions, animates, checks the audio and every cut
           ──► finished videos + captions/titles for each platform, in projects/<video>/…/exports/
```

**Several takes?** Record as many attempts as you like and tell Claude Code which parts went well ("take 1's
opening, take 2's ending"). ChatGPT picks the best delivery of every point, and Claude Code splices them into one
clean video.

## What you need
- **Claude Code** and **ChatGPT Plus**.
- A Mac, Windows PC or Linux machine with about 3 GB free. No GPU needed.

## What's inside
| Folder | What it is |
|---|---|
| `CLAUDE.md` | the operating manual Claude Code follows |
| `PRODUCTION-STANDARDS.md` | the house rules for every brand: footage, voice, music, captions, slides, delivery |
| `chatgpt-project/` | the ChatGPT Project: instructions, 7 reference files, prompts, setup guide |
| `brand/` | the brand interview and templates for your profile and style SOP |
| `tools/` | transcription, cut planning, rendering, captions, explainers, checks, Style Lab |
| `setup/` | installers for Mac, Windows and Linux |
| `my-studio/` | **yours**, created on first run: brand, style SOP, Style Lab (its own private git repo) |
| `projects/` | your videos and exports (never uploaded) |

**Updating:** ask Claude Code to "update Clip Studio". It pulls the latest kit; your `my-studio/` and projects
are untouched.

## Built with
[faster-whisper](https://github.com/SYSTRAN/faster-whisper) (MIT) · [FFmpeg](https://ffmpeg.org) ·
[OpenCV](https://opencv.org) · [HyperFrames](https://github.com/heygen-com/hyperframes) (Apache-2.0) ·
[GSAP](https://gsap.com) · [Google Fonts](https://fonts.google.com) (OFL) · [uv](https://github.com/astral-sh/uv).

MIT licensed. See `LICENSE`.
