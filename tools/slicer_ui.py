#!/usr/bin/env python3
"""Minimal live UI for tilesheet_slicer.

  python tools/slicer_ui.py [--port 8765] [--out Sprites]

Opens http://127.0.0.1:8765 : load a sheet (URL or file), tweak grid settings with
a live preview, click Save to write sprites + manifest via tilesheet_slicer.
"""
import argparse
import io
import json
import os
import subprocess
import sys
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from tilesheet_slicer import slice_sheet  # noqa: E402

OUT = Path("Sprites")

PAGE = r"""<!doctype html><meta charset=utf-8><title>Tilesheet Slicer</title>
<style>
body{font:14px system-ui;margin:0;background:#1e1e1e;color:#ddd;display:flex;height:100vh}
#side{width:260px;padding:12px;background:#2a2a2a;overflow:auto;box-sizing:border-box}
#main{flex:1;overflow:auto;padding:12px}
label{display:block;margin:8px 0 2px;font-size:12px;color:#999}
input[type=text],input[type=number]{width:100%;box-sizing:border-box;background:#111;color:#ddd;border:1px solid #444;padding:4px}
button{margin-top:8px;padding:6px 10px;width:100%;cursor:pointer}
#sheet{position:relative;display:inline-block;background:repeating-conic-gradient(#333 0 25%,#2b2b2b 0 50%) 0 0/16px 16px}
#sheet canvas{display:block}
#grid{position:absolute;inset:0;pointer-events:none}
#sprites{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
.sp{background:repeating-conic-gradient(#333 0 25%,#2b2b2b 0 50%) 0 0/12px 12px;text-align:center;font-size:11px}
.sp canvas{display:block}
#msg{margin-top:10px;font-size:12px;color:#8c8;word-break:break-all}
</style>
<div id=side>
 <b>Tilesheet Slicer</b>
 <label>URL</label><input type=text id=url placeholder="https://…/sheet.png">
 <button id=load>Load URL</button>
 <label>…or file</label><input type=file id=file accept="image/*">
 <label>Name</label><input type=text id=name>
 <label>Columns</label><input type=number id=cols value=8 min=1>
 <label>Tile width (0 = auto)</label><input type=number id=tw value=0 min=0>
 <label>Tile height (0 = 2×width)</label><input type=number id=th value=0 min=0>
 <label><input type=checkbox id=trim> Trim to content</label>
 <label><input type=checkbox id=empty> Keep empty cells</label>
 <label>Save to folder</label><input type=text id=out>
 <button id=browse>Browse…</button>
 <button id=save>Save sprites</button>
 <div id=msg></div>
</div>
<div id=main><div id=sheet><canvas id=cv></canvas><canvas id=grid></canvas></div><div id=sprites></div></div>
<script>
const $=id=>document.getElementById(id);
let img=null, srcKind=null, srcVal=null, tiles=[];
function setImg(blobOrUrl,name){
  const i=new Image(); i.onload=()=>{img=i;if(name&&!$('name').value)$('name').value=name;render()};
  i.src=blobOrUrl;
}
$('load').onclick=()=>{const u=$('url').value.trim();if(!u)return;
  srcKind='url';srcVal=u;$('name').value=u.split('/').pop().replace(/\.[^.]+$/,'');
  setImg('/fetch?url='+encodeURIComponent(u));};
$('file').onchange=e=>{const f=e.target.files[0];if(!f)return;
  srcKind='file';srcVal=f;$('name').value=f.name.replace(/\.[^.]+$/,'');setImg(URL.createObjectURL(f));};
['cols','tw','th','trim','empty'].forEach(k=>$(k).oninput=render);
function dims(){
  const cols=+$('cols').value||1; let tw=+$('tw').value||Math.floor(img.width/cols);
  let th=+$('th').value||tw*2; return {cols:Math.floor(img.width/tw),rows:Math.floor(img.height/th),tw,th};
}
function render(){
  if(!img)return; const {cols,rows,tw,th}=dims();
  const cv=$('cv'),g=$('grid'); cv.width=g.width=img.width; cv.height=g.height=img.height;
  const cx=cv.getContext('2d'); cx.drawImage(img,0,0);
  const gx=g.getContext('2d'); gx.strokeStyle='rgba(0,200,255,.6)';
  for(let c=0;c<=cols;c++){gx.beginPath();gx.moveTo(c*tw+.5,0);gx.lineTo(c*tw+.5,rows*th);gx.stroke()}
  for(let r=0;r<=rows;r++){gx.beginPath();gx.moveTo(0,r*th+.5);gx.lineTo(cols*tw,r*th+.5);gx.stroke()}
  const box=$('sprites'); box.innerHTML=''; let n=0;
  for(let r=0;r<rows;r++)for(let c=0;c<cols;c++){
    const d=cx.getImageData(c*tw,r*th,tw,th).data; let minx=tw,miny=th,maxx=-1,maxy=-1;
    for(let y=0;y<th;y++)for(let x=0;x<tw;x++)if(d[(y*tw+x)*4+3]){
      if(x<minx)minx=x;if(x>maxx)maxx=x;if(y<miny)miny=y;if(y>maxy)maxy=y;}
    const empty=maxx<0; if(empty&&!$('empty').checked)continue; n++;
    let sx=0,sy=0,sw=tw,sh=th;
    if($('trim').checked&&!empty){sx=minx;sy=miny;sw=maxx-minx+1;sh=maxy-miny+1}
    const s=document.createElement('canvas'); s.width=sw; s.height=sh;
    s.getContext('2d').drawImage(img,c*tw+sx,r*th+sy,sw,sh,0,0,sw,sh);
    s.style.width=Math.min(sw,96)+'px'; s.style.height='auto';
    const w=document.createElement('div'); w.className='sp'; w.append(s,r*cols+c); box.append(w);
  }
  $('msg').textContent=`${img.width}×${img.height} · tile ${tw}×${th} · ${n}/${cols*rows} sprites`;
}
fetch('/config').then(r=>r.json()).then(c=>{$('out').value=c.out});
$('browse').onclick=async()=>{
  const r=await fetch('/browse?start='+encodeURIComponent($('out').value)); const p=await r.text();
  if(p)$('out').value=p;
};
$('save').onclick=async()=>{
  if(!img)return; const q=new URLSearchParams({out:$('out').value,name:$('name').value,cols:$('cols').value,
    tw:$('tw').value,th:$('th').value,trim:$('trim').checked?1:0,empty:$('empty').checked?1:0,kind:srcKind});
  let body; if(srcKind==='url'){q.set('url',srcVal);body=''} else body=await srcVal.arrayBuffer();
  $('msg').textContent='Saving…';
  const r=await fetch('/save?'+q,{method:'POST',body}); $('msg').textContent=await r.text();
};
</script>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, data, ctype="text/plain; charset=utf-8"):
        if isinstance(data, str):
            data = data.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    @staticmethod
    def _fetch(url):
        if not url.startswith(("http://", "https://")):
            raise ValueError("only http(s) URLs")
        req = urllib.request.Request(url, headers={"User-Agent": "tilesheet-slicer"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            return self._send(200, PAGE, "text/html; charset=utf-8")
        if u.path == "/config":
            return self._send(200, json.dumps({"out": str(OUT.resolve())}), "application/json")
        if u.path == "/browse":
            start = parse_qs(u.query).get("start", [""])[0]
            code = ("import sys,tkinter as t;from tkinter import filedialog as f;"
                    "r=t.Tk();r.withdraw();r.attributes('-topmost',True);"
                    "print(f.askdirectory(initialdir=sys.argv[1] or None,title='Save sprites to'))")
            try:
                res = subprocess.run([sys.executable, "-c", code, start],
                                     capture_output=True, text=True, timeout=300)
                path = res.stdout.strip().replace("/", os.sep)
            except Exception:
                path = ""
            return self._send(200, path)
        if u.path == "/fetch":
            try:
                data = self._fetch(parse_qs(u.query)["url"][0])
            except Exception as e:
                return self._send(502, str(e))
            return self._send(200, data, "image/png")
        self._send(404, "not found")

    def do_POST(self):
        u = urlparse(self.path)
        if u.path != "/save":
            return self._send(404, "not found")
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if q.get("kind") == "url":
                data = self._fetch(q["url"])
            else:
                data = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            img = Image.open(io.BytesIO(data)).convert("RGBA")
            name = "".join(ch for ch in (q.get("name") or "sheet") if ch.isalnum() or ch in "-_.") or "sheet"
            out, n, total = slice_sheet(
                img, name, Path(q.get("out") or OUT), int(q.get("cols") or 8),
                int(q.get("tw") or 0) or None, int(q.get("th") or 0) or None,
                q.get("trim") == "1", q.get("empty") == "1")
            self._send(200, f"Saved {n}/{total} sprites to {out.resolve()}")
        except Exception as e:
            self._send(500, f"Error: {e}")


def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--out", default="Sprites")
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    OUT = Path(a.out)
    url = f"http://127.0.0.1:{a.port}"
    print(f"Slicer UI on {url}  (output: {OUT.resolve()})")
    if not a.no_browser:
        webbrowser.open(url)
    ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()


if __name__ == "__main__":
    main()
