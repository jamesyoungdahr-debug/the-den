"""Force-compiles SettingsPage.qml against a real SettingsController + backend, and
exercises a real save() to trigger onSaved (verifying its Connections handler, which
clears secret fields, has no scoping issues -- though this page has no ListView.header
at all so the M3 bug's precondition doesn't apply here, worth confirming empirically
anyway). Run under QT_QPA_PLATFORM=offscreen, no display needed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from models.settings_controller import SettingsController
from theme import Theme

app = QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()
controller = SettingsController(lambda: "http://127.0.0.1:8686")
theme = Theme()
engine.rootContext().setContextProperty("settingsController", controller)
engine.rootContext().setContextProperty("Theme", theme)

errors = []
engine.warnings.connect(lambda warnings: errors.extend(str(w) for w in warnings))

qml_file = Path(__file__).parent.parent / "src" / "qml" / "SettingsPage.qml"
engine.load(str(qml_file))

if not engine.rootObjects():
    print("FAIL: no root object created (compile/load error)")
    sys.exit(1)


def trigger_save():
    print(f"loaded qbitUrl: {controller.qbitUrl!r}")
    print("-- triggering a real save() to exercise onSaved --")
    controller.save("", controller.qbitUrl, controller.qbitUsername, "", controller.moviesRoot,
                     controller.tvRoot, controller.automationIntervalSeconds, "")


def finish():
    if errors:
        print(f"FAIL: {len(errors)} QML warning(s)/error(s): {errors}")
        sys.exit(1)
    print("Loaded OK, save() round-tripped with no scoping errors.")
    print("PASS")
    app.quit()


QTimer.singleShot(800, trigger_save)
QTimer.singleShot(2000, finish)
sys.exit(app.exec())
