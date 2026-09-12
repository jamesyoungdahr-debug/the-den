import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "holt"
import "holt/Holt.js" as H

// Home: a trending hero, Recommended for you, then the TMDB rails -- every card
// stamped with the library's and Plex's status.
HoltPage {
    id: page
    objectName: "discoverPage"
    title: "Discover"
    padding: 0

    readonly property var rails: [trendingRail, recommendedRail, popularMoviesRail, upcomingMoviesRail, popularTvRail, onTheAirRail]
    property var hero: null

    Component.onCompleted: { for (var i = 0; i < rails.length; i++) rails[i].refresh() }

    Connections {
        target: trendingRail
        function onLoaded() {
            for (var i = 0; i < trendingRail.count; i++) {
                var item = trendingRail.get(i)
                if (item.backdrop_path) { page.hero = item; return }
            }
            page.hero = null
        }
        function onErrorOccurred(message) { banner.showError("Discover needs a TMDB key on the server: " + message) }
    }

    ColumnLayout {
        width: page.width
        spacing: Theme.space4

        // ---- hero ----
        Item {
            Layout.fillWidth: true
            implicitHeight: page.hero ? Math.min(420, Math.max(280, page.width * 0.32)) : 0
            visible: page.hero !== null
            clip: true

            Image {
                anchors.fill: parent
                source: page.hero ? H.backdropUrl(page.hero.backdrop_path) : ""
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
                sourceSize.width: 1280
            }
            Rectangle {
                anchors.fill: parent
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: Theme.scrimStrong }
                    GradientStop { position: 0.6; color: Theme.scrimMid }
                    GradientStop { position: 1.0; color: Theme.scrimWeak }
                }
            }
            Rectangle {
                anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                height: parent.height * 0.5
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "transparent" }
                    GradientStop { position: 1.0; color: Theme.deep }
                }
            }
            ColumnLayout {
                anchors { left: parent.left; bottom: parent.bottom; margins: Theme.space5 }
                width: Math.min(640, parent.width - 2 * Theme.space5)
                spacing: Theme.space2
                Eyebrow { text: "Trending this week" }
                Text {
                    text: page.hero ? page.hero.title : ""
                    font.family: Theme.fontCore; font.weight: Font.Black; font.pixelSize: Math.min(Theme.sizeDisplay, Math.max(28, page.width / 24)); font.letterSpacing: -1.8
                    color: Theme.ink; wrapMode: Text.WordWrap; Layout.fillWidth: true
                }
                Meta { text: page.hero ? ((page.hero.media_type === "movie" ? "Movie" : "Series") + (page.hero.year ? " · " + page.hero.year : "") + (page.hero.rating ? " · ★ " + Number(page.hero.rating).toFixed(1) : "")) : "" }
                Text { text: page.hero ? page.hero.overview : ""; font.family: Theme.fontCore; font.pixelSize: 14; color: Theme.ink70; wrapMode: Text.WordWrap; maximumLineCount: 3; elide: Text.ElideRight; Layout.fillWidth: true }
                RowLayout {
                    spacing: 10
                    HoltButton { kind: "primary"; text: "Details"; onClicked: Controls.ApplicationWindow.window.openDetail(page.hero.media_type, page.hero.tmdb_id) }
                    Badge { tone: page.hero ? H.statusBadge(page.hero.status).tone : ""; label: page.hero ? H.statusBadge(page.hero.status).label : "" }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.space4
            Layout.rightMargin: Theme.space4
            Layout.bottomMargin: Theme.space5
            spacing: Theme.space5

            StatusBanner { id: banner; sticky: true }

            Rail { title: "Recommended for you"; subtitle: "based on what you added recently"; model: recommendedRail; onCardClicked: (t, id) => Controls.ApplicationWindow.window.openDetail(t, id) }
            Rail { title: "Trending"; subtitle: "movies and series this week"; model: trendingRail; onCardClicked: (t, id) => Controls.ApplicationWindow.window.openDetail(t, id) }
            Rail { title: "Popular movies"; model: popularMoviesRail; onCardClicked: (t, id) => Controls.ApplicationWindow.window.openDetail(t, id) }
            Rail { title: "Upcoming"; subtitle: "in cinemas soon"; model: upcomingMoviesRail; onCardClicked: (t, id) => Controls.ApplicationWindow.window.openDetail(t, id) }
            Rail { title: "Popular series"; model: popularTvRail; onCardClicked: (t, id) => Controls.ApplicationWindow.window.openDetail(t, id) }
            Rail { title: "On the air"; subtitle: "airing now"; model: onTheAirRail; onCardClicked: (t, id) => Controls.ApplicationWindow.window.openDetail(t, id) }

            EmptyState {
                visible: !trendingRail.loading && trendingRail.count === 0 && !banner.visible
                title: "Nothing to discover yet"
                body: "Discover needs a TMDB key on the server. One ships with The Den, so check the server can reach themoviedb.org."
            }
        }
    }
}
