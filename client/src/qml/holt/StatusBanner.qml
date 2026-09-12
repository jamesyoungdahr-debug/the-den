import QtQuick
import QtQuick.Layouts

// The one inline message every page uses instead of the old copy-pasted
// Connections + InlineMessage block. Call show(text, tone) with tone = positive |
// warning | error | info; hides itself after a while unless sticky.
Rectangle {
    id: banner
    property string tone: "info"
    property string message: ""
    property bool sticky: false

    function show(text, kind) {
        message = text
        tone = kind || "info"
        visible = true
        if (!sticky) hideTimer.restart()
    }
    function showError(text) { show(text, "error") }

    visible: false
    Layout.fillWidth: true
    implicitHeight: label.implicitHeight + 22
    radius: Theme.radiusMd
    color: tone === "positive" ? "#1A28E0C8" : tone === "warning" || tone === "error" ? "#1AFFB84D" : Theme.currentTint
    border.width: 1
    border.color: tone === "positive" ? Theme.healthy : tone === "warning" || tone === "error" ? Theme.warning : Theme.current

    Text {
        id: label
        anchors { fill: parent; margins: 11; leftMargin: 14 }
        text: banner.message
        font.family: Theme.fontCore
        font.pixelSize: 13
        color: Theme.ink
        wrapMode: Text.WordWrap
    }
    MouseArea { anchors.fill: parent; onClicked: banner.visible = false }
    Timer { id: hideTimer; interval: 6000; onTriggered: banner.visible = false }
}
