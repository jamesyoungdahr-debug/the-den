import QtQuick

// Initial-in-a-circle avatar (the web's .holt-avatar).
Rectangle {
    property string initial: "?"
    property int size: Theme.avatar
    width: size; height: size; radius: size / 2
    color: Theme.currentTint
    border.width: 1
    border.color: Theme.current
    Text { anchors.centerIn: parent; text: initial; font.family: Theme.fontCore; font.weight: Font.Black; font.pixelSize: Math.round(size * 0.42); color: Theme.ink }
}
