# DNH Care — scroll-cinematic site

Canvas frame-scrub site (Lenis smooth scroll) for **DNH Care Homeopathic Centre** (dnhcare.co.in).

- Launch: double-click `Launch Demo.bat` → http://localhost:8347
- Two scrub sections: `#hero` → `frames/hero/`, `#philosophy` → `frames/botanical/` (180 frames each, 1600×900 JPG q88).

## Swapping in real Higgsfield clips
The current frames are **locally rendered placeholders** (`render_frames.py`) because the
Higgsfield workspace had 0 credits at build time. Once the workspace has credits:

1. Generate keyframe (`nano_banana_pro`, 16:9): amber-glass homeopathy bottle on wet stone,
   botanical herbs, emerald background, golden rim light — and a second botanical macro scene.
2. Generate two `seedance_2_0` 1080p 6s clips (start_image = keyframe job id):
   - hero: "smooth seamless full 360-degree rotation, one complete revolution, stays centered"
   - botanical: "herbs and petals assemble outward and float in slow motion, deep parallax"
3. Slice: `ffmpeg -i clip.mp4 -vf "fps=30,scale=1600:-2" -q:v 4 frames/hero/frame_%04d.jpg`
   (target ~180 frames; adjust fps = 180 / clip seconds), same for `frames/botanical/`.
4. Update `frameCount` in the `SCRUB_SECTIONS` config at the bottom of `index.html` if the
   frame count differs. Nothing else changes.
