# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════╗
║       ALL APP IN ONE  🚀             ║
║  TikTok Downloader  |  Variant Gen   ║
║  Image Optimizer    |  → WebP        ║
║  Video Upscaler     |  Creative Lab  ║
╚══════════════════════════════════════╝
"""

import streamlit as st
import subprocess, os, datetime, tempfile, json, re, time
import zipfile, traceback, struct, math
from io import BytesIO
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
from auth import is_authenticated, show_activation_gate

# ─────────────────────────────────────────────────────────────
# Tool binary resolver
# ─────────────────────────────────────────────────────────────
def _find_bin(name):
    candidates = [
        f"/opt/homebrew/bin/{name}",
        f"/usr/local/bin/{name}",
        f"/usr/bin/{name}",
        name,
    ]
    flag = "-version" if name in ("ffmpeg", "ffprobe") else "--version"
    for p in candidates:
        try:
            r = subprocess.run([p, flag], capture_output=True, timeout=5)
            if r.returncode == 0:
                return p
        except Exception:
            continue
    return name

YTDLP   = _find_bin("yt-dlp")
FFMPEG  = _find_bin("ffmpeg")
FFPROBE = _find_bin("ffprobe")

# ─────────────────────────────────────────────────────────────
# Page config & global CSS
# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="ALL APP IN ONE", page_icon="🚀", layout="wide")

# ── Activation gate — blocks everything below if not authenticated ──
if not is_authenticated():
    show_activation_gate()
    st.stop()

st.markdown("""
<style>
  .stTabs [data-baseweb="tab-list"]  { gap: 6px; }
  .stTabs [data-baseweb="tab"] {
      height: 52px; padding: 0 20px;
      background-color: #1a1a1a;
      border-radius: 10px 10px 0 0;
      color: white; font-weight: 700; font-size: 15px;
  }
  .stTabs [aria-selected="true"] { background-color: #ee0a78 !important; }
  div[data-testid="metric-container"] {
      background:#1a1a1a; border-radius:10px;
      padding:12px 18px; border-left:4px solid #ee0a78;
  }
  .tool-card {
      background:#1a1a1a; border-radius:14px; padding:22px;
      border:1px solid #2a2a2a; margin-bottom:10px;
      transition: border-color 0.2s;
  }
  .tool-card:hover { border-color:#ee0a78; }
  .badge {
      display:inline-block; background:#ee0a78; color:white;
      border-radius:20px; padding:3px 12px; font-size:12px; font-weight:700;
  }
  .size-pill {
      display:inline-block; border-radius:8px; padding:2px 8px; font-size:11px;
      margin:2px;
  }
  .pill-green  { background:#004d1a; color:#00ff6a; }
  .pill-orange { background:#4d2500; color:#ff9900; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<h1 style='text-align:center; font-size:2.6rem; margin-bottom:4px'>
  🚀 ALL APP IN ONE
</h1>
<p style='text-align:center; color:#888; margin-bottom:24px'>
  TikTok tools · Image optimizer · WebP converter · Video upscaler
</p>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────
tabs = st.tabs([
    "🏠 Home",
    "📥 TikTok Downloader",
    "🎛️ Variant Generator",
    "🖼️ Image Optimizer",
    "🔄 → WebP",
    "🎬 Video Upscaler",
])
tab_home, tab_dl, tab_vg, tab_img, tab_webp, tab_upscale = tabs


# ══════════════════════════════════════════════════════════════
# HOME TAB
# ══════════════════════════════════════════════════════════════
with tab_home:
    st.markdown("## Welcome to All App In One")
    st.markdown("Pick a tool from the tabs above. Here's what each one does:")

    def card(icon, title, desc, badge=""):
        st.markdown(f"""
        <div class="tool-card">
          <h3>{icon} {title}
            {"<span class='badge'>" + badge + "</span>" if badge else ""}
          </h3>
          <p style="color:#aaa;margin:0">{desc}</p>
        </div>""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        card("📥","TikTok Downloader",
             "Extract & download TikTok videos from any profile or hashtag URL. Grid and List view, ZIP export.")
        card("🖼️","Image Optimizer",
             "Upscale images 1.5×–4× using LANCZOS resampling + smart sharpening. Keep quality, increase resolution.", "NEW")
        card("🎬","Video Upscaler",
             "Upscale videos to 720p / 1080p / 4K with ffmpeg LANCZOS + optional sharpen + denoise.", "NEW")
    with col2:
        card("🎛️","Variant Generator",
             "Generate up to 5 TikTok video variants (120fps · 4000kbps · 1080×1920) with hooks, zoom, pitch.")
        card("🔄","→ WebP Converter",
             "Convert PNG, JPG, BMP, TIFF, GIF → WebP. Batch processing, quality control, lossless mode.", "NEW")

    st.markdown("---")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Tools available","6")
    c2.metric("Video formats","MP4 · MOV · M4V")
    c3.metric("Image formats","PNG · JPG · WebP · BMP · TIFF")
    c4.metric("Max quality","120fps · 4K")


# ══════════════════════════════════════════════════════════════
# HELPERS shared across video tabs
# ══════════════════════════════════════════════════════════════
def format_number(num):
    try:
        num = int(num)
        if num >= 1_000_000: return f"{num/1_000_000:.1f}M"
        if num >= 1_000:     return f"{num/1_000:.1f}K"
        return str(num)
    except Exception:
        return str(num) if num else "N/A"

def check_ytdlp():
    try:
        return subprocess.run([YTDLP,"--version"],capture_output=True,timeout=5).returncode == 0
    except Exception:
        return False

def extract_with_ytdlp(url):
    cmd = [YTDLP,"--dump-json","--flat-playlist","--no-warnings",
           "--no-check-certificate","--extractor-retries","3","--playlist-end","9999",url]
    result = subprocess.run(cmd,capture_output=True,text=True,timeout=300)
    videos = []
    for line in result.stdout.strip().split("\n"):
        if not line: continue
        try:
            info = json.loads(line)
            vid_id = info.get("id","")
            if not vid_id: continue
            videos.append({
                "id":        vid_id,
                "title":     info.get("title","TikTok Video"),
                "thumbnail": info.get("thumbnail",""),
                "views":     format_number(info.get("view_count",0)),
                "likes":     format_number(info.get("like_count",0)),
                "duration":  info.get("duration",0),
                "url":       info.get("webpage_url") or info.get("url",""),
            })
        except json.JSONDecodeError:
            continue
    return videos

TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)")

def parse_progress(line):
    try:
        m = TIME_RE.search(line or "")
        if not m: return None
        h,m_,s = m.groups()
        return int(h)*3600 + int(m_)*60 + float(s)
    except Exception:
        return None

def ffprobe_streams(path):
    try:
        p = subprocess.run([FFPROBE,"-v","error","-select_streams","v:0",
                            "-show_entries","stream=width,height,r_frame_rate,avg_frame_rate",
                            "-of","json",path],capture_output=True,text=True,timeout=30)
        return json.loads(p.stdout).get("streams",[{}])[0]
    except Exception:
        return {}

def get_video_meta(path):
    try:
        s = ffprobe_streams(path)
        def fps(r):
            try:
                n,d = r.split("/"); return float(n)/float(d)
            except Exception: return None
        return s.get("width"),s.get("height"),fps(s.get("avg_frame_rate") or s.get("r_frame_rate",""))
    except Exception:
        return None,None,None

def get_duration(path):
    try:
        p = subprocess.run([FFPROBE,"-v","error","-show_entries","format=duration",
                            "-of","json",path],capture_output=True,text=True,timeout=30)
        return float(json.loads(p.stdout).get("format",{}).get("duration",0))
    except Exception:
        return 0

def run_ffmpeg_progress(cmd, total_secs, prog_cb=None, log_cb=None):
    try:
        proc = subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,
                                text=True,bufsize=1,errors="replace")
        start = time.time()
        last_prog = start
        for line in proc.stderr:
            if log_cb: log_cb(line.rstrip("\n"))
            t = parse_progress(line)
            if t is not None and total_secs and prog_cb:
                prog_cb(max(0,min(100,int(t/total_secs*100))))
                last_prog = time.time()
            if time.time()-last_prog > 120:
                proc.terminate(); return -2
            if time.time()-start > 600:
                proc.terminate(); return -3
        rc = proc.wait()
        if prog_cb: prog_cb(100 if rc==0 else 0)
        return rc
    except Exception as e:
        st.error(f"FFmpeg error: {e}"); return -1

SAFE_THREADS = ["-threads","2"]
TARGET_W, TARGET_H = 1080, 1920


# ══════════════════════════════════════════════════════════════
# TAB 2 — TIKTOK DOWNLOADER  (Grid + List view)
# ══════════════════════════════════════════════════════════════
with tab_dl:
    st.header("📥 TikTok Video Extractor & Downloader")
    st.markdown("Paste any TikTok profile or hashtag URL. Choose **Grid** or **List** view.")

    if "dl_videos"   not in st.session_state: st.session_state.dl_videos   = []
    if "dl_selected" not in st.session_state: st.session_state.dl_selected = set()
    if "dl_view"     not in st.session_state: st.session_state.dl_view     = "Grid"

    # ── Step 1 ────────────────────────────────────────────────
    st.subheader("Step 1 — Extract")
    c_url, c_btn = st.columns([5,1])
    with c_url:
        tiktok_url = st.text_input("TikTok URL",
            placeholder="https://www.tiktok.com/@username or /tag/hashtag",
            label_visibility="collapsed")
    with c_btn:
        extract_btn = st.button("🔍 Extract", use_container_width=True)

    if extract_btn:
        if not tiktok_url or "tiktok.com" not in tiktok_url:
            st.error("Please enter a valid TikTok URL.")
        elif not check_ytdlp():
            st.error("yt-dlp not found. Install: `pip install yt-dlp`")
        else:
            with st.spinner("Extracting …"):
                try:
                    vids = extract_with_ytdlp(tiktok_url)
                    if vids:
                        st.session_state.dl_videos   = vids
                        st.session_state.dl_selected = set()
                        st.success(f"✅ Found **{len(vids)}** videos!")
                    else:
                        st.warning("No videos found. Check the URL or profile privacy.")
                except Exception as e:
                    st.error(f"Extraction failed: {e}")

    # ── Step 2 ────────────────────────────────────────────────
    if st.session_state.dl_videos:
        st.markdown("---")
        st.subheader("Step 2 — Browse & Select")

        # Controls row
        ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([1,1,1,2])
        with ctrl1:
            if st.button("✅ Select All", use_container_width=True):
                st.session_state.dl_selected = {v["id"] for v in st.session_state.dl_videos}
                st.rerun()
        with ctrl2:
            if st.button("❌ Deselect All", use_container_width=True):
                st.session_state.dl_selected = set()
                st.rerun()
        with ctrl3:
            view_mode = st.selectbox("View", ["Grid","List"], index=0, label_visibility="collapsed")
            st.session_state.dl_view = view_mode
        with ctrl4:
            search_q = st.text_input("🔍 Filter by title", placeholder="Search…", label_visibility="collapsed")

        videos = st.session_state.dl_videos
        if search_q:
            videos = [v for v in videos if search_q.lower() in v["title"].lower()]

        # ── GRID VIEW ──────────────────────────────────────────
        if st.session_state.dl_view == "Grid":
            CPR = 4
            for row_start in range(0, len(videos), CPR):
                row_vids = videos[row_start:row_start+CPR]
                cols = st.columns(CPR)
                for col, video in zip(cols, row_vids):
                    with col:
                        is_sel = video["id"] in st.session_state.dl_selected
                        border  = "#ee0a78" if is_sel else "#2a2a2a"
                        icon    = "✅" if is_sel else "⬜"
                        dur_s   = video.get("duration",0) or 0
                        dur_str = f"{int(dur_s//60)}:{int(dur_s%60):02d}" if dur_s else "—"
                        st.markdown(f"""
                        <div style="border:3px solid {border};border-radius:12px;
                        padding:10px;margin-bottom:8px;text-align:center;">
                          <div style="font-size:22px">{icon}</div>
                          <div style="font-size:11px;font-weight:600;margin:6px 0;
                          overflow:hidden;max-height:2.8em">{video['title'][:55]}</div>
                          <div style="font-size:11px;color:#666">
                            👁️ {video['views']} &nbsp; ❤️ {video['likes']} &nbsp; ⏱️ {dur_str}
                          </div>
                        </div>""", unsafe_allow_html=True)
                        label = "Deselect" if is_sel else "Select"
                        if st.button(label, key=f"g_{video['id']}", use_container_width=True):
                            if is_sel: st.session_state.dl_selected.discard(video["id"])
                            else:      st.session_state.dl_selected.add(video["id"])
                            st.rerun()

        # ── LIST VIEW ──────────────────────────────────────────
        else:
            for video in videos:
                is_sel  = video["id"] in st.session_state.dl_selected
                bg      = "#1f0010" if is_sel else "#111"
                icon    = "✅" if is_sel else "⬜"
                dur_s   = video.get("duration",0) or 0
                dur_str = f"{int(dur_s//60)}:{int(dur_s%60):02d}" if dur_s else "—"
                c_chk, c_info, c_btn2 = st.columns([0.5, 7, 1.5])
                with c_chk:
                    st.markdown(f"<div style='font-size:24px;padding-top:8px'>{icon}</div>", unsafe_allow_html=True)
                with c_info:
                    st.markdown(
                        f"<div style='background:{bg};border-radius:8px;padding:10px'>"
                        f"<b>{video['title'][:90]}</b><br>"
                        f"<span style='font-size:12px;color:#888'>"
                        f"👁️ {video['views']} &nbsp; ❤️ {video['likes']} &nbsp; ⏱️ {dur_str}"
                        f"</span></div>",
                        unsafe_allow_html=True
                    )
                with c_btn2:
                    label = "Deselect" if is_sel else "Select"
                    if st.button(label, key=f"l_{video['id']}", use_container_width=True):
                        if is_sel: st.session_state.dl_selected.discard(video["id"])
                        else:      st.session_state.dl_selected.add(video["id"])
                        st.rerun()

        # ── Step 3 ────────────────────────────────────────────
        st.markdown("---")
        st.subheader("Step 3 — Download")
        sel_count = len(st.session_state.dl_selected)
        st.info(f"**{sel_count}** video(s) selected")

        if st.button(f"📥 Download {sel_count} Video(s) as ZIP",
                     disabled=sel_count==0, use_container_width=True):
            selected_vids = [v for v in st.session_state.dl_videos
                             if v["id"] in st.session_state.dl_selected]
            pbar   = st.progress(0)
            ptext  = st.empty()
            total  = len(selected_vids)
            id2url = {v["id"]: v["url"] for v in st.session_state.dl_videos}

            with tempfile.TemporaryDirectory() as tmpdir:
                downloaded = []
                for idx, vid in enumerate(selected_vids):
                    url = id2url.get(vid["id"], f"https://www.tiktok.com/@x/video/{vid['id']}")
                    ptext.markdown(f"⬇️ **{idx+1}/{total}** — `{vid['id']}`")
                    pbar.progress(idx/total)
                    tmpl = os.path.join(tmpdir, f"{vid['id']}.%(ext)s")
                    cmd  = [YTDLP,"-f","bestvideo+bestaudio/best",
                            "--merge-output-format","mp4",
                            "--no-warnings","--no-check-certificate",
                            "--extractor-retries","3",
                            "-o",tmpl, url]
                    r = subprocess.run(cmd, capture_output=True, timeout=300)
                    if r.returncode == 0:
                        for fn in os.listdir(tmpdir):
                            if fn.startswith(vid["id"]):
                                downloaded.append(os.path.join(tmpdir,fn)); break
                    pbar.progress((idx+1)/total)

                if downloaded:
                    zbuf = BytesIO()
                    with zipfile.ZipFile(zbuf,"w",zipfile.ZIP_DEFLATED) as zf:
                        for fp in downloaded:
                            zf.write(fp,os.path.basename(fp))
                    zbuf.seek(0)
                    ptext.success(f"✅ {len(downloaded)} video(s) ready!")
                    st.download_button(
                        label=f"⬇️ Save ZIP ({len(downloaded)} videos)",
                        data=zbuf,
                        file_name=f"tiktok_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                        mime="application/zip",
                    )
                else:
                    ptext.error("No videos downloaded successfully.")


# ══════════════════════════════════════════════════════════════
# TAB 3 — VARIANT GENERATOR
# ══════════════════════════════════════════════════════════════
with tab_vg:
    st.header("🎛️ TikTok Variant Generator")
    st.markdown("Generate up to **5 variants** (120fps · 4000kbps · 1080×1920) with hooks, zoom, pitch.")

    def ffmpeg_prefix(hw):
        return [FFMPEG,"-y","-hwaccel","videotoolbox"] if hw else [FFMPEG,"-y"]

    def build_vf(zoom, w, h, out_fps):
        base = []
        if zoom == "zoom + crop":
            base.append("scale=iw*1.01:ih*1.01,crop=iw:ih")
        elif zoom == "zoom inverse + pad":
            base.append("scale=iw*0.99:ih*0.99,pad=iw:ih:(ow-iw)/2:(oh-ih)/2")
        if (w,h)==(TARGET_W,TARGET_H) and zoom=="none":
            norm = f"format=yuv420p,fps={out_fps}"
        else:
            norm = (f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
                    f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p,fps={out_fps}")
        return ",".join([*base,norm]) if base else norm

    def audio_filters(mode, label):
        if mode=="pitch +1%":
            return f"{label}asetrate=44100*1.01,aresample=44100,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo"
        if mode=="pitch -1%":
            return f"{label}asetrate=44100*0.99,aresample=44100,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo"
        return f"{label}aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo"

    def audio_simple(mode):
        if mode=="pitch +1%": return ["-filter:a","asetrate=44100*1.01,aresample=44100","-c:a","aac"]
        if mode=="pitch -1%": return ["-filter:a","asetrate=44100*0.99,aresample=44100","-c:a","aac"]
        return ["-c:a","aac","-ar","44100","-ac","2"]

    def build_cmd(inp, out, *, vname, hw, stable, htype, hdur, himg, hvid, hkeep, zoom, amode, intro, intro_s, ovl=None):
        fps = 120; br = 4000
        w,h,_ = get_video_meta(inp)
        out_fps = min(fps,120)
        base_vf = build_vf(zoom,w,h,out_fps)
        meta = ["-map_metadata","-1",
                "-metadata",f"title=Variant_{vname}",
                "-metadata",f"creation_time={datetime.datetime.now().isoformat()}"]
        if stable:
            vc = ["-b:v",f"{br}k","-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p"]+SAFE_THREADS+meta
        else:
            vc = ["-b:v",f"{br}k","-c:v","h264_videotoolbox","-pix_fmt","yuv420p"]+SAFE_THREADS+meta
        ao = ["-c:a","aac","-ar","44100","-ac","2"]

        if vname=="5" and ovl:
            cmd = ffmpeg_prefix(hw)+["-i",inp,"-i",ovl]
            fc = (f"[0:v]{base_vf}[base];[1:v]scale={TARGET_W}:{TARGET_H}[ov];"
                  f"[base][ov]overlay=0:0[vout];{audio_filters(amode,'[0:a]')}[aout]")
            return cmd+["-filter_complex",fc,"-map","[vout]","-map","[aout]"]+vc+ao+[out], br, get_duration(inp)

        if htype=="None":
            if intro and intro_s>0:
                cmd = ffmpeg_prefix(hw)+[
                    "-f","lavfi","-t",str(intro_s),"-i",
                    f"color=size={TARGET_W}x{TARGET_H}:color=black:rate={out_fps},format=yuv420p",
                    "-f","lavfi","-t",str(intro_s),"-i","anullsrc=channel_layout=stereo:sample_rate=44100",
                    "-i",inp,
                    "-filter_complex",
                    f"[2:v]{base_vf}[vm];{audio_filters(amode,'[2:a]')}[am];"
                    f"[0:v][1:a][vm][am]concat=n=2:v=1:a=1[vout][aout]",
                    "-map","[vout]","-map","[aout]",
                ]+vc+ao+[out]
                return cmd,br,intro_s+get_duration(inp)
            cmd = ffmpeg_prefix(hw)+["-i",inp,"-vf",base_vf,"-r",str(out_fps),
                                      "-map","0:v:0","-map","0:a?"]+vc+audio_simple(amode)+[out]
            return cmd,br,get_duration(inp)

        if htype=="Image overlay":
            cmd = ffmpeg_prefix(hw)+["-i",inp,"-loop","1","-t",str(hdur),"-i",himg]
            fc = (f"[0:v]{base_vf}[base];[1:v][base]scale2ref=w=iw:h=ih[img][b2];"
                  f"[b2][img]overlay=(W-w)/2:(H-h)/2:enable='between(t,0,{hdur})'[vout];"
                  f"{audio_filters(amode,'[0:a]')}[aout]")
            return cmd+["-filter_complex",fc,"-map","[vout]","-map","[aout]"]+vc+ao+[out],br,get_duration(inp)

        if htype=="Video prepend":
            cmd = ffmpeg_prefix(hw)+["-i",hvid,"-i",inp]
            tnorm=(f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
                   f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p,fps={out_fps}")
            fc = f"[0:v]{tnorm}[vh];[1:v]{base_vf}[vm];"
            fc += f"{audio_filters(amode,'[0:a]')}[ah];" if hkeep else "anullsrc=channel_layout=stereo:sample_rate=44100[ah];"
            fc += f"{audio_filters(amode,'[1:a]')}[am];[vh][ah][vm][am]concat=n=2:v=1:a=1[vout][aout]"
            return cmd+["-filter_complex",fc,"-map","[vout]","-map","[aout]"]+vc+ao+[out],br,get_duration(hvid)+get_duration(inp)

        if htype=="Video overlay":
            cmd = ffmpeg_prefix(hw)+["-i",inp,"-i",hvid]
            tnorm=(f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
                   f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p,fps={out_fps}")
            fc = (f"[0:v]{base_vf}[base];[1:v]{tnorm}[hv];"
                  f"[base][hv]overlay=(W-w)/2:(H-h)/2:enable='between(t,0,{hdur})'[vout];"
                  f"{audio_filters(amode,'[0:a]')}[aout]")
            return cmd+["-filter_complex",fc,"-map","[vout]","-map","[aout]"]+vc+ao+[out],br,get_duration(inp)

        cmd = ffmpeg_prefix(hw)+["-i",inp,"-vf",base_vf,"-r",str(out_fps),"-map","0:v:0","-map","0:a?"]+vc+ao+[out]
        return cmd,br,get_duration(inp)

    # ── Presets ────────────────────────────────────────────────
    PRESETS = {
        "Custom": None,
        "⚡ Quick TikTok (V1 only)": {"variants":["1"],"zoom":"zoom + crop","stable":True,"hw":False},
        "🔥 Viral Pack (V1-V4)":     {"variants":["1","2","3","4"],"zoom":"zoom + crop","stable":True,"hw":False},
        "🎯 Ultra (All V1-V5)":       {"variants":["1","2","3","4","5"],"zoom":"zoom + crop","stable":True,"hw":False},
    }

    with st.expander("⚙️ Settings", expanded=True):
        preset_choice = st.selectbox("🎛️ Preset", list(PRESETS.keys()))
        preset = PRESETS[preset_choice]

        col_a, col_b = st.columns(2)
        with col_a:
            stable = st.checkbox("Ultra-stable (libx264)", value=preset["stable"] if preset else True)
            hw     = st.checkbox("Hardware decode (Videotoolbox)", value=preset["hw"] if preset else False)
            zoom   = st.radio("Creative zoom", ["zoom + crop","zoom inverse + pad","none"],
                              index=["zoom + crop","zoom inverse + pad","none"].index(preset["zoom"] if preset else "zoom + crop"))
        with col_b:
            default_v = preset["variants"] if preset else ["1","2","3","4"]
            sel_v = st.multiselect("Variants to generate",["1","2","3","4","5"],default=default_v,
                                   help="1=Base | 2=+Intro+Hook | 3=+Pitch+1% | 4=+Pitch-1% | 5=Overlay")
            htype = st.selectbox("Hook type",["None","Image overlay","Video prepend","Video overlay"])

    with st.expander("🎣 Hook & Overlay files"):
        himg=hvid=ovl=None; hkeep=False
        if htype=="Image overlay":
            himg = st.file_uploader("Hook image",type=["png","jpg","jpeg"],key="vg_hi")
        elif htype in ("Video prepend","Video overlay"):
            hvid = st.file_uploader("Hook video",type=["mp4","mov","m4v"],key="vg_hv")
            if htype=="Video prepend": hkeep = st.checkbox("Keep hook audio",value=True)
        ovl = st.file_uploader("V5 Overlay PNG (transparent)",type=["png"],key="vg_ov")

    st.markdown("### 📥 Videos")
    vg_videos = st.file_uploader("Drop videos here",type=["mp4","mov","m4v"],
                                  accept_multiple_files=True,key="vg_vids")

    st.markdown("---")
    run_vg = st.button("🚀 Generate Variants", type="primary", use_container_width=True)

    if run_vg and vg_videos:
        if not sel_v: st.error("Select at least one variant."); st.stop()
        all_defs = {
            "1":{"name":"1","hdur":0.3,"intro":False,"isec":0.0,"audio":"normal"},
            "2":{"name":"2","hdur":0.1,"intro":True, "isec":0.01,"audio":"normal"},
            "3":{"name":"3","hdur":0.1,"intro":True, "isec":0.01,"audio":"pitch +1%"},
            "4":{"name":"4","hdur":0.1,"intro":True, "isec":0.01,"audio":"pitch -1%"},
            "5":{"name":"5","hdur":0.3,"intro":False,"isec":0.0,"audio":"normal"},
        }
        variants = [all_defs[v] for v in sel_v]
        total_tasks = len(vg_videos)*len(variants)
        overall = st.progress(0)
        ostatus = st.empty()
        done_tasks = 0
        all_files = []

        himg_p=hvid_p=ovl_p=None
        for uf,(attr,key) in [(himg,("himg_p","hi")),(hvid,("hvid_p","hv")),(ovl,("ovl_p","ov"))]:
            if uf:
                with tempfile.NamedTemporaryFile(delete=False,suffix=os.path.splitext(uf.name)[1]) as f:
                    f.write(uf.read())
                    if attr=="himg_p": himg_p=f.name
                    elif attr=="hvid_p": hvid_p=f.name
                    else: ovl_p=f.name

        for vi,file in enumerate(vg_videos):
            st.markdown(f"---\n## 🎬 Video {vi+1}/{len(vg_videos)}: **{file.name}**")
            with tempfile.NamedTemporaryFile(delete=False,suffix=os.path.splitext(file.name)[1]) as tmp:
                tmp.write(file.read()); inp=tmp.name

            base = os.path.splitext(file.name)[0]
            for var in variants:
                out_name = f"{base}_v{var['name']}.mp4"
                out_tmp  = os.path.join(tempfile.gettempdir(),out_name)
                ostatus.markdown(f"Video **{vi+1}** · Variant **{var['name']}** · **{done_tasks}/{total_tasks}** done")
                st.markdown(f"### ▶️ Variant {var['name']}")
                try:
                    cmd,br,est = build_cmd(inp,out_tmp,vname=var["name"],hw=hw,stable=stable,
                                           htype=htype,hdur=var["hdur"],himg=himg_p,hvid=hvid_p,
                                           hkeep=hkeep,zoom=zoom,amode=var["audio"],
                                           intro=var["intro"],intro_s=var["isec"],ovl=ovl_p)
                    if cmd is None: done_tasks+=1; overall.progress(done_tasks/total_tasks); continue
                    pb=st.progress(0); pt=st.empty()
                    log_exp=st.expander(f"FFmpeg logs — V{var['name']}",expanded=False)
                    lb=log_exp.empty()
                    rc = run_ffmpeg_progress(cmd,est or 0,
                                            prog_cb=lambda p,_pb=pb,_pt=pt: (_pb.progress(p),_pt.markdown(f"**{p}%**")),
                                            log_cb=lambda l,_lb=lb: _lb.code(l,language="bash"))
                    if rc==0: st.success(f"✅ Variant {var['name']} done"); all_files.append({"path":out_tmp,"name":out_name})
                    else:     st.error(f"FFmpeg error code {rc}")
                except Exception as e:
                    st.error(f"Error: {e}\n{traceback.format_exc()}")
                done_tasks+=1; overall.progress(done_tasks/total_tasks)
            try: os.unlink(inp)
            except Exception: pass

        st.markdown("---\n# 📦 All Done")
        if all_files:
            zbuf=BytesIO()
            with zipfile.ZipFile(zbuf,"w",zipfile.ZIP_DEFLATED) as zf:
                for fi in all_files:
                    try: zf.write(fi["path"],fi["name"])
                    except Exception: pass
            zbuf.seek(0)
            st.success(f"🎉 {len(all_files)} variant(s) ready!")
            st.balloons()
            st.download_button(f"⬇️ Download All ({len(all_files)} files)",zbuf,
                               f"TikTok_Variants_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.zip","application/zip",key="vg_dl")
            for fi in all_files:
                try: os.unlink(fi["path"])
                except Exception: pass
        else:
            st.error("No variants generated successfully.")
    elif not vg_videos:
        st.info("Upload videos above, then click Generate.")
        st.markdown("""
| # | What it does |
|---|---|
| 1 | Base — 120fps, 4000kbps |
| 2 | + Invisible 0.01s intro + Hook |
| 3 | V2 + Audio pitch **+1%** |
| 4 | V2 + Audio pitch **−1%** |
| 5 | + Custom overlay / border PNG |
""")


# ══════════════════════════════════════════════════════════════
# IMAGE PROCESSING HELPERS
# ══════════════════════════════════════════════════════════════
def optimize_image(img_bytes, scale=2.0, sharpen=True, sharpen_amount=150,
                   enhance_color=False, fmt="JPEG", quality=90):
    img = Image.open(BytesIO(img_bytes))
    orig_mode = img.mode
    orig_w, orig_h = img.size
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)

    out = img.resize((new_w, new_h), Image.LANCZOS)

    if sharpen:
        out = out.filter(ImageFilter.UnsharpMask(radius=1.5, percent=sharpen_amount, threshold=3))

    if enhance_color:
        out = ImageEnhance.Color(out).enhance(1.15)
        out = ImageEnhance.Contrast(out).enhance(1.05)

    buf = BytesIO()
    if fmt == "WEBP":
        if out.mode not in ("RGB","RGBA"): out = out.convert("RGBA" if "A" in out.mode else "RGB")
        out.save(buf, "WEBP", quality=quality, method=6)
    elif fmt == "PNG":
        out.save(buf, "PNG", optimize=True)
    else:
        if out.mode != "RGB": out = out.convert("RGB")
        out.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)

    return buf.getvalue(), (orig_w, orig_h), (new_w, new_h)


def convert_to_webp(img_bytes, quality=85, lossless=False):
    img = Image.open(BytesIO(img_bytes))
    if img.mode == "P": img = img.convert("RGBA")
    elif img.mode not in ("RGB","RGBA","L"): img = img.convert("RGB")
    buf = BytesIO()
    if lossless:
        img.save(buf, "WEBP", lossless=True, quality=100)
    else:
        img.save(buf, "WEBP", quality=quality, method=6)
    return buf.getvalue()


def human_size(n):
    if n < 1024: return f"{n} B"
    if n < 1024**2: return f"{n/1024:.1f} KB"
    return f"{n/1024**2:.2f} MB"


# ══════════════════════════════════════════════════════════════
# TAB 4 — IMAGE OPTIMIZER (Upscale + Enhance)
# ══════════════════════════════════════════════════════════════
with tab_img:
    st.header("🖼️ Image Optimizer — Upscale & Enhance")
    st.markdown("Upload images, choose upscale factor, apply smart sharpening and color enhancement.")

    # Settings
    c1, c2, c3 = st.columns(3)
    with c1:
        scale_mode = st.radio("Scale mode", ["Factor (×)", "Custom size"])
        if scale_mode == "Factor (×)":
            scale_factor = st.select_slider("Scale factor", options=[1.5, 2.0, 2.5, 3.0, 4.0], value=2.0)
            custom_w = custom_h = None
        else:
            scale_factor = None
            custom_w = st.number_input("Width (px)", min_value=100, max_value=8000, value=1920)
            custom_h = st.number_input("Height (px)", min_value=100, max_value=8000, value=1080)

    with c2:
        out_fmt   = st.selectbox("Output format", ["JPEG","PNG","WEBP"])
        quality   = st.slider("Quality (JPEG/WebP)", 60, 100, 90)
        do_sharpen = st.checkbox("Smart sharpen", value=True)
        sharpen_amt = st.slider("Sharpen amount", 50, 300, 150, disabled=not do_sharpen)

    with c3:
        enhance_col = st.checkbox("Color + Contrast boost", value=False)
        st.markdown("---")
        st.markdown("**What this does:**\n"
                    "- LANCZOS resampling (best algorithm)\n"
                    "- Unsharp mask sharpening\n"
                    "- Optional color/contrast boost")

    imgs = st.file_uploader(
        "Upload images (PNG · JPG · JPEG · BMP · TIFF · WebP)",
        type=["png","jpg","jpeg","bmp","tiff","tif","webp"],
        accept_multiple_files=True,
        key="img_opt_up",
    )

    if imgs and st.button("🚀 Optimize All", type="primary", use_container_width=True):
        results_buf = BytesIO()
        ext_map = {"JPEG":"jpg","PNG":"png","WEBP":"webp"}
        ext = ext_map[out_fmt]

        with zipfile.ZipFile(results_buf,"w",zipfile.ZIP_DEFLATED) as zf:
            cols = st.columns(min(len(imgs),4))
            for i,file in enumerate(imgs):
                raw = file.read()
                orig_sz = len(raw)

                # Compute actual scale
                if scale_factor:
                    sf = scale_factor
                else:
                    img_tmp = Image.open(BytesIO(raw))
                    sf = min(custom_w/img_tmp.width, custom_h/img_tmp.height)

                try:
                    new_bytes,(ow,oh),(nw,nh) = optimize_image(
                        raw, scale=sf, sharpen=do_sharpen,
                        sharpen_amount=sharpen_amt,
                        enhance_color=enhance_col,
                        fmt=out_fmt, quality=quality
                    )
                    new_sz = len(new_bytes)
                    out_name = os.path.splitext(file.name)[0]+f"_x{sf}.{ext}"
                    zf.writestr(out_name, new_bytes)

                    with cols[i % len(cols)]:
                        st.image(new_bytes, use_container_width=True)
                        size_change = "📈" if new_sz > orig_sz else "📉"
                        st.markdown(
                            f"**{file.name[:28]}**  \n"
                            f"`{ow}×{oh}` → `{nw}×{nh}`  \n"
                            f"{human_size(orig_sz)} → {size_change} **{human_size(new_sz)}**"
                        )
                except Exception as e:
                    st.error(f"❌ {file.name}: {e}")

        results_buf.seek(0)
        st.success(f"✅ {len(imgs)} image(s) optimized!")
        st.download_button(
            "⬇️ Download All (ZIP)",
            data=results_buf,
            file_name=f"optimized_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.zip",
            mime="application/zip",
        )
    elif not imgs:
        st.info("Upload one or more images above, then click Optimize All.")


# ══════════════════════════════════════════════════════════════
# TAB 5 — → WebP CONVERTER
# ══════════════════════════════════════════════════════════════
with tab_webp:
    st.header("🔄 Image → WebP Converter")
    st.markdown("Batch convert any image format to **WebP** — smaller files, same quality.")

    c1,c2 = st.columns(2)
    with c1:
        wp_quality  = st.slider("WebP quality", 50, 100, 82)
        wp_lossless = st.checkbox("Lossless mode", value=False,
                                  help="Lossless = perfect quality but larger file. Best for PNG with transparency.")
    with c2:
        st.markdown("**WebP advantages:**\n"
                    "- ~30% smaller than JPEG at same quality\n"
                    "- ~25% smaller than PNG\n"
                    "- Supports transparency (like PNG)\n"
                    "- Supported by all modern browsers")

    wp_imgs = st.file_uploader(
        "Upload images (any format)",
        type=["png","jpg","jpeg","bmp","tiff","tif","gif","webp"],
        accept_multiple_files=True,
        key="webp_up",
    )

    if wp_imgs and st.button("🔄 Convert All → WebP", type="primary", use_container_width=True):
        zbuf = BytesIO()
        total_orig = 0; total_new = 0

        with zipfile.ZipFile(zbuf,"w",zipfile.ZIP_DEFLATED) as zf:
            rows = []
            for file in wp_imgs:
                raw = file.read()
                orig_sz = len(raw)
                total_orig += orig_sz
                try:
                    new_bytes = convert_to_webp(raw, quality=wp_quality, lossless=wp_lossless)
                    new_sz = len(new_bytes)
                    total_new += new_sz
                    out_name = os.path.splitext(file.name)[0]+".webp"
                    zf.writestr(out_name, new_bytes)
                    saved_pct = round((1 - new_sz/orig_sz)*100, 1)
                    rows.append({
                        "File":     file.name,
                        "Original": human_size(orig_sz),
                        "WebP":     human_size(new_sz),
                        "Saved":    f"{saved_pct}%",
                        "Status":   "✅",
                    })
                except Exception as e:
                    rows.append({"File":file.name,"Original":human_size(orig_sz),
                                 "WebP":"—","Saved":"—","Status":f"❌ {e}"})

        zbuf.seek(0)

        import pandas as pd
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        total_saved = round((1-total_new/total_orig)*100,1) if total_orig else 0
        c1,c2,c3 = st.columns(3)
        c1.metric("Total original", human_size(total_orig))
        c2.metric("Total WebP",     human_size(total_new))
        c3.metric("Space saved",    f"{total_saved}%")

        st.download_button(
            "⬇️ Download All WebP (ZIP)",
            data=zbuf,
            file_name=f"webp_converted_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.zip",
            mime="application/zip",
        )
    elif not wp_imgs:
        st.info("Upload images above to convert them to WebP.")


# ══════════════════════════════════════════════════════════════
# TAB 6 — VIDEO UPSCALER  (Full Auto 5-Stage Pipeline)
# ══════════════════════════════════════════════════════════════
with tab_upscale:
    st.header("🎬 Video Upscaler — Auto Pixel & Quality Enhancement")
    st.markdown(
        "Upload any video. The app **automatically** analyzes it and applies a **5-stage enhancement pipeline** — "
        "no settings needed. Text, faces, edges and colors are all enhanced."
    )

    # ── Pipeline visual ──────────────────────────────────────
    st.markdown("""
<div style="display:flex;gap:8px;margin:14px 0;flex-wrap:wrap">
  <div style="background:#1a1a1a;border:1px solid #ee0a78;border-radius:10px;padding:10px 16px;flex:1;min-width:120px;text-align:center">
    <div style="font-size:22px">🧹</div><b>Stage 1</b><br><span style="color:#aaa;font-size:12px">Deblock &<br>Denoise</span>
  </div>
  <div style="color:#ee0a78;font-size:24px;align-self:center">→</div>
  <div style="background:#1a1a1a;border:1px solid #ee0a78;border-radius:10px;padding:10px 16px;flex:1;min-width:120px;text-align:center">
    <div style="font-size:22px">✨</div><b>Stage 2</b><br><span style="color:#aaa;font-size:12px">Pre-Sharpen<br>(text & edges)</span>
  </div>
  <div style="color:#ee0a78;font-size:24px;align-self:center">→</div>
  <div style="background:#1a1a1a;border:1px solid #ee0a78;border-radius:10px;padding:10px 16px;flex:1;min-width:120px;text-align:center">
    <div style="font-size:22px">🔍</div><b>Stage 3</b><br><span style="color:#aaa;font-size:12px">LANCZOS<br>Upscale</span>
  </div>
  <div style="color:#ee0a78;font-size:24px;align-self:center">→</div>
  <div style="background:#1a1a1a;border:1px solid #ee0a78;border-radius:10px;padding:10px 16px;flex:1;min-width:120px;text-align:center">
    <div style="font-size:22px">🎯</div><b>Stage 4</b><br><span style="color:#aaa;font-size:12px">Post-Sharpen<br>(restore detail)</span>
  </div>
  <div style="color:#ee0a78;font-size:24px;align-self:center">→</div>
  <div style="background:#1a1a1a;border:1px solid #ee0a78;border-radius:10px;padding:10px 16px;flex:1;min-width:120px;text-align:center">
    <div style="font-size:22px">🎨</div><b>Stage 5</b><br><span style="color:#aaa;font-size:12px">Color &<br>Contrast Boost</span>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Target resolution selector ────────────────────────────
    UP_TARGETS = {
        "🤖 Auto (smart detect)": "auto",
        "720p  (1280×720)":       "1280:720",
        "1080p (1920×1080)":      "1920:1080",
        "1440p (2560×1440)":      "2560:1440",
        "4K    (3840×2160)":      "3840:2160",
    }
    # Auto CRF (quality-based) bitrate per resolution
    AUTO_CRF    = {"720":16, "1080":16, "1440":15, "2160":14}
    AUTO_BITRATE= {"720":6000,"1080":10000,"1440":16000,"2160":22000}

    col_res, col_mode = st.columns(2)
    with col_res:
        up_target = st.selectbox("Target resolution", list(UP_TARGETS.keys()), index=0)
    with col_mode:
        enhance_mode = st.selectbox("Enhancement strength",
            ["🔥 Maximum (recommended)","⚡ Balanced","🌿 Light (fast)"],
            index=0)

    with st.expander("⚙️ Advanced options (optional)", expanded=False):
        adv_c1, adv_c2, adv_c3 = st.columns(3)
        with adv_c1:
            adv_denoise  = st.slider("Denoise strength", 0.0, 4.0, 1.5, 0.5,
                                     help="0 = no denoise. Higher = stronger noise removal before upscale.")
            adv_pre_sharp = st.slider("Pre-sharpen (before upscale)", 0.0, 2.0, 1.0, 0.1,
                                      help="Sharpens edges/text BEFORE upscaling. Makes text crisper.")
        with adv_c2:
            adv_post_sharp = st.slider("Post-sharpen (after upscale)", 0.0, 1.5, 0.6, 0.1,
                                       help="Sharpens AFTER upscaling to restore perceived sharpness.")
            adv_contrast   = st.slider("Contrast boost", 1.0, 1.2, 1.06, 0.01)
        with adv_c3:
            adv_saturation = st.slider("Saturation boost", 1.0, 1.3, 1.10, 0.01)
            adv_brightness = st.slider("Brightness", -0.1, 0.1, 0.01, 0.01)
            adv_preset     = st.selectbox("Encoding preset",
                                          ["veryfast","fast","medium","slow"], index=2)

    up_video = st.file_uploader(
        "🎬 Drop your video here",
        type=["mp4","mov","m4v","avi","mkv","flv","wmv"],
        key="up_video",
    )

    if up_video:
        if st.button("🚀 Auto-Enhance & Upscale", type="primary", use_container_width=True):

            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(up_video.name)[1]) as fin:
                fin.write(up_video.read()); inp_path = fin.name

            orig_w, orig_h, orig_fps = get_video_meta(inp_path)
            dur = get_duration(inp_path)
            orig_w  = orig_w  or 1280
            orig_h  = orig_h  or 720
            orig_fps = orig_fps or 30.0

            # ── Auto target resolution ────────────────────────
            raw_target = UP_TARGETS[up_target]
            if raw_target == "auto":
                if orig_h <= 360:   tw,th = 1280,720
                elif orig_h <= 540: tw,th = 1920,1080
                elif orig_h <= 720: tw,th = 1920,1080
                elif orig_h <= 1080:tw,th = 2560,1440
                else:               tw,th = 3840,2160
            else:
                tw,th = (int(x) for x in raw_target.split(":"))

            scale_factor = round(tw / orig_w, 2)
            res_key = str(th)
            crf     = AUTO_CRF.get(res_key, 16)
            bitrate = AUTO_BITRATE.get(res_key, 10000)

            # ── Enhancement strength presets ──────────────────
            if enhance_mode.startswith("🔥"):
                denoise_l    = 1.5;  pre_s  = 1.0;  post_s = 0.6
                contrast_v   = 1.06; sat_v  = 1.10; bright = 0.01
                enc_preset   = "slow"
            elif enhance_mode.startswith("⚡"):
                denoise_l    = 0.8;  pre_s  = 0.6;  post_s = 0.4
                contrast_v   = 1.03; sat_v  = 1.05; bright = 0.0
                enc_preset   = "medium"
            else:
                denoise_l    = 0.3;  pre_s  = 0.3;  post_s = 0.2
                contrast_v   = 1.01; sat_v  = 1.02; bright = 0.0
                enc_preset   = "fast"

            # Override with advanced settings if user changed them
            if adv_denoise   != 1.5: denoise_l  = adv_denoise
            if adv_pre_sharp != 1.0: pre_s      = adv_pre_sharp
            if adv_post_sharp!= 0.6: post_s     = adv_post_sharp
            if adv_contrast  != 1.06:contrast_v = adv_contrast
            if adv_saturation!= 1.10:sat_v      = adv_saturation
            if adv_brightness != 0.01:bright     = adv_brightness
            if adv_preset     != "medium": enc_preset = adv_preset

            # ── Show analysis card ────────────────────────────
            st.markdown(f"""
<div style="background:#1a1a1a;border-radius:12px;padding:16px;border-left:4px solid #ee0a78;margin:10px 0">
  <b>🔎 Auto Analysis Result</b><br>
  Source: <code>{orig_w}×{orig_h}</code> @ <code>{orig_fps:.1f}fps</code> · <code>{dur:.1f}s</code><br>
  Target: <b><code>{tw}×{th}</code></b> · Scale factor: <b>{scale_factor}×</b><br>
  Enhancement: <b>{enhance_mode}</b> · CRF: <b>{crf}</b> · Preset: <b>{enc_preset}</b>
</div>
""", unsafe_allow_html=True)

            out_name = os.path.splitext(up_video.name)[0] + f"_enhanced_{tw}x{th}.mp4"
            out_path = os.path.join(tempfile.gettempdir(), out_name)

            # ══════════════════════════════════════════════════
            # BUILD THE 5-STAGE FILTER CHAIN
            # ══════════════════════════════════════════════════
            filters = []

            # Stage 1 — Deblock + Denoise (remove compression artifacts)
            if denoise_l > 0:
                # hqdn3d: luma_spatial, chroma_spatial, luma_temporal, chroma_temporal
                ls = round(denoise_l, 2)
                lt = round(denoise_l * 4, 2)
                cs = round(denoise_l * 0.75, 2)
                ct = round(denoise_l * 3, 2)
                filters.append(f"hqdn3d={ls}:{cs}:{lt}:{ct}")

            # Stage 2 — Pre-sharpen (critical for text crispness before upscale)
            if pre_s > 0:
                # unsharp: lx,ly,la (luma) cx,cy,ca (chroma)
                # Large radius + medium amount = enhances fine details and text edges
                la = round(pre_s, 2)
                ca = round(pre_s * 0.4, 2)
                filters.append(f"unsharp=luma_msize_x=7:luma_msize_y=7:luma_amount={la}"
                                f":chroma_msize_x=5:chroma_msize_y=5:chroma_amount={ca}")

            # Stage 3 — LANCZOS upscale (best quality algorithm)
            # accurate_rnd + full_chroma = best color & sharpness accuracy
            scale_str = (
                f"scale={tw}:{th}"
                f":flags=lanczos+accurate_rnd+full_chroma_inp+full_chroma_int"
                f":force_original_aspect_ratio=decrease"
            )
            pad_str = f"pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
            filters.append(f"{scale_str},{pad_str}")

            # Stage 4 — Post-sharpen (restore sharpness lost in resize)
            if post_s > 0:
                pa = round(post_s, 2)
                ca2 = round(post_s * 0.3, 2)
                filters.append(f"unsharp=luma_msize_x=3:luma_msize_y=3:luma_amount={pa}"
                                f":chroma_msize_x=3:chroma_msize_y=3:chroma_amount={ca2}")

            # Stage 5 — Color, contrast, brightness enhancement
            filters.append(
                f"eq=contrast={round(contrast_v,3)}"
                f":brightness={round(bright,3)}"
                f":saturation={round(sat_v,3)}"
                f":gamma=1.02"
            )

            # Final format
            filters.append("format=yuv420p")

            vf_chain = ",".join(filters)

            # ── FFmpeg command ────────────────────────────────
            cmd = [
                FFMPEG, "-y", "-i", inp_path,
                "-vf", vf_chain,
                "-c:v", "libx264",
                "-preset", enc_preset,
                "-crf", str(crf),          # quality-based (better than just bitrate)
                "-maxrate", f"{bitrate}k",
                "-bufsize", f"{bitrate*2}k",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "44100", "-ac", "2",
                "-map_metadata", "-1",
                out_path,
            ]

            # ── Pipeline stage display ────────────────────────
            stages_text = st.empty()
            pbar  = st.progress(0)
            ptext = st.empty()
            log_exp = st.expander("📋 FFmpeg detail log", expanded=False)
            lb = log_exp.empty()

            stage_labels = [
                "🧹 Stage 1: Deblocking & denoising compression artifacts…",
                "✨ Stage 2: Pre-sharpening text & edges…",
                "🔍 Stage 3: LANCZOS upscaling pixels…",
                "🎯 Stage 4: Post-sharpening to restore detail…",
                "🎨 Stage 5: Color & contrast enhancement…",
            ]

            def smart_progress(p, _pb=pbar, _pt=ptext, _st=stages_text):
                _pb.progress(p)
                stage_idx = min(4, int(p / 20))
                _st.markdown(f"**{stage_labels[stage_idx]}**")
                _pt.markdown(f"⚙️ Overall: **{p}%** complete")

            rc = run_ffmpeg_progress(
                cmd, dur,
                prog_cb=smart_progress,
                log_cb=lambda l, _lb=lb: _lb.code(l, language="bash"),
            )

            try: os.unlink(inp_path)
            except Exception: pass

            if rc == 0 and os.path.exists(out_path):
                file_size = os.path.getsize(out_path)
                stages_text.empty()
                pbar.progress(100)
                ptext.success(f"✅ Enhancement complete! **{out_name}** — {human_size(file_size)}")

                with open(out_path, "rb") as f:
                    st.download_button(
                        label=f"⬇️ Download Enhanced Video  {tw}×{th}  ({human_size(file_size)})",
                        data=f.read(),
                        file_name=out_name,
                        mime="video/mp4",
                        use_container_width=True,
                    )
                try: os.unlink(out_path)
                except Exception: pass
            else:
                ptext.error(f"❌ Enhancement failed (exit code {rc}). Check the log above.")

    else:
        st.info("⬆️ Upload a video above — the app will automatically analyze and enhance it.")
        st.markdown("""
| Stage | What it does | Why it matters |
|---|---|---|
| 🧹 Denoise | Removes H.264/H.265 compression blocks & noise | Prevents upscaling artifacts from being magnified |
| ✨ Pre-sharpen | Sharpens edges & text BEFORE upscale | Text stays crisp after resize |
| 🔍 LANCZOS | Best-quality upscaling algorithm with full chroma accuracy | Sharpest pixels possible |
| 🎯 Post-sharpen | Restores perceived sharpness after resize | Counters softness introduced by scaling |
| 🎨 Color boost | Contrast +6%, saturation +10%, gamma 1.02 | Vibrant, professional-looking output |

**Auto resolution logic:**
- Source ≤ 360p → output **720p**
- Source ≤ 720p → output **1080p**
- Source ≤ 1080p → output **1440p**
- Source > 1080p → output **4K**
""")
