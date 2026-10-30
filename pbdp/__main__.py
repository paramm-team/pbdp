"""Read-only terminal inspection: python -m pbdp inspect FILE."""
import argparse
import json
from pathlib import Path

from . import Parser


def _mapping(entries, option):
    result = {}
    for entry in entries:
        key, separator, value = entry.partition('=')
        if not separator or not key.strip() or not value.strip():
            raise ValueError(f'{option} requires COLUMN=VALUE')
        key, value = key.strip(), value.strip()
        if key in result:
            raise ValueError(f'Duplicate {option} key: {key!r}')
        result[key] = value
    return result


def main(argv=None):
    cli = argparse.ArgumentParser(
        description='Inspect a battery export without saving.')
    commands = cli.add_subparsers(dest='command', required=True)
    inspect = commands.add_parser(
        'inspect', help='Print a JSON import inspection report')
    inspect.add_argument('source', type=Path)
    inspect.add_argument(
        '--cycler', default='', help='Vendor name or 1-based header line')
    inspect.add_argument(
        '--time-unit', action='append', default=[], metavar='COLUMN=UNIT')
    inspect.add_argument('--current-epsilon', type=float, default=.001, metavar='AMPS')
    inspect.add_argument(
        '--mode-column', help='Source column for explicit mode mapping')
    inspect.add_argument('--mode', action='append', default=[], metavar='VALUE=STATE',
                         help='Map a mode to charging, discharging or rest')
    inspect.add_argument(
        '--states', action='store_true', help='Include battery-state counts')
    args = cli.parse_args(argv)
    try:
        parser = Parser(
            time_units=_mapping(args.time_unit, '--time-unit') or None,
            current_epsilon=args.current_epsilon,
            current_mode_column=args.mode_column,
            current_mode_map=_mapping(args.mode, '--mode') or None,
        )
    except ValueError as exc:
        cli.error(str(exc))
    report = parser.inspect_file(
        args.source, cycler=args.cycler, state_option='yes' if args.states else '')
    print(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))
    return 0 if report['status'] == 'ok' else 1


if __name__ == '__main__':
    raise SystemExit(main())
