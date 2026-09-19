"""Loopback-only Motion Studio server. Standard library + local FFmpeg."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import argparse,json,os,shutil,subprocess,secrets,threading,time,urllib.parse,webbrowser,struct
ROOT=Path(__file__).resolve().parent
EXPORTS=ROOT/'exports';EXPORTS.mkdir(exist_ok=True)
TOKEN=secrets.token_urlsafe(32)
FFMPEG=shutil.which('ffmpeg')
jobs={};lock=threading.Lock()
def result(j):
 return {k:j[k] for k in ['id','state','frames','total','width','height','fps','duration','error']}|{'url':'/exports/'+j['id']+'.mp4' if j['state']=='done' else None}
def stop(j):
 if j['proc'].poll() is None:
  j['proc'].terminate()
  try:j['proc'].wait(timeout=5)
  except subprocess.TimeoutExpired:j['proc'].kill();j['proc'].wait()
 try:j['proc'].stdin.close()
 except Exception:pass
 j['log'].close()
def finish(j):
 try:
  j['proc'].stdin.close()
  code=j['proc'].wait(timeout=180)
  j['log'].close()
  if j['state']=='cancelled':return
  if code or not j['path'].is_file() or j['path'].stat().st_size<100:
   raise RuntimeError('動画エンコードに失敗しました。ログを確認してください。')
  j['state']='done'
 except Exception as e:
  j['error']=str(e);j['state']='error';stop(j)
class Handler(SimpleHTTPRequestHandler):
 protocol_version='HTTP/1.1'
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT),**kw)
 def log_message(self,*a):pass
 def allowed(self):
  return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
 def reply(self,data,status=200):
  payload=json.dumps(data,ensure_ascii=False).encode('utf-8');self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(payload)
 def do_GET(self):
  if not self.allowed():return self.reply({'error':'Invalid host'},403)
  p=urllib.parse.urlparse(self.path).path
  if p=='/api/info':return self.reply({'token':TOKEN,'ffmpeg':bool(FFMPEG),'outputFolder':str(EXPORTS),'version':1})
  if p.startswith('/api/export/'):
   j=jobs.get(p.rsplit('/',1)[-1]);return self.reply(result(j) if j else {'error':'書き出しが見つかりません'},200 if j else 404)
  path=Path(self.translate_path(self.path)).resolve()
  if not path.is_relative_to(ROOT) or (p not in ['/', '/index.html','/app.js','/renderer.js','/style.css'] and not p.startswith(('/assets/','/exports/'))):
   return self.reply({'error':'Not found'},404)
  if path.is_dir() and p!='/':return self.reply({'error':'Not found'},404)
  super().do_GET()
 def do_POST(self):
  origin=self.headers.get('Origin')
  if not self.allowed() or self.headers.get('X-Studio-Token')!=TOKEN or (origin and origin not in {f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}):
   return self.reply({'error':'操作元を確認できません。画面を再読み込みしてください。'},403)
  try:
   size=int(self.headers.get('Content-Length','0'))
   if not 0<=size<=12*1024*1024:raise ValueError('リクエストが大きすぎます')
   raw=self.rfile.read(size);p=urllib.parse.urlparse(self.path);bits=p.path.strip('/').split('/')
   if p.path=='/api/export':
    if not FFMPEG:raise ValueError('FFmpegが見つかりません。インストール後にアプリを再起動してください。')
    a=json.loads(raw);w=int(a['width']);h=int(a['height']);fps=int(a['fps']);duration=float(a['duration'])
    if (w,h) not in [(1280,720),(1920,1080)] or fps not in [24,30,60] or not 1<=duration<=60:raise ValueError('書き出し設定が範囲外です')
    with lock:
     if any(j['state'] in ['receiving','encoding'] for j in jobs.values()):return self.reply({'error':'別の書き出しが進行中です'},409)
     jid=time.strftime('%Y%m%d_%H%M%S')+'_'+secrets.token_hex(3);path=EXPORTS/(jid+'.mp4');log=open(EXPORTS/(jid+'.log'),'wb')
     proc=subprocess.Popen([FFMPEG,'-hide_banner','-loglevel','error','-y','-f','image2pipe','-vcodec','mjpeg','-framerate',str(fps),'-i','pipe:0','-an','-vf',f'scale={w}:{h}:flags=lanczos,setsar=1','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(path)],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
     j={'id':jid,'state':'receiving','frames':0,'total':round(fps*duration),'width':w,'height':h,'fps':fps,'duration':duration,'error':None,'proc':proc,'log':log,'path':path,'last':time.time(),'guard':threading.Lock()};jobs[jid]=j
    return self.reply(result(j))
   if len(bits)!=4 or bits[:2]!=['api','export']:return self.reply({'error':'Not found'},404)
   j=jobs.get(bits[2]);action=bits[3]
   if not j:return self.reply({'error':'書き出しが見つかりません'},404)
   with j['guard']:
    j['last']=time.time()
    if action=='cancel':
     if j['state'] in ['receiving','encoding']:j['state']='cancelled';stop(j)
     return self.reply(result(j))
    if j['state']!='receiving':return self.reply({'error':'この書き出しは受信を終了しています'},409)
    if action=='frame':
     idx=int(urllib.parse.parse_qs(p.query).get('index',['-1'])[0])
     if idx!=j['frames'] or idx>=j['total']:raise ValueError('フレームの順番が一致しません')
     if not(raw.startswith(b'\xff\xd8') and raw.endswith(b'\xff\xd9')):raise ValueError('画像データが不正です')
     try:j['proc'].stdin.write(raw);j['proc'].stdin.flush()
     except (BrokenPipeError,OSError):j['state']='error';j['error']='FFmpegが終了しました。保存先のログを確認してください。';stop(j);return self.reply(result(j),500)
     j['frames']+=1;return self.reply({'frames':j['frames']})
    if action=='finish':
     if j['frames']!=j['total']:raise ValueError('フレーム数が不足しています')
     j['state']='encoding';threading.Thread(target=finish,args=(j,),daemon=True).start();return self.reply(result(j))
    return self.reply({'error':'Not found'},404)
  except (ValueError,KeyError,TypeError,json.JSONDecodeError) as e:self.reply({'error':str(e)},400)
  except Exception as e:self.reply({'error':str(e)},500)
def cleanup():
 while True:
  time.sleep(10)
  for j in list(jobs.values()):
   if j['state']=='receiving' and time.time()-j['last']>90:
    with j['guard']:j['state']='cancelled';j['error']='画面との接続が途切れたため書き出しを停止しました';stop(j)
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--open',action='store_true');parser.add_argument('--port',type=int,default=8877);a=parser.parse_args()
 try:server=ThreadingHTTPServer(('127.0.0.1',a.port),Handler)
 except OSError:
  if a.open:webbrowser.open(f'http://127.0.0.1:{a.port}')
  return
 threading.Thread(target=cleanup,daemon=True).start()
 if a.open:webbrowser.open(f'http://127.0.0.1:{a.port}')
 print(f'Motion Studio: http://127.0.0.1:{a.port}',flush=True)
 server.serve_forever()
if __name__=='__main__':main()
