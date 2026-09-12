import QtQuick

// The reduced HoltOS mark: a ring. Mirrors the web UI's .den-ringmark.
Rectangle {
    id: root
    property int markSize: 30
    property color ringColor: Theme.current

    width: markSize
    height: markSize
    radius: markSize / 2
    color: "transparent"
    border.width: Math.max(2, Math.round(markSize * 0.23))
    border.color: ringColor
}
