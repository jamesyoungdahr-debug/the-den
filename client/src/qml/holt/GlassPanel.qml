import QtQuick

// A HoltOS Glass surface: translucent panel, hairline border, a faint highlight along
// the top edge. Content shows through the ground layer's ambient glows, which gives the
// glass feel without a live blur pass (see Ground.qml); `strong` is the floating variant
// used for dialogs and the sidebar.
Rectangle {
    id: panel
    property bool strong: false
    property int padding: Theme.space3
    default property alias content: inner.data

    color: strong ? Theme.glassSurfaceStrong : Theme.glassSurface
    radius: Theme.radiusLg
    border.width: 1
    border.color: strong ? Theme.glassBorderStrong : Theme.glassBorder
    implicitWidth: inner.implicitWidth + padding * 2
    implicitHeight: inner.implicitHeight + padding * 2

    Rectangle {
        anchors { left: parent.left; right: parent.right; top: parent.top; leftMargin: panel.radius; rightMargin: panel.radius }
        height: 1
        color: panel.strong ? Theme.glassHighlightStrong : Theme.glassHighlight
    }

    Item {
        id: inner
        anchors.fill: parent
        anchors.margins: panel.padding
        implicitWidth: childrenRect.width
        implicitHeight: childrenRect.height
    }
}
