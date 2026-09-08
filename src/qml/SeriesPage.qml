import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page
    title: "TV"

    Component.onCompleted: seriesModel.refresh()

    ListView {
        id: listView
        model: seriesModel

        header: ColumnLayout {
            width: ListView.view.width
            spacing: Kirigami.Units.largeSpacing

            // Nested here, not as a page-level sibling: ListView.header is
            // Component-typed, so an inline item assigned to it gets implicitly
            // wrapped in its own Component with its own id scope -- statusBanner
            // is only visible to things declared inside that same wrapped scope.
            Connections {
                target: seriesModel
                function onErrorOccurred(message) {
                    statusBanner.text = "Error: " + message
                    statusBanner.type = Kirigami.MessageType.Error
                    statusBanner.visible = true
                }
            }

            Connections {
                target: seriesSearchModel
                function onErrorOccurred(message) {
                    statusBanner.text = "Search error: " + message
                    statusBanner.type = Kirigami.MessageType.Error
                    statusBanner.visible = true
                }
            }

            Kirigami.InlineMessage {
                id: statusBanner
                Layout.fillWidth: true
                visible: false
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                Controls.TextField {
                    id: searchField
                    Layout.fillWidth: true
                    placeholderText: "Search TVmaze..."
                    onAccepted: seriesSearchModel.search(text)
                }
                Controls.Button {
                    text: "Search"
                    onClicked: seriesSearchModel.search(searchField.text)
                }
            }

            Repeater {
                id: searchRepeater
                model: seriesSearchModel
                delegate: Kirigami.SwipeListItem {
                    Layout.fillWidth: true
                    contentItem: RowLayout {
                        spacing: Kirigami.Units.largeSpacing

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                text: title
                                font.family: Theme.fontCore
                                font.weight: Font.Bold
                                font.pixelSize: 13
                                color: Theme.ink
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            Text {
                                text: year ? String(year) : "-"
                                font.family: Theme.fontMono
                                font.pixelSize: 10
                                color: Theme.ink42
                            }
                        }

                        Controls.Button {
                            text: "Add"
                            highlighted: true
                            onClicked: seriesModel.addSeries(tvmazeId, title, year ? String(year) : "", overview, posterPath)
                        }
                    }
                }
            }

            Kirigami.Separator { Layout.fillWidth: true; visible: searchRepeater.count > 0 }

            Kirigami.Heading {
                text: "Library"
                level: 3
            }
        }

        delegate: Kirigami.SwipeListItem {
            width: ListView.view.width
            contentItem: RowLayout {
                spacing: Kirigami.Units.largeSpacing

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        text: title
                        font.family: Theme.fontCore
                        font.weight: Font.Bold
                        font.pixelSize: 13
                        color: Theme.ink
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                    Text {
                        text: year ? String(year) : "-"
                        font.family: Theme.fontMono
                        font.pixelSize: 10
                        color: Theme.ink42
                    }
                }
            }
            actions: [
                Kirigami.Action {
                    text: "View episodes"
                    onTriggered: applicationWindow().pageStack.push(
                        Qt.resolvedUrl("EpisodesPage.qml"), { seriesId: seriesId, seriesTitle: title })
                },
                Kirigami.Action { text: "Remove"; onTriggered: seriesModel.deleteSeries(seriesId) }
            ]
        }
    }
}
