import QtQuick

// Mono, uppercase, tracked section label -- the web's .holt-eyebrow.
Text {
    property bool accent: true
    font.family: Theme.fontMono
    font.pixelSize: Theme.sizeEyebrow
    font.letterSpacing: Theme.trackingEyebrow
    font.capitalization: Font.AllUppercase
    color: accent ? Theme.current : Theme.ink28
}
