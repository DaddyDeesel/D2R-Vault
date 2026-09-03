"""Windows portable entry point. No inventory ships with the application."""
import argparse
import csv
import ctypes
import hashlib
import json
import os
from pathlib import Path
import runpy
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

VERSION='0.3'
BUNDLE=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
APP_HOME=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent

def configure(runtime):
    runtime.mkdir(parents=True,exist_ok=True)
    os.environ.update(D2R_VAULT_APP_DIR=str(BUNDLE/'live'),D2R_VAULT_SUPPORT_DIR=str(BUNDLE/'support'),D2R_VAULT_RUNTIME_DIR=str(runtime),D2R_DEFAULT_DB=str(runtime/'__select_inventory__.db'),D2R_DEFAULT_ASSETS=str(BUNDLE/'assets/item_assets.db'),D2R_ENABLE_SHUTDOWN='1')
    return runtime

def status(port):
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/status',timeout=2) as response:return json.load(response)

def check_instance(value,runtime):
    expected=hashlib.sha256(str(runtime.resolve()).casefold().encode()).hexdigest()[:20]
    if value.get('application')!='d2r-treasure-vault' or value.get('instanceId')!=expected:
        raise RuntimeError('This port belongs to another app or another copy of D2R Treasure Vault. Close that copy first.')

def log_streams(runtime):
    log=(runtime/'reader.log').open('a',encoding='utf-8',buffering=1)
    sys.stdout=log;sys.stderr=log

def self_test(destination):
    """Exercises the frozen worker against synthetic data, never a user's DB."""
    from server import compile_inventory,InventoryState,DEFAULT_DB,DEFAULT_ASSETS
    work=Path(destination).resolve();work.mkdir(parents=True,exist_ok=True)
    fields=dict(unit_id=1,profile_id='synthetic-profile',account_id='synthetic-account',char_name='TestMule',snapshot_ts='2026-09-02T00:00:00Z',txt_file_no=610,quality=2,unique_set_id=0,identified=1,ethereal=0,item_name='El Rune',base_name='El Rune',item_type='Rune',stash_type='advanced',grid_x=0,grid_y=0,stats_json='{}',skills_json='{}',base_defense=None,stack_count=12,container_unit_id=1,is_runeword=0,runeword_name=None,socketed_runes='[]',first_seen_at='',last_seen_at='')
    data=compile_inventory([fields],work/'synthetic',DEFAULT_ASSETS,include_inventory=True)
    assert len(data['items'])==1 and data['items'][0]['quantity']==12 and data['items'][0].get('image')
    state=InventoryState(DEFAULT_DB,DEFAULT_ASSETS,work/'first-run')
    state.refresh();assert state.status()['needsSetup'] and not state.status()['error']
    (work/'self-test.json').write_text(json.dumps({'version':VERSION,'passed':True,'syntheticListings':len(data['items']),'syntheticUnits':12,'artwork':True,'firstRun':True}),encoding='utf-8')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--server',action='store_true');parser.add_argument('--stop',action='store_true');parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--port',type=int,default=8766);parser.add_argument('--runtime',type=Path);parser.add_argument('--pipeline',choices=['organize.py','polish.py']);parser.add_argument('--self-test',type=Path)
    args=parser.parse_args()
    runtime=configure(args.runtime or Path(os.environ.get('D2R_VAULT_RUNTIME_DIR',APP_HOME/'user-data')))
    if args.pipeline:
        # Worker errors are captured by the local reader; no windowed stdout assumed.
        if sys.stdout is None:sys.stdout=open(os.devnull,'w')
        if sys.stderr is None:sys.stderr=open(os.devnull,'w')
        runpy.run_path(str(BUNDLE/'support'/args.pipeline),run_name='__main__');return
    if args.self_test:
        log_streams(runtime);self_test(args.self_test);return
    if args.server:
        log_streams(runtime)
        import server
        sys.argv=[sys.argv[0],'--port',str(args.port)]
        server.main();return
    try:current=status(args.port)
    except (urllib.error.URLError,TimeoutError,ConnectionError):current=None
    if current:check_instance(current,runtime)
    if args.stop:
        if current:
            request=urllib.request.Request(f'http://127.0.0.1:{args.port}/api/shutdown',data=b'{}',headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(request,timeout=5) as response:response.read()
        return
    if current is None:
        env={**os.environ,'PYINSTALLER_RESET_ENVIRONMENT':'1'}
        with (runtime/'launcher.log').open('ab') as log:
            child=subprocess.Popen([sys.executable,'--server','--port',str(args.port),'--runtime',str(runtime)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,env=env,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.DETACHED_PROCESS)
        for _ in range(60):
            if child.poll() is not None:raise RuntimeError('The reader did not start. See user-data/reader.log.')
            try:current=status(args.port);break
            except (urllib.error.URLError,TimeoutError,ConnectionError):time.sleep(.25)
        if current is None:raise RuntimeError('The reader took too long to start. See user-data/reader.log.')
        check_instance(current,runtime)
    if not args.no_browser:webbrowser.open(f'http://127.0.0.1:{args.port}/')

if __name__=='__main__':
    try:main()
    except Exception as error:
        if '--pipeline' in sys.argv or '--self-test' in sys.argv or '--server' in sys.argv:
            raise
        ctypes.windll.user32.MessageBoxW(None,str(error),'D2R Treasure Vault could not start',0x10)
        sys.exit(1)
