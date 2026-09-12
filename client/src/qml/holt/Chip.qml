import QtQuick
import QtQuick.Controls as Controls

// Filter / tab pill. `on` = selected.
Controls.AbstractButton {
    id: chip
    property bool on: false
    property string badge: ""

    implicitHeight: 30
    leftPadding: 12
    rightPadding: 12
    hoverEnabled: true

    contentItem: Row {
        spacing: 8
        Text {
            text: chip.text
            font.family: Theme.fontCore
            font.pixelSize: 13
            font.weight: Font.Bold
            color: chip.on ? Theme.ink : Theme.ink70
            anchors.verticalCenter: parent.verticalCenter
        }
        Rectangle {
            visible: chip.badge !== ""
            width: badgeText.implicitWidth + 10; height: 18; radius: 9
            color: Theme.current
            anchors.verticalCenter: parent.verticalCenter
            Text { id: badgeText; anchors.centerIn: parent; text: chip.badge; font.family: Theme.fontMono; font.pixelSize: 10; color: Theme.deep }
        }
    }

    background: Rectangle {
        radius: Theme.radiusPill
        color: chip.on ? Theme.currentTint : (chip.hovered ? Theme.glassHighlight : "transparent")
        border.width: 1
        border.color: chip.on ? Theme.current : Theme.glassBorder
    }
}
