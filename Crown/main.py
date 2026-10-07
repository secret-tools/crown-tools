"""Crown-Tools application launcher."""
from lib.entry import run_crown
if __name__ == '__main__':
    try:
        run_crown()
    except Exception:
        import sys
        import traceback
        from pathlib import Path
        from datetime import datetime
        report = traceback.format_exc()
        folder = Path(__file__).resolve().parent.parent / 'Output' / 'Logs'
        try:
            folder.mkdir(parents=True, exist_ok=True)
            log = folder / ('startup-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.log')
            log.write_text(report, encoding='utf-8')
            print('Startup error / Erreur au demarrage. Log: ' + str(log), file=sys.stderr)
        except OSError:
            pass
        print(report, file=sys.stderr)
        sys.exit(1)
