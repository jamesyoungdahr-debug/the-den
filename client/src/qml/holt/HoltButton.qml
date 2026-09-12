import QtQuick
import QtQuick.Controls as Controls

// The three web button kinds: primary (solid purple), secondary (glass), quiet (text).
Controls.Button {
    id: btn
    property string kind: "secondary"   // primary | secondary | quiet | danger
    property bool small: false

    implicitHeight: small ? 30 : 38
    leftPadding: small ? 12 : 16
    rightPadding: leftPadding
    hoverEnabled: true
    font.family: Theme.fontCore
    font.pixelSize: small ? 12 : Theme.sizeButton
    font.weight: Font.ExtraBold
    opacity: enabled ? 1 : 0.5

    contentItem: Text {
        text: btn.text
        font: btn.font
        color: btn.kind === "primary" ? Theme.deep : (btn.kind === "danger" ? Theme.warning : Theme.ink)
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: Theme.radiusMd
        color: btn.kind === "primary" ? (btn.hovered ? Theme.currentHover : Theme.current)
             : btn.kind === "quiet" ? (btn.hovered ? Theme.glassHighlightStrong : "transparent")
             : (btn.hovered ? Theme.glassSurfaceStrong : Theme.glassSurface)
        border.width: btn.kind === "secondary" || btn.kind === "danger" ? 1 : 0
        border.color: Theme.glassBorderStrong
        Behavior on color { ColorAnimation { duration: Theme.motionFast } }
    }
}
