from __future__ import annotations

import sys

from app.bootstrap import create_application
from app.composition import build_services
from ui.main_window import MainWindow


def main() -> int:
    app = create_application(sys.argv)
    window = MainWindow(build_services())
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
