import QtQuick

// Small mono secondary text -- the web's .holt-meta.
Text {
    font.family: Theme.fontMono
    font.pixelSize: Theme.sizeMeta + 1
    color: Theme.ink42
    elide: Text.ElideRight
}
