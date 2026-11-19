"""RISD yearbook local server. Google tokens and source files stay server-side."""
import io, os, re, secrets, tempfile, time
from pathlib import Path
from urllib.parse import urlencode
import requests
from flask import Flask, abort, jsonify, redirect, request, send_file, session
from PIL import Image, ImageOps
import numpy as np
import tifffile
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__, static_folder='static', static_url_path='')
app.secret_key = os.getenv('SECRET_KEY', 'local-development-only-change-me')
app.config.update(MAX_CONTENT_LENGTH=150*1024*1024, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE')=='1')
STORE = {}  # process-local; deploy with a shared encrypted session store
API='https://www.googleapis.com/drive/v3/files'
SCOPES='https://www.googleapis.com/auth/drive'

def state():
    sid=session.get('sid')
    if not sid:
        sid=secrets.token_urlsafe(32); session['sid']=sid
    return STORE.setdefault(sid, {})

def configured():
    return all(os.getenv(k) for k in ('GOOGLE_CLIENT_ID','GOOGLE_CLIENT_SECRET','GOOGLE_PICKER_API_KEY','GOOGLE_APP_ID','GOOGLE_REDIRECT_URI','ALLOWED_FOLDER_ID'))

def headers():
    s=state(); token=s.get('token')
    if not token: abort(401, 'Please connect Google Drive first')
    if time.time() > s.get('expires',0)-60:
        refresh=s.get('refresh')
        if not refresh: abort(401, 'Google authorization expired; reconnect')
        r=requests.post('https://oauth2.googleapis.com/token',data={'client_id':os.environ['GOOGLE_CLIENT_ID'],'client_secret':os.environ['GOOGLE_CLIENT_SECRET'],'refresh_token':refresh,'grant_type':'refresh_token'},timeout=30); r.raise_for_status(); data=r.json(); s.update(token=data['access_token'],expires=time.time()+data['expires_in']); token=data['access_token']
    return {'Authorization':'Bearer '+token}

def metadata(file_id):
    r=requests.get(f'{API}/{file_id}',headers=headers(),params={'fields':'id,name,parents,mimeType,trashed','supportsAllDrives':'true'},timeout=30); r.raise_for_status(); return r.json()

def authorized(file_id):
    # Traverse all parent links; reject files outside the configured tree.
    root=os.environ.get('ALLOWED_FOLDER_ID',''); todo=[file_id]; seen=set()
    while todo and len(seen)<100:
        f=todo.pop()
        if f==root and root: return True
        if f in seen: continue
        seen.add(f); info=metadata(f)
        if info.get('trashed'): return False
        todo.extend(info.get('parents',[]))
    return False

def safe_name(name, number):
    if not re.fullmatch(r'[1-9][0-9]*',str(number)): raise ValueError('Enter a positive whole number.')
    name=Path(name.replace('\\','/')).name
    stem=name.rsplit('.',1)[0] if '.' in name else name
    if not stem or len(stem)>180: raise ValueError('Invalid source filename')
    return f'{number}_{stem}.tif'

def preview(data, filename):
    ext=Path(filename).suffix.lower()
    if ext in {'.raw','.cr2','.cr3','.nef','.arw','.dng','.raf','.rw2','.orf'}:
        import rawpy
        with tempfile.NamedTemporaryFile(suffix=ext) as f:
            f.write(data); f.flush()
            with rawpy.imread(f.name) as raw: arr=raw.postprocess(output_bps=8, use_camera_wb=True, no_auto_bright=False)
        img=Image.fromarray(arr)
    else:
        img=ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert('RGB')
    img.thumbnail((2400,2400)); out=io.BytesIO(); img.save(out,'PNG'); return out.getvalue()

@app.get('/')
def index(): return app.send_static_file('index.html')
@app.get('/api/config')
def config(): return jsonify(configured=configured(),apiKey=os.getenv('GOOGLE_PICKER_API_KEY',''),appId=os.getenv('GOOGLE_APP_ID',''),connected=bool(state().get('token')))
@app.get('/oauth/start')
def oauth_start():
    if not configured(): abort(503,'Google Cloud settings are not configured')
    nonce=secrets.token_urlsafe(32); session['oauth_state']=nonce
    return redirect('https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({'client_id':os.environ['GOOGLE_CLIENT_ID'],'redirect_uri':os.environ['GOOGLE_REDIRECT_URI'],'response_type':'code','scope':SCOPES,'access_type':'offline','prompt':'consent','state':nonce}))
@app.get('/oauth/callback')
def oauth_callback():
    if not secrets.compare_digest(request.args.get('state',''),session.pop('oauth_state','!')): abort(400,'Invalid OAuth state')
    r=requests.post('https://oauth2.googleapis.com/token',data={'code':request.args.get('code',''),'client_id':os.environ['GOOGLE_CLIENT_ID'],'client_secret':os.environ['GOOGLE_CLIENT_SECRET'],'redirect_uri':os.environ['GOOGLE_REDIRECT_URI'],'grant_type':'authorization_code'},timeout=30); r.raise_for_status(); d=r.json(); state().update(token=d['access_token'],refresh=d.get('refresh_token'),expires=time.time()+d['expires_in']); return redirect('/#drive-connected')
@app.get('/api/picker-token')
def picker_token(): return jsonify(token=headers()['Authorization'][7:])
@app.post('/api/drive/select')
def select():
    file_id=(request.json or {}).get('id','')
    if not re.fullmatch(r'[\w-]{1,200}',file_id) or not authorized(file_id): abort(403,'File is outside the permitted Yearbook folder')
    m=metadata(file_id)
    if not m.get('parents') or m.get('mimeType')=='application/vnd.google-apps.folder': abort(400,'Choose a photo file')
    r=requests.get(f'{API}/{file_id}',headers=headers(),params={'alt':'media','supportsAllDrives':'true'},timeout=120); r.raise_for_status()
    if len(r.content)>150*1024*1024: abort(413)
    image=preview(r.content,m['name']); state()['selected']={'id':file_id,'name':m['name'],'parent':m['parents'][0]}; return jsonify(name=m['name'],preview='/api/preview?'+secrets.token_hex(4),image=image.hex())
@app.post('/api/preview-local')
def local_preview():
    f=request.files.get('photo')
    if not f: abort(400,'Choose a photo')
    return send_file(io.BytesIO(preview(f.read(),f.filename)),mimetype='image/png')
@app.post('/api/export')
def export():
    number=request.form.get('number',''); source=request.form.get('name',''); mode=request.form.get('mode','demo')
    s=state(); selected=s.get('selected')
    if mode=='drive':
        if not selected or not authorized(selected['id']) or not authorized(selected['parent']): abort(403,'Selected file is no longer accessible')
        source=selected['name']
    try: name=safe_name(source,number)
    except ValueError as e: abort(400,str(e))
    f=request.files.get('composite')
    if not f: abort(400,'Missing composite')
    img=Image.open(f.stream).convert('RGB'); arr=np.asarray(img,dtype=np.uint8)
    out=io.BytesIO(); tifffile.imwrite(out,arr,photometric='rgb',compression='deflate',metadata=None); data=out.getvalue()
    if mode!='drive': return send_file(io.BytesIO(data),mimetype='image/tiff',as_attachment=True,download_name=name)
    # Never update existing files. Resolve a collision by appending a number.
    parent=selected['parent']; stem=name[:-4]; candidate=name
    for n in range(1,1000):
        q="'%s' in parents and trashed = false and name = '%s'"%(parent.replace("'","\\'"),candidate.replace('\\','\\\\').replace("'","\\'"))
        r=requests.get(API,headers=headers(),params={'q':q,'fields':'files(id,name)','supportsAllDrives':'true','includeItemsFromAllDrives':'true'},timeout=30); r.raise_for_status()
        if not r.json().get('files'): break
        candidate=f'{stem} ({n+1}).tif'
    else: abort(409,'Too many matching filenames')
    import json
    r=requests.post('https://www.googleapis.com/upload/drive/v3/files',headers=headers(),params={'uploadType':'multipart','supportsAllDrives':'true','fields':'id,name'},files={'metadata':('metadata',json.dumps({'name':candidate,'parents':[parent]}),'application/json; charset=UTF-8'),'file':(candidate,data,'image/tiff')},timeout=180); r.raise_for_status(); return jsonify(r.json())

if __name__=='__main__': app.run(host='127.0.0.1',port=5000,debug=False)
