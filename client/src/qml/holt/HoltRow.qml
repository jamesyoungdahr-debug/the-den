import QtQuick
import QtQuick.Layouts

// A glass list row: optional thumb on the left, whatever you put in the middle, and
// actions on the right. The web's .holt-row.
Rectangle {
    id: row
    property string thumb: ""
    property int thumbWidth: 40
    property bool highlighted: false
    default property alias content: main.data
    property alias actions: actionsRow.data
    signal clicked()

    Layout.fillWidth: true
    implicitHeight: Math.max(thumbItem.visible ? thumbItem.height + 20 : 0, main.implicitHeight + 24, 56)
    radius: Theme.radiusMd
    color: mouse.containsMouse ? Theme.glassSurfaceStrong : Theme.glassSurface
    border.width: 1
    border.color: highlighted ? Theme.current : Theme.glassBorder

    MouseArea { id: mouse; anchors.fill: parent; hoverEnabled: true; onClicked: row.clicked(); propagateComposedEvents: true; z: -1 }

    RowLayout {
        anchors { fill: parent; leftMargin: 12; rightMargin: 12 }
        spacing: Theme.space3

        Rectangle {
            id: thumbItem
            visible: row.thumb !== "" || row.thumbWidth > 0 && thumbSlotVisible
            property bool thumbSlotVisible: row.thumb !== ""
            width: row.thumbWidth; height: Math.round(row.thumbWidth * 1.5)
            radius: Theme.radiusSm
            color: Theme.raised
            clip: true
            Image { anchors.fill: parent; source: row.thumb; fillMode: Image.PreserveAspectCrop; asynchronous: true; cache: true; sourceSize.width: 92 }
        }

        ColumnLayout {
            id: main
            Layout.fillWidth: true
            spacing: 3
            // Whatever the page drops in here hugs the left edge and may take the full width.
            onChildrenChanged: { for (var i = 0; i < children.length; i++) { children[i].Layout.fillWidth = true; children[i].Layout.alignment = Qt.AlignLeft } }
        }

        Row { id: actionsRow; spacing: 6 }
    }
}
