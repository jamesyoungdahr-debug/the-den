import QtQuick
import QtQuick.Layouts

// Centred empty state: ring mark, title, body, optional action.
GlassPanel {
    id: empty
    property string title: ""
    property string body: ""
    property string actionText: ""
    signal action()

    padding: Theme.space5
    Layout.fillWidth: true

    ColumnLayout {
        width: parent.width
        spacing: Theme.space2
        RingMark { markSize: 34; Layout.alignment: Qt.AlignHCenter; ringColor: Theme.ink28 }
        Text { text: empty.title; font.family: Theme.fontCore; font.pixelSize: Theme.sizeSectionTitle; font.weight: Font.ExtraBold; color: Theme.ink; Layout.alignment: Qt.AlignHCenter }
        Text { text: empty.body; font.family: Theme.fontCore; font.pixelSize: Theme.sizeBodySmall; color: Theme.ink55; Layout.alignment: Qt.AlignHCenter; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; Layout.maximumWidth: 420 }
        HoltButton { visible: empty.actionText !== ""; text: empty.actionText; small: true; Layout.alignment: Qt.AlignHCenter; Layout.topMargin: Theme.space2; onClicked: empty.action() }
    }
}
