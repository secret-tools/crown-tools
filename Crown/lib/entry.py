"""Application entry point shared by all launch methods."""
import argparse
from .deps import bootstrap
from .localization import LANGUAGES

def run_crown(argv=None):
    parser = argparse.ArgumentParser(description='Crown-Tools')
    parser.add_argument('--no-boot', action='store_true')
    parser.add_argument('--tool', help='Tool identifier; see --list-tools')
    parser.add_argument('--lang', choices=tuple(LANGUAGES))
    parser.add_argument('--list-tools', action='store_true')
    args = parser.parse_args(argv)
    bootstrap()
    from .update_check import require_current_version
    if not require_current_version(args.lang):
        return
    from .constants import ensure_data_dirs
    ensure_data_dirs()
    from .pages import TOOL_IDS
    if args.list_tools:
        for key, (category, name) in TOOL_IDS.items():
            print(f'{key:24} {category} / {name}')
        return
    if args.tool and args.tool not in TOOL_IDS:
        parser.error('Unknown tool: ' + args.tool)
    from .ui import CrownApp
    CrownApp(boot=not args.no_boot and (not args.tool), initial_tool=TOOL_IDS.get(args.tool), language=args.lang, welcome_links=True).run()
