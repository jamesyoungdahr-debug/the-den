import QtQuick
import "Holt.js" as H

// Poster with a status badge overlay, title and year underneath; hover lifts it.
Item {
    id: card
    property string title: ""
    property var year: null
    property string posterPath: ""
    property string status: ""
    property real rating: 0
    property int posterWidth: Theme.posterMd
    property bool showRating: true
    signal clicked()

    width: posterWidth
    implicitHeight: poster.height + 8 + titleText.implicitHeight + metaText.implicitHeight + 4

    Rectangle {
        id: poster
        width: card.posterWidth
        height: Math.round(card.posterWidth * 1.5)
        radius: Theme.radiusMd
        color: Theme.raised
        border.width: 1
        border.color: mouse.containsMouse ? Theme.currentHover : Theme.glassBorder
        clip: true
        scale: mouse.containsMouse ? 1.03 : 1
        Behavior on scale { NumberAnimation { duration: Theme.motionFast; easing.type: Easing.OutCubic } }
        Behavior on border.color { ColorAnimation { duration: Theme.motionFast } }

        Image {
            anchors.fill: parent
            source: H.posterUrl(card.posterPath)
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
            cache: true
            sourceSize.width: 342
            visible: status === Image.Ready
        }
        Text {
            anchors.centerIn: parent
            visible: card.posterPath === ""
            text: card.title.length ? card.title.charAt(0) : "?"
            font.family: Theme.fontCore
            font.weight: Font.Black
            font.pixelSize: Math.round(card.posterWidth * 0.36)
            color: Theme.ink28
        }
        Badge {
            anchors { left: parent.left; top: parent.top; margins: 8 }
            solid: true
            tone: H.statusBadge(card.status).tone
            label: H.statusBadge(card.status).label
        }
        Rectangle {
            visible: card.showRating && card.rating > 0
            anchors { right: parent.right; bottom: parent.bottom; margins: 8 }
            width: ratingText.implicitWidth + 12; height: 20; radius: 10
            color: Theme.glassBadgeSurface
            border.width: 1; border.color: Theme.glassBorder
            Text { id: ratingText; anchors.centerIn: parent; text: "★ " + Number(card.rating).toFixed(1); font.family: Theme.fontMono; font.pixelSize: 10; color: Theme.ink }
        }
    }

    Text {
        id: titleText
        anchors { top: poster.bottom; topMargin: 8; left: parent.left; right: parent.right }
        text: card.title
        font.family: Theme.fontCore
        font.pixelSize: 13
        font.weight: Font.Bold
        color: mouse.containsMouse ? Theme.current : Theme.ink
        elide: Text.ElideRight
        maximumLineCount: 1
    }
    Meta {
        id: metaText
        anchors { top: titleText.bottom; topMargin: 2; left: parent.left; right: parent.right }
        text: card.year ? String(card.year) : " "
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: card.clicked()
    }
}
