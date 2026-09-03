"""Start the private reader once and open its local page."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

URL='http://127.0.0.1:8765/'
HERE=Path(__file__).resolve().parent
def check():
    with urllib.request.urlopen(URL+'api/status',timeout=2) as response:
        data=json.load(response)
    if data.get('application')!='d2r-treasure-vault':raise RuntimeError('Port 8765 is being used by another application.')
    return data
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--no-browser',action='store_true');args=parser.parse_args()
    try: status=check()
    except (urllib.error.URLError,TimeoutError,ConnectionError):
        runtime=HERE/'.runtime';runtime.mkdir(exist_ok=True)
        with (runtime/'reader.log').open('ab') as log:
            flags=(subprocess.CREATE_NO_WINDOW|subprocess.DETACHED_PROCESS) if os.name=='nt' else 0
            process=subprocess.Popen([sys.executable,str(HERE/'server.py')],cwd=str(HERE),stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=flags,start_new_session=os.name!='nt')
        status=None
        for _ in range(30):
            time.sleep(.3)
            if process.poll() is not None:raise RuntimeError('The stash reader could not start. See live/.runtime/reader.log.')
            try:status=check();break
            except (urllib.error.URLError,TimeoutError,ConnectionError):pass
        if status is None:raise RuntimeError('Timed out starting the stash reader. See live/.runtime/reader.log.')
    print(URL,flush=True)
    if not args.no_browser:webbrowser.open(URL)
if __name__=='__main__':
    try:main()
    except Exception as exc:print(str(exc),file=sys.stderr);sys.exit(1)
