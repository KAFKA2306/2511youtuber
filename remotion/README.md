# Remotion Video Renderer

This directory contains the Remotion.dev project for rendering videos programmatically.

## Setup

```bash
npm install
```

## Development

Start the Remotion Studio:

```bash
npm run dev
```

## Render

Render a video with props:

```bash
npx remotion render src/index.ts NewsVideo output.mp4 --props='{"subtitles": [...], "audioUrl": "path/to/audio.wav"}'
```
