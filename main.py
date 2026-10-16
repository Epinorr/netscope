"""NetScope application entry point, including the tightly-scoped UAC repair helper."""
from __future__ import annotations

import sys


def _run_elevated_helper(argv: list[str]) -> int | None:
    if "--run-elevated-fix" not in argv:
        return None
    try:
        index = argv.index("--run-elevated-fix")
        fix_ids_raw = argv[index + 1]
        output_index = argv.index("--result-file")
        output_path = argv[output_index + 1]
    except (ValueError, IndexError):
        return 2

    # Import only after validating that this is the explicit helper entry point.
    from netscope.repairs import execute_elevated_from_cli
    fix_ids = [fid.strip() for fid in fix_ids_raw.split(",") if fid.strip()]
    return execute_elevated_from_cli(fix_ids, output_path)


if __name__ == "__main__":
    helper_result = _run_elevated_helper(sys.argv[1:])
    if helper_result is not None:
        raise SystemExit(helper_result)
    from netscope.app import main
    main()