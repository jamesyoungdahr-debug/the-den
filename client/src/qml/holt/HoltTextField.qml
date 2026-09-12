import QtQuick
import QtQuick.Controls as Controls

// Glass input, with the field label rendered above in eyebrow style when `label` is set.
Controls.TextField {
    id: field
    property string label: ""

    implicitHeight: 38
    implicitWidth: 160
    topPadding: 0
    leftPadding: 12
    rightPadding: 12
    font.family: Theme.fontCore
    font.pixelSize: 14
    color: Theme.ink
    placeholderTextColor: Theme.ink28
    selectionColor: Theme.current
    selectedTextColor: Theme.deep
    selectByMouse: true

    background: Rectangle {
        radius: Theme.radiusMd
        color: Theme.glassInputSurface
        border.width: 1
        border.color: field.activeFocus ? Theme.current : Theme.glassBorderStrong
        Behavior on border.color { ColorAnimation { duration: Theme.motionFast } }
    }
}
