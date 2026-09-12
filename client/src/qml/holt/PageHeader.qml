import QtQuick
import QtQuick.Layouts

// Page title + meta line on the left, an optional toolbar (filters, actions) on the right.
RowLayout {
    id: header
    property string title: ""
    property string meta: ""
    default property alias toolbar: tools.data
    Layout.fillWidth: true
    spacing: Theme.space3

    ColumnLayout {
        spacing: 2
        Text { text: header.title; font.family: Theme.fontCore; font.pixelSize: Theme.sizePageTitle; font.weight: Font.ExtraBold; font.letterSpacing: -1; color: Theme.ink }
        Meta { text: header.meta; visible: header.meta !== "" }
    }
    Item { Layout.fillWidth: true }
    Row { id: tools; spacing: 6 }
}
