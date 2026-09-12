import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts

// Floating-glass modal dialog with an eyebrow title and a footer for buttons.
Controls.Popup {
    id: dialog
    property string title: ""
    default property alias body: bodyLayout.data
    property alias footer: footerRow.data

    parent: Controls.Overlay.overlay
    anchors.centerIn: parent
    modal: true
    focus: true
    width: Math.min(520, parent ? parent.width - 40 : 520)
    padding: Theme.space4
    closePolicy: Controls.Popup.CloseOnEscape | Controls.Popup.CloseOnPressOutside

    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.motionFast } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: Theme.motionFast } }

    Controls.Overlay.modal: Rectangle { color: Theme.scrimMid }

    background: GlassPanel { strong: true; radius: Theme.radiusLg }

    contentItem: ColumnLayout {
        spacing: Theme.space3
        Eyebrow { text: dialog.title }
        ColumnLayout { id: bodyLayout; spacing: Theme.space2; Layout.fillWidth: true }
        RowLayout { id: footerRow; spacing: 8; Layout.fillWidth: true; Layout.alignment: Qt.AlignRight }
    }
}
