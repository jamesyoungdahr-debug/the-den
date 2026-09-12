import QtQuick
import QtQuick.Layouts

// A titled, horizontally scrolling row of PosterCards over a JsonListModel with the
// Discover card fields. Hidden when the model is empty and not loading.
ColumnLayout {
    id: rail
    property string title: ""
    property string subtitle: ""
    property var model: null
    property int posterWidth: Theme.posterMd
    signal cardClicked(string mediaType, int tmdbId)

    visible: (model && (model.count > 0 || model.loading)) ? true : false
    spacing: Theme.space2
    Layout.fillWidth: true

    RowLayout {
        Layout.fillWidth: true
        ColumnLayout {
            spacing: 2
            Text { text: rail.title; font.family: Theme.fontCore; font.pixelSize: Theme.sizeSectionTitle; font.weight: Font.ExtraBold; color: Theme.ink }
            Meta { text: rail.subtitle; visible: rail.subtitle !== "" }
        }
        Item { Layout.fillWidth: true }
        HoltButton { kind: "quiet"; small: true; text: "‹"; onClicked: list.contentX = Math.max(0, list.contentX - list.width * 0.8) }
        HoltButton { kind: "quiet"; small: true; text: "›"; onClicked: list.contentX = Math.min(list.contentWidth - list.width, list.contentX + list.width * 0.8) }
    }

    ListView {
        id: list
        Layout.fillWidth: true
        implicitHeight: Math.round(rail.posterWidth * 1.5) + 48
        orientation: ListView.Horizontal
        spacing: Theme.space3
        clip: true
        model: rail.model
        boundsBehavior: Flickable.StopAtBounds
        Behavior on contentX { NumberAnimation { duration: Theme.motionBase; easing.type: Easing.OutCubic } }

        delegate: PosterCard {
            posterWidth: rail.posterWidth
            title: model.title
            year: model.year
            posterPath: model.posterPath
            status: model.status
            rating: model.rating
            onClicked: rail.cardClicked(model.mediaType, model.tmdbId)
        }

        Row {
            visible: rail.model && rail.model.loading && rail.model.count === 0
            spacing: Theme.space3
            Repeater { model: 6; Skeleton { width: rail.posterWidth; height: Math.round(rail.posterWidth * 1.5) } }
        }
    }
}
