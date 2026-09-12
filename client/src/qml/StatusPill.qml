import QtQuick
import QtQuick.Layouts

// Mirrors the web UI's .holt-pill: a mono-labeled dot. Teal ("healthy") only ever
// means online/healthy, never decoration -- same rule as the CSS version.
RowLayout {
    id: root
    property string label: ""
    property string tone: "idle"  // healthy | working | warning | idle

    readonly property var toneColor: ({
        healthy: Theme.healthy,
        working: Theme.current,
        warning: Theme.warning,
        idle: Theme.ink42,
    })[root.tone] || Theme.ink42

    readonly property var dotColor: ({
        healthy: Theme.healthy,
        working: Theme.current,
        warning: Theme.warning,
        idle: Theme.ink28,
    })[root.tone] || Theme.ink28

    spacing: 6

    Rectangle {
        width: 6
        height: 6
        radius: 3
        color: root.dotColor
        Layout.alignment: Qt.AlignVCenter
    }

    Text {
        text: root.label
        font.family: Theme.fontMono
        font.pixelSize: 11  // font.pixelSize is int in QML; CSS's 10.5px rounds here
        color: root.toneColor
    }
}
