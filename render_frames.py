"""
DNH Care — placeholder cinematic frame renderer.
Renders two 180-frame scroll-scrub sequences (1600x900 JPG q88) that match the
brand (deep emerald, amber glass, botanical gold) until real Higgsfield clips
are generated and sliced with ffmpeg into the same folders.

  frames/hero/frame_0001.jpg .. frame_0180.jpg   (amber bottle slow orbit)
  frames/botanical/frame_0001.jpg .. 0180        (leaves assemble into a wreath)
"""
import math, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

W, H = 1600, 900
N = 180
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")

# ---------------- shared helpers ----------------

def radial_gradient(w, h, cx, cy, inner, outer, power=1.6):
    """inner/outer are (r,g,b). Returns float array h,w,3."""
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((x - cx) / (w * 0.62)) ** 2 + ((y - cy) / (h * 0.62)) ** 2)
    d = np.clip(d, 0, 1) ** power
    inner = np.array(inner, np.float32); outer = np.array(outer, np.float32)
    return inner[None, None, :] * (1 - d[..., None]) + outer[None, None, :] * d[..., None]

def to_img(arr):
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")

def glow_sprite(size, color, hard=0.18):
    """Soft radial glow disc RGBA sprite."""
    s = size
    y, x = np.mgrid[0:s, 0:s].astype(np.float32)
    d = np.sqrt((x - s / 2) ** 2 + (y - s / 2) ** 2) / (s / 2)
    a = np.clip(1 - d, 0, 1) ** 2
    a = np.where(d < hard, 1.0, a)
    rgba = np.zeros((s, s, 4), np.uint8)
    rgba[..., 0] = color[0]; rgba[..., 1] = color[1]; rgba[..., 2] = color[2]
    rgba[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")

def screen_paste(base, sprite, pos, alpha=1.0):
    """Additive-ish paste of an RGBA glow sprite."""
    if alpha <= 0: return
    sp = sprite
    if alpha < 1.0:
        sp = sprite.copy()
        a = sp.getchannel("A").point(lambda v: int(v * alpha))
        sp.putalpha(a)
    base.paste(Image.composite(sp.convert("RGB"), base.crop(
        (pos[0], pos[1], pos[0] + sp.width, pos[1] + sp.height)).convert("RGB"),
        sp.getchannel("A")) if False else sp, pos, sp)

def make_rays(w, h, n_rays=7, seed=3):
    rnd = random.Random(seed)
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    for i in range(n_rays):
        x_top = rnd.uniform(0.25, 0.75) * w
        spread = rnd.uniform(40, 130)
        x_bot = x_top + rnd.uniform(-250, 250)
        d.polygon([(x_top - spread * 0.25, -50), (x_top + spread * 0.25, -50),
                   (x_bot + spread, h * 0.9), (x_bot - spread, h * 0.9)],
                  fill=int(rnd.uniform(26, 54)))
    return img.filter(ImageFilter.GaussianBlur(48))

def make_mist(w, h, seed=7):
    rnd = np.random.default_rng(seed)
    noise = rnd.random((h // 8, w // 8)).astype(np.float32)
    img = Image.fromarray((noise * 255).astype(np.uint8), "L").resize((w, h), Image.BICUBIC)
    return img.filter(ImageFilter.GaussianBlur(36))

def vignette(w, h):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((x - w / 2) / (w * 0.58)) ** 2 + ((y - h * 0.46) / (h * 0.62)) ** 2)
    v = np.clip(1 - 0.72 * np.clip(d - 0.45, 0, 1) ** 1.5, 0, 1)
    return v[..., None]

EMERALD_IN = (16, 56, 41)
EMERALD_OUT = (4, 14, 10)
GOLD = (217, 164, 65)
SAGE = (127, 184, 154)
CREAM = (245, 241, 230)
AMBER = (170, 108, 34)

# ---------------- hero sequence: amber bottle orbit ----------------

def build_bottle(scale=1.0):
    """Pre-render amber glass bottle RGBA sprite (no highlight)."""
    bw, bh = int(360 * scale), int(560 * scale)
    img = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    body_t, body_b = int(bh * 0.30), int(bh * 0.97)
    bx0, bx1 = int(bw * 0.16), int(bw * 0.84)
    # body with vertical amber gradient
    for yy in range(body_t, body_b):
        k = (yy - body_t) / (body_b - body_t)
        r = int(AMBER[0] * (0.55 + 0.55 * k)); g = int(AMBER[1] * (0.50 + 0.50 * k)); b = int(AMBER[2] * (0.55 + 0.45 * k))
        d.line([(bx0, yy), (bx1, yy)], fill=(r, g, b, 235))
    # round shoulders + neck + cork
    d.ellipse([bx0, body_t - int(bh * 0.055), bx1, body_t + int(bh * 0.07)], fill=(150, 96, 30, 235))
    nx0, nx1 = int(bw * 0.40), int(bw * 0.60)
    d.rectangle([nx0, int(bh * 0.12), nx1, body_t], fill=(140, 88, 26, 235))
    d.rounded_rectangle([nx0 - 8, int(bh * 0.02), nx1 + 8, int(bh * 0.13)], radius=10, fill=(96, 70, 48, 255))
    # rounded bottom corners
    mask = Image.new("L", (bw, bh), 0)
    dm = ImageDraw.Draw(mask)
    dm.rounded_rectangle([bx0, body_t - int(bh * 0.05), bx1, body_b], radius=int(bw * 0.13), fill=255)
    dm.rectangle([nx0, int(bh * 0.02), nx1, body_t], fill=255)
    dm.rounded_rectangle([nx0 - 8, int(bh * 0.02), nx1 + 8, int(bh * 0.13)], radius=10, fill=255)
    a = np.array(img.getchannel("A"), np.uint16) * np.array(mask, np.uint16) // 255
    img.putalpha(Image.fromarray(a.astype(np.uint8), "L"))
    # label band
    d = ImageDraw.Draw(img)
    ly0, ly1 = int(bh * 0.46), int(bh * 0.78)
    d.rounded_rectangle([int(bw * 0.225), ly0, int(bw * 0.775), ly1], radius=14,
                        fill=(CREAM[0], CREAM[1], CREAM[2], 246))
    # emblem: leaf cross
    cx, cy = bw // 2, (ly0 + ly1) // 2 - int(bh * 0.03)
    rr = int(bw * 0.085)
    d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(18, 60, 43, 255), width=4)
    lw = int(rr * 0.42)
    d.rectangle([cx - lw // 3, cy - rr + 8, cx + lw // 3, cy + rr - 8], fill=(18, 60, 43, 255))
    d.rectangle([cx - rr + 8, cy - lw // 3, cx + rr - 8, cy + lw // 3], fill=(18, 60, 43, 255))
    # wordmark lines
    d.line([(int(bw * 0.30), ly1 - int(bh * 0.085)), (int(bw * 0.70), ly1 - int(bh * 0.085))], fill=(18, 60, 43, 220), width=6)
    d.line([(int(bw * 0.36), ly1 - int(bh * 0.05)), (int(bw * 0.64), ly1 - int(bh * 0.05))], fill=(18, 60, 43, 150), width=4)
    return img

def render_hero():
    out = os.path.join(OUT, "hero"); os.makedirs(out, exist_ok=True)
    base_grad = to_img(radial_gradient(W + 400, H + 240, (W + 400) / 2, (H + 240) * 0.42, EMERALD_IN, EMERALD_OUT))
    rays = make_rays(W, H)
    mist = make_mist(W * 2, H)
    vig = vignette(W, H)
    bottle = build_bottle(1.0)
    rnd = random.Random(42)
    parts = []
    for i in range(95):
        parts.append({
            "rx": rnd.uniform(260, 760), "rz": rnd.uniform(0.35, 1.0),
            "y": rnd.uniform(H * 0.18, H * 0.85), "ph": rnd.uniform(0, 2 * math.pi),
            "sz": rnd.choice([10, 14, 18, 26, 40, 58]),
            "col": rnd.choice([GOLD, GOLD, SAGE, (220, 200, 150)]),
            "sp": rnd.choice([1, 1, 1, 2]),
        })
    sprites = {}
    for p in parts:
        key = (p["sz"], p["col"])
        if key not in sprites: sprites[key] = glow_sprite(p["sz"] * 4, p["col"])
    bcx = int(W * 0.66)            # bottle center x (right third; copy sits left)
    bx = bcx - bottle.width // 2
    by = int(H * 0.30)
    floor_glow = glow_sprite(900, (60, 130, 95))

    for f in range(N):
        t = f / N
        ang = 2 * math.pi * t
        # drifting background (orbit feel)
        ox = int(200 + 120 * math.cos(ang)); oy = int(120 + 40 * math.sin(ang))
        frame = base_grad.crop((ox, oy, ox + W, oy + H)).copy()
        # rotating god rays
        r = rays.rotate(4 * math.sin(ang), resample=Image.BILINEAR, center=(W * 0.5, -80))
        frame = ImageChops.screen(frame, Image.merge("RGB", (
            r.point(lambda v: int(v * 0.55)), r, r.point(lambda v: int(v * 0.75)))))
        # floor glow
        screen_paste(frame, floor_glow, (bcx - 450, int(H * 0.62)), 0.9)
        d = ImageDraw.Draw(frame, "RGBA")
        d.ellipse([bcx - W * 0.20, H * 0.835, bcx + W * 0.20, H * 0.95], fill=(8, 26, 18, 200))
        d.ellipse([bcx - W * 0.17, H * 0.85, bcx + W * 0.17, H * 0.935], fill=(20, 64, 45, 160))
        # back particles
        bob = math.sin(ang * 2) * 7
        for p in parts:
            a = p["ph"] + ang * p["sp"]
            s, c = math.sin(a), math.cos(a)
            if s >= 0: continue
            x = bcx + c * p["rx"]
            depth = 0.45 + 0.55 * (0.5 - 0.5 * s)
            spr = sprites[(p["sz"], p["col"])]
            sw = max(6, int(spr.width * p["rz"] * 0.7))
            sp2 = spr.resize((sw, sw), Image.BILINEAR)
            frame.paste(sp2, (int(x - sw / 2), int(p["y"] - sw / 2 + bob * p["rz"])), sp2)
        # bottle with sweeping rim highlight
        bimg = bottle.copy()
        hl = Image.new("RGBA", bimg.size, (0, 0, 0, 0))
        dh = ImageDraw.Draw(hl)
        hx = bimg.width * (0.5 + 0.30 * math.cos(ang))
        dh.line([(hx, bimg.height * 0.30), (hx, bimg.height * 0.95)],
                fill=(255, 236, 190, 110), width=26)
        dh.line([(hx * 0.92 + 14, bimg.height * 0.32), (hx * 0.92 + 14, bimg.height * 0.93)],
                fill=(255, 248, 225, 70), width=9)
        hl = hl.filter(ImageFilter.GaussianBlur(7))
        bimg = Image.alpha_composite(bimg, Image.composite(hl, Image.new("RGBA", hl.size, (0,0,0,0)), bimg.getchannel("A")))
        frame.paste(bimg, (bx, int(by + bob)), bimg)
        # front particles
        for p in parts:
            a = p["ph"] + ang * p["sp"]
            s, c = math.sin(a), math.cos(a)
            if s < 0: continue
            x = bcx + c * p["rx"]
            spr = sprites[(p["sz"], p["col"])]
            sw = max(8, int(spr.width * p["rz"]))
            sp2 = spr.resize((sw, sw), Image.BILINEAR)
            frame.paste(sp2, (int(x - sw / 2), int(p["y"] - sw / 2 + bob * p["rz"] * 1.4)), sp2)
        # mist (two drifting layers)
        mx = int((t * 320) % W)
        m = ImageChops.offset(mist.crop((0, 0, W, H)), -mx, 0)
        tint = Image.merge("RGB", (m.point(lambda v: v * 30 // 255), m.point(lambda v: v * 64 // 255), m.point(lambda v: v * 48 // 255)))
        frame = ImageChops.screen(frame, tint)
        # vignette
        arr = np.asarray(frame, np.float32) * vig
        to_img(arr).save(os.path.join(out, f"frame_{f+1:04d}.jpg"), quality=88)
        if f % 30 == 0: print("hero", f)

# ---------------- botanical sequence: wreath assembly ----------------

def leaf_sprite(length, width, color, blur=0):
    img = Image.new("RGBA", (length, length), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = length // 2
    d.ellipse([cx - width // 2, 6, cx + width // 2, length - 6], fill=color + (255,))
    d.line([(cx, 14), (cx, length - 14)], fill=(min(color[0]+40,255), min(color[1]+40,255), min(color[2]+30,255), 200), width=3)
    for k in range(3, length - 20, 14):
        d.line([(cx, k + 10), (cx - width // 3, k + 22)], fill=(0, 0, 0, 60), width=2)
        d.line([(cx, k + 10), (cx + width // 3, k + 22)], fill=(0, 0, 0, 60), width=2)
    if blur: img = img.filter(ImageFilter.GaussianBlur(blur))
    return img

def ease(p): return p * p * (3 - 2 * p)

def render_botanical():
    out = os.path.join(OUT, "botanical"); os.makedirs(out, exist_ok=True)
    base_grad = to_img(radial_gradient(W + 400, H + 240, (W + 400) / 2, (H + 240) * 0.5, (10, 46, 38), (3, 12, 9)))
    rays = make_rays(W, H, n_rays=5, seed=11)
    mist = make_mist(W * 2, H, seed=13)
    vig = vignette(W, H)
    rnd = random.Random(99)
    cx, cy, R = W / 2, H * 0.46, 235
    leaves = []
    cols = [(70, 130, 95), (96, 150, 104), (124, 170, 118), (170, 150, 80)]
    for i in range(30):
        a = 2 * math.pi * i / 30
        leaves.append({
            "sx": rnd.uniform(-0.15, 1.15) * W, "sy": rnd.uniform(-0.2, 1.2) * H,
            "sr": rnd.uniform(0, 360),
            "tx": cx + R * math.cos(a), "ty": cy + R * math.sin(a),
            "tr": -math.degrees(a) - 90,
            "spr": leaf_sprite(rnd.choice([90, 110, 130]), rnd.choice([26, 34]), rnd.choice(cols),
                               blur=rnd.choice([0, 0, 1])),
            "dly": rnd.uniform(0, 0.25),
        })
    sparks = [{"x": rnd.uniform(0, W), "y": rnd.uniform(0, H), "v": rnd.uniform(20, 90),
               "sz": rnd.choice([8, 12, 18, 28]), "ph": rnd.uniform(0, 6.28)} for _ in range(70)]
    spark_spr = {s: glow_sprite(s * 4, GOLD) for s in [8, 12, 18, 28]}
    ring = glow_sprite(620, (220, 190, 120), hard=0.0)
    emblem_glow = glow_sprite(330, (235, 215, 160), hard=0.05)

    for f in range(N):
        p = f / (N - 1)
        frame = base_grad.crop((200, 120, 200 + W, 120 + H)).copy()
        r = rays.rotate(2.5 * math.sin(2 * math.pi * p), resample=Image.BILINEAR, center=(W * 0.5, -80))
        frame = ImageChops.screen(frame, Image.merge("RGB", (
            r.point(lambda v: int(v * 0.5)), r, r.point(lambda v: int(v * 0.7)))))
        # rising sparks
        for s in sparks:
            yy = (s["y"] - p * s["v"] * 6) % H
            xx = s["x"] + 18 * math.sin(s["ph"] + p * 6)
            spr = spark_spr[s["sz"]]
            frame.paste(spr, (int(xx - spr.width / 2), int(yy - spr.height / 2)), spr)
        # halo grows as wreath assembles
        halo_a = max(0.0, (p - 0.55) / 0.45)
        if halo_a > 0:
            hw = int(620 * (0.8 + 0.25 * halo_a))
            hs = ring.resize((hw, hw), Image.BILINEAR)
            aimg = hs.getchannel("A").point(lambda v: int(v * 0.5 * halo_a))
            hs.putalpha(aimg)
            frame.paste(hs, (int(cx - hw / 2), int(cy - hw / 2)), hs)
            ew = int(330 * halo_a)
            if ew > 10:
                es = emblem_glow.resize((ew, ew), Image.BILINEAR)
                frame.paste(es, (int(cx - ew / 2), int(cy - ew / 2)), es)
                d = ImageDraw.Draw(frame, "RGBA")
                rr = int(58 * halo_a); lw2 = int(rr * 0.42)
                col = (18, 60, 43, int(255 * halo_a))
                if rr > 14:
                    d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=col, width=5)
                    d.rectangle([cx - lw2 // 3, cy - rr + 10, cx + lw2 // 3, cy + rr - 10], fill=col)
                    d.rectangle([cx - rr + 10, cy - lw2 // 3, cx + rr - 10, cy + lw2 // 3], fill=col)
        # leaves fly in
        for lf in leaves:
            lp = ease(min(1.0, max(0.0, (p - lf["dly"]) / (0.9 - lf["dly"]))))
            x = lf["sx"] + (lf["tx"] - lf["sx"]) * lp
            y = lf["sy"] + (lf["ty"] - lf["sy"]) * lp
            rot = lf["sr"] + (lf["tr"] - lf["sr"]) * lp + (1 - lp) * 160 * math.sin(p * 9 + lf["sr"])
            spr = lf["spr"].rotate(rot, resample=Image.BILINEAR, expand=True)
            frame.paste(spr, (int(x - spr.width / 2), int(y - spr.height / 2)), spr)
        # mist
        mx = int((p * 420) % W)
        m = ImageChops.offset(mist.crop((0, 0, W, H)), mx, 0)
        tint = Image.merge("RGB", (m.point(lambda v: v * 26 // 255), m.point(lambda v: v * 58 // 255), m.point(lambda v: v * 46 // 255)))
        frame = ImageChops.screen(frame, tint)
        arr = np.asarray(frame, np.float32) * vig
        to_img(arr).save(os.path.join(out, f"frame_{f+1:04d}.jpg"), quality=88)
        if f % 30 == 0: print("botanical", f)

if __name__ == "__main__":
    import sys
    os.makedirs(OUT, exist_ok=True)
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "hero"): render_hero()
    if which in ("all", "botanical"): render_botanical()
    print("done")
