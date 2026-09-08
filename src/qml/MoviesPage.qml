import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page
    title: "Movies"

    Component.onCompleted: movieModel.refresh()

    ListView {
        id: listView
        model: movieModel

        header: ColumnLayout {
            width: ListView.view.width
            spacing: Kirigami.Units.largeSpacing

            // Nested here, not as a page-level sibling: ListView.header is
            // Component-typed, so an inline item assigned to it gets implicitly
            // wrapped in its own Component with its own id scope -- statusBanner
            // is only visible to things declared inside that same wrapped scope.
            Connections {
                target: movieModel
                function onErrorOccurred(message) {
                    statusBanner.text = "Error: " + message
                    statusBanner.type = Kirigami.MessageType.Error
                    statusBanner.visible = true
                }
            }

            Connections {
                target: movieSearchModel
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
                    placeholderText: "Search TMDB..."
                    onAccepted: movieSearchModel.search(text)
                }
                Controls.Button {
                    text: "Search"
                    onClicked: movieSearchModel.search(searchField.text)
                }
            }

            Repeater {
                id: searchRepeater
                model: movieSearchModel
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
                            onClicked: movieModel.addMovie(tmdbId, title, year ? String(year) : "", overview, posterPath)
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

                StatusPill {
                    label: hasFile ? "have" : "missing"
                    tone: hasFile ? "healthy" : "idle"
                }
            }
            actions: [
                Kirigami.Action {
                    text: "Find releases"
                    visible: !hasFile
                    onTriggered: applicationWindow().pageStack.push(
                        Qt.resolvedUrl("CandidatesPage.qml"), { movieId: movieId, movieTitle: title })
                },
                Kirigami.Action { text: "Remove"; onTriggered: movieModel.deleteMovie(movieId) }
            ]
        }
    }
}
