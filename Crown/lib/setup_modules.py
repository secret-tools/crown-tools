"""Install and verify the standard edition's dependencies."""
import importlib.util,importlib.metadata,subprocess,sys,threading,time,os,tempfile
from pathlib import Path

MODULES=('textual','rich','pyfiglet','psutil','arabic_reshaper','bidi','PIL','numpy','qrcode','requests','dns','charset_normalizer','phonenumbers','pypdf','zxingcpp','detect_secrets')

def dependencies_ready(requirements):
    try:
        for line in requirements.read_text(encoding='utf-8-sig').splitlines():
            line=line.strip()
            if not line or line.startswith('#'):continue
            name,expected=line.split('==',1)
            if importlib.metadata.version(name)!=expected:return False
        for name in MODULES:
            importlib.import_module(name)
        return True
    except (OSError,ValueError,ImportError,RuntimeError,importlib.metadata.PackageNotFoundError):return False

def install(requirements):
    log_dir=Path(os.environ.get('LOCALAPPDATA',tempfile.gettempdir()))/'CrownTools'/'logs'
    log_dir.mkdir(parents=True,exist_ok=True)
    log_path=log_dir/f'installation-{time.time_ns()}.log'
    finished=threading.Event()
    started=time.monotonic()
    def progress():
        while not finished.wait(5):
            print(f'Installing dependencies... {int(time.monotonic()-started)}s',flush=True)
    print('Installing dependencies. First installation may take a few minutes.',flush=True)
    worker=threading.Thread(target=progress,daemon=True)
    worker.start()
    try:
        with log_path.open('w',encoding='utf-8') as log:
            result=subprocess.run([sys.executable,'-m','pip','install','--disable-pip-version-check','--no-compile','--only-binary=:all:','--no-input','--timeout','30','--retries','2','-r',str(requirements)],stdout=log,stderr=subprocess.STDOUT)
    finally:
        finished.set()
        worker.join()
    if result.returncode:
        print(log_path.read_text(encoding='utf-8',errors='replace')[-6000:])
        print(f'Installation log: {log_path}')
    return result.returncode
def main():
    if sys.version_info < (3,12):
        print('Python 3.12+ required.');return 1
    requirements=Path(__file__).resolve().parents[1]/'requirements.txt'
    if dependencies_ready(requirements):return 0
    if '--check' in sys.argv[1:]:return 1
    status=install(requirements)
    if status:return status
    if not dependencies_ready(requirements):
        print('Dependency verification failed. Run setup.bat to repair the environment.');return 1
    print('Installation verified. Launch start.bat.');return 0
if __name__=='__main__':sys.exit(main())
