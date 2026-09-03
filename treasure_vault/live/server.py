"""Loopback-only stash viewer. The source connection is always read-only."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
from urllib.parse import urlsplit

HERE=Path(os.environ.get('D2R_VAULT_APP_DIR',Path(__file__).resolve().parent))
SUPPORT=Path(os.environ.get('D2R_VAULT_SUPPORT_DIR',HERE.parent/'support'))
RUNTIME=Path(os.environ.get('D2R_VAULT_RUNTIME_DIR',HERE/'.runtime'))
DEFAULT_DB=Path(os.environ.get('D2R_DEFAULT_DB','__select_inventory__.db'))
DEFAULT_ASSETS=Path(os.environ.get('D2R_DEFAULT_ASSETS',DEFAULT_DB.with_name('item_assets.db')))
UTC=lambda:datetime.now(timezone.utc).isoformat(timespec='seconds')
SETTINGS=RUNTIME/'settings.json'

def source_id(path):
    return hashlib.sha256(str(Path(path).resolve()).casefold().encode()).hexdigest()[:20]

def validate_database(value):
    path=Path(value).expanduser()
    if not path.is_absolute() or path.suffix.lower()!='.db' or not path.is_file():
        raise ValueError('Choose an existing .db file using its full path.')
    required={'account_id','char_name','unit_id','snapshot_ts','stash_type','item_name','base_name','item_type','quality','unique_set_id','identified','ethereal','stats_json','skills_json','stack_count','grid_x','grid_y','is_runeword','runeword_name','socketed_runes'}
    try:
        with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=3)) as connection:
            connection.execute('PRAGMA query_only=ON')
            columns={r[1] for r in connection.execute('PRAGMA table_info(stash_items)')}
            if not required.issubset(columns):raise ValueError('This database does not contain a compatible stash_items table. Choose your D2R Manager items.db.')
    except sqlite3.Error as exc:raise ValueError('The selected file could not be read as a SQLite inventory database.') from exc
    return path.resolve()

def pick_database(directory):
    script="""Add-Type -AssemblyName System.Windows.Forms
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Title = 'Select your D2R Manager items.db'
$dialog.Filter = 'Inventory database (items.db)|items.db|SQLite databases (*.db)|*.db'
$dialog.CheckFileExists = $true
$dialog.RestoreDirectory = $true
$dialog.InitialDirectory = $env:VAULT_PICKER_DIR
try { if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $dialog.FileName } } finally { $dialog.Dispose() }
"""
    result=subprocess.run(['powershell.exe','-NoProfile','-STA','-WindowStyle','Hidden','-Command',script],env={**os.environ,'VAULT_PICKER_DIR':str(directory)},capture_output=True,text=True,encoding='utf-8-sig',timeout=180,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    if result.returncode:raise RuntimeError('The file picker could not open. Paste the full database path instead.')
    return result.stdout.strip()

def capture_stash(path):
    with closing(sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=3)) as connection:
        connection.execute('PRAGMA query_only=ON')
        connection.row_factory=sqlite3.Row
        connection.execute('BEGIN')
        rows=[dict(row) for row in connection.execute('SELECT * FROM stash_items ORDER BY account_id,char_name,unit_id')]
    encoded=json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    return rows,hashlib.sha256(encoded).hexdigest()

def assemble_payload(directory):
    data=json.loads((directory/'support/browser-data.json').read_text(encoding='utf-8'))
    post=(directory/'d2jsp_organized_draft.txt').read_text(encoding='utf-8')
    data['postHeader']=post[:post.index('[/center]')+len('[/center]')]
    data['sectionHeaders']={}
    names={item['name']:item for item in data['items']}
    for line in post.splitlines():
        match=re.match(r'^\[b\](?:\d+ · )?(.+?)\[/b\](?: —|$)',line)
        if match and match[1] in names: names[match[1]]['postLine']=line
    for category in dict.fromkeys(item['category'] for item in data['items']):
        path=directory/'category-drafts'/(category.lower().replace(',','').replace(' ','-')+'.txt')
        text=path.read_text(encoding='utf-8')
        data['sectionHeaders'][category]=text.split('[/center]',1)[1].strip().split('\n\n',1)[0]
    if not all(item.get('postLine') and item.get('key') for item in data['items']):
        raise ValueError('An item is missing its export line or stable selection key')
    if len({item['key'] for item in data['items']})!=len(data['items']):
        raise ValueError('Selection keys must be unique')
    return data

def compile_inventory(rows,output,assets=DEFAULT_ASSETS,include_inventory=False):
    output=Path(output); work=output/'support'; work.mkdir(parents=True,exist_ok=True)
    for reference in SUPPORT.glob('*.txt'):
        target=work/reference.name
        if not target.exists() or target.stat().st_mtime_ns!=reference.stat().st_mtime_ns:
            shutil.copy2(reference,target)
    captured=output/'captured-stash.json'
    captured.write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8')
    env={**os.environ,'D2R_OUTPUT_DIR':str(output),'D2R_INPUT_JSON':str(captured),'D2R_ASSETS_DB':str(assets),'D2R_INCLUDE_INVENTORY':'1' if include_inventory else '0'}
    for script in ['organize.py','polish.py']:
        command=[sys.executable,'--pipeline',script] if getattr(sys,'frozen',False) else [sys.executable,str(SUPPORT/script)]
        result=subprocess.run(command,env=env,capture_output=True,text=True,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        if result.returncode:
            raise RuntimeError(f'{script} failed: {result.stderr[-2000:]}')
    return assemble_payload(output)

class InventoryState:
    def __init__(self,database,assets,output,interval=5,include_inventory=True,settings_path=None):
        self.database=Path(database); self.assets=Path(assets); self.output=Path(output)
        self.interval=interval; self.lock=threading.Lock(); self.sync_lock=threading.Lock()
        self.include_inventory=include_inventory
        self.settings_path=settings_path; self.picker_lock=threading.Lock()
        self.version=None; self.payload=None; self.encoded=None
        self.error=None; self.checked=None; self.updated=None; self.source_time=None; self.refreshing=False
        self.wakeup=threading.Event(); self.stop=threading.Event()
    def status(self):
        with self.lock:
            return {'application':'d2r-treasure-vault','version':self.version,'ready':self.payload is not None,
                    'refreshing':self.refreshing,'error':self.error,'lastChecked':self.checked,
                    'lastUpdated':self.updated,'sourceCaptured':self.source_time,'pollSeconds':self.interval,
                    'listings':len(self.payload['items']) if self.payload else 0,'sourceId':source_id(self.database),'databasePath':str(self.database),
                    'instanceId':source_id(self.output.parent),'needsSetup':self.payload is None and not self.database.is_file()}
    def settings(self):
        with self.lock:return {'databasePath':str(self.database),'assetsPath':str(self.assets),'needsSetup':self.payload is None and not self.database.is_file()}
    def switch_database(self,value):
        path=validate_database(value)
        with self.sync_lock:
            with self.lock:self.refreshing=True
            try:
                assets=path.with_name('item_assets.db')
                if not assets.is_file():assets=DEFAULT_ASSETS
                rows,digest=capture_stash(path)
                data=compile_inventory(rows,self.output.parent/'switch-build',assets,include_inventory=self.include_inventory)
                version=source_id(path)+':'+digest; timestamp=UTC()
                data.update(version=version,sourceId=source_id(path),legacySourceId=source_id(DEFAULT_DB),databasePath=str(path),updatedAt=timestamp,sourceCaptured=max((r['snapshot_ts'] for r in rows),default=None))
                encoded=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode('utf-8')
                if self.settings_path:
                    config=Path(self.settings_path);config.parent.mkdir(parents=True,exist_ok=True)
                    temporary=config.with_suffix('.tmp');temporary.write_text(json.dumps({'databasePath':str(path),'assetsPath':str(assets)}),encoding='utf-8');temporary.replace(config)
                with self.lock:
                    self.database=path;self.assets=assets;self.payload=data;self.encoded=encoded;self.version=version
                    self.updated=timestamp;self.source_time=data['sourceCaptured'];self.error=None;self.checked=timestamp
            finally:
                with self.lock:self.refreshing=False
        return self.settings()
    def refresh(self):
        if not self.sync_lock.acquire(blocking=False): return
        try:
            with self.lock: self.refreshing=True
            if self.database==DEFAULT_DB and not self.database.is_file() and self.payload is None:
                with self.lock:self.checked=UTC();self.error=None
                return
            rows,version=capture_stash(self.database)
            version=source_id(self.database)+':'+version
            if version!=self.version:
                data=compile_inventory(rows,self.output,self.assets,include_inventory=self.include_inventory)
                timestamp=UTC(); data['version']=version; data['updatedAt']=timestamp
                data['sourceId']=source_id(self.database);data['legacySourceId']=source_id(DEFAULT_DB);data['databasePath']=str(self.database)
                data['sourceCaptured']=max((r['snapshot_ts'] for r in rows),default=None)
                encoded=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode('utf-8')
                with self.lock:
                    self.payload=data; self.encoded=encoded; self.version=version
                    self.updated=timestamp; self.source_time=data['sourceCaptured']
            with self.lock: self.error=None; self.checked=UTC()
        except Exception as exc:
            print(f'[{UTC()}] Refresh failed: {exc}',file=sys.stderr,flush=True)
            with self.lock:
                self.error='Could not read the stash. Last successful inventory is retained. Check that the database is available.'
                self.checked=UTC()
        finally:
            with self.lock: self.refreshing=False
            self.sync_lock.release()
    def watch(self):
        while not self.stop.is_set():
            self.refresh()
            self.wakeup.wait(self.interval); self.wakeup.clear()

def handler_for(state,port):
    allowed={f'127.0.0.1:{port}',f'localhost:{port}'}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,format,*args): pass
        def permitted(self):
            if self.headers.get('Host','') not in allowed:
                self.send_error(403,'Loopback host required'); return False
            origin=self.headers.get('Origin')
            if origin and origin not in {f'http://{host}' for host in allowed}:
                self.send_error(403,'Same-origin access required'); return False
            return True
        def reply(self,body,content_type='application/json',status=200,etag=None):
            self.send_response(status)
            self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            if etag:self.send_header('ETag',f'"{etag}"')
            self.end_headers(); self.wfile.write(body)
        def do_GET(self):
            if not self.permitted(): return
            route=urlsplit(self.path).path
            if route=='/api/status': self.reply(json.dumps(state.status()).encode()); return
            if route=='/api/settings':self.reply(json.dumps(state.settings()).encode());return
            if route=='/api/inventory':
                with state.lock: content=state.encoded; version=state.version
                if content is None:self.reply(b'{"error":"Loading stash"}',status=503)
                else:self.reply(content,etag=version)
                return
            files={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/theme.css':('theme.css','text/css; charset=utf-8'),'/logic.js':('logic.js','text/javascript; charset=utf-8'),'/features.js':('features.js','text/javascript; charset=utf-8')}
            if route not in files:self.send_error(404); return
            filename,mime=files[route]
            self.reply((HERE/filename).read_bytes(),mime)
        def do_POST(self):
            if not self.permitted(): return
            route=urlsplit(self.path).path
            if route=='/api/shutdown' and os.environ.get('D2R_ENABLE_SHUTDOWN')=='1':
                if self.headers.get('Content-Type','').split(';')[0]!='application/json':self.send_error(415);return
                self.reply(b'{"stopped":true}');state.stop.set();state.wakeup.set()
                threading.Thread(target=self.server.shutdown,daemon=True).start();return
            if route in {'/api/settings','/api/settings/pick'}:
                if self.headers.get('Content-Type','').split(';')[0]!='application/json':self.send_error(415);return
                try:
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<size<=8192:raise ValueError('Invalid settings request size.')
                    body=json.loads(self.rfile.read(size))
                    if not isinstance(body,dict):raise ValueError('Invalid settings request.')
                    if route.endswith('/pick'):
                        if not state.picker_lock.acquire(blocking=False):raise ValueError('The file picker is already open.')
                        try:result={'path':pick_database(state.database.parent)}
                        finally:state.picker_lock.release()
                    else:result=state.switch_database(str(body.get('databasePath','')))
                    self.reply(json.dumps(result).encode())
                except (ValueError,RuntimeError,sqlite3.Error,subprocess.TimeoutExpired,OSError) as exc:
                    message=str(exc) if isinstance(exc,ValueError) else 'Could not load this database or open the picker. Your current inventory remains active. You can paste the full path instead.'
                    self.reply(json.dumps({'error':message}).encode(),status=400)
                return
            if route!='/api/refresh':self.send_error(404);return
            state.wakeup.set();self.reply(b'{"queued":true}',status=202)
    return Handler

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--database',type=Path)
    parser.add_argument('--assets',type=Path)
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    try:saved=json.loads(SETTINGS.read_text(encoding='utf-8'))
    except (OSError,ValueError):saved={}
    if not isinstance(saved,dict):saved={}
    database=args.database or Path(saved.get('databasePath',DEFAULT_DB))
    assets=args.assets or (database.with_name('item_assets.db') if database.with_name('item_assets.db').is_file() else DEFAULT_ASSETS)
    state=InventoryState(database,assets,RUNTIME/'build',settings_path=SETTINGS)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),handler_for(state,args.port))
    threading.Thread(target=state.watch,daemon=True).start()
    print(f'Treasure Vault running at http://127.0.0.1:{args.port}/',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: state.stop.set();state.wakeup.set();server.server_close()

if __name__=='__main__':main()
