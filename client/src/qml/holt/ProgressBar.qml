import QtQuick

// Thin drawn progress bar; `tone` picks the fill colour (processing purple or
// available teal). Value is 0..1.
Rectangle {
    id: bar
    property real value: 0
    property string tone: "processing"
    implicitHeight: 6
    radius: 3
    color: Theme.glassHighlightStrong
    Rectangle {
        height: parent.height
        width: Math.max(0, Math.min(1, bar.value)) * parent.width
        radius: 3
        color: bar.tone === "available" ? Theme.healthy : Theme.current
        Behavior on width { NumberAnimation { duration: Theme.motionBase } }
    }
}
