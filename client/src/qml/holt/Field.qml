import QtQuick
import QtQuick.Layouts

// Label-above-control form field (the web's .holt-field). Put the control inside.
ColumnLayout {
    id: field
    property string label: ""
    property string hint: ""
    default property alias control: slot.data
    spacing: 6
    Layout.fillWidth: true
    Layout.minimumWidth: 0
    Layout.preferredWidth: 160

    Eyebrow { text: field.label; accent: false; visible: field.label !== ""; Layout.fillWidth: true; elide: Text.ElideRight }
    Item {
        id: slot
        Layout.fillWidth: true
        implicitHeight: childrenRect.height
        onChildrenChanged: { for (var i = 0; i < children.length; i++) children[i].width = Qt.binding(function () { return slot.width }) }
    }
    Meta { text: field.hint; visible: field.hint !== ""; Layout.fillWidth: true; wrapMode: Text.WordWrap; elide: Text.ElideNone }
}
