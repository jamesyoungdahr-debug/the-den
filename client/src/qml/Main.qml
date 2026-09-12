import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "holt"

// The HoltOS Glass shell (U4): glass sidebar on the left (rail when narrow or
// collapsed), glass top bar with global search + the page's one primary action, and a
// page stack. Every page is a Kirigami.ScrollablePage pushed onto `pageStack`; the
// Kirigami.Theme overrides cascade the brand into every QQC2/Kirigami control.
Controls.ApplicationWindow {
    id: root
    title: "The Den"
    width: 1280
    height: 820
    minimumWidth: 640
    minimumHeight: 480
    visible: true
    color: Theme.deep

    // ---- navigation state ------------------------------------------------------------
    property string activeNav: "discover"
    property bool sidebarCollapsed: false
    readonly property bool compact: width < Theme.mobileBreakpoint
    readonly property bool railMode: compact || sidebarCollapsed
    property alias pageStack: stack
    // The page's single primary action, shown in the top bar ("one shout per screen").
    property var pageAction: null

    readonly property var navGroups: [
        { name: "Browse", items: [
            { key: "discover", label: "Discover", page: "DiscoverPage.qml", icon: "◎" },
            { key: "requests", label: "Requests", page: "RequestsPage.qml", icon: "▤" },
        ]},
        { name: "Library", items: [
            { key: "movies", label: "Movies", page: "MoviesPage.qml", icon: "▭" },
            { key: "tv", label: "TV", page: "SeriesPage.qml", icon: "▯" },
            { key: "calendar", label: "Calendar", page: "CalendarPage.qml", icon: "▦" },
        ]},
        { name: "Admin", admin: true, items: [
            { key: "downloads", label: "Downloads", page: "DownloadsPage.qml", icon: "⇣" },
            { key: "indexers", label: "Indexers", page: "IndexersPage.qml", icon: "⌕" },
            { key: "settings", label: "Settings", page: "SettingsPage.qml", icon: "⚙" },
        ]},
    ]

    function navigate(key) {
        for (var g = 0; g < navGroups.length; g++)
            for (var i = 0; i < navGroups[g].items.length; i++)
                if (navGroups[g].items[i].key === key) {
                    activeNav = key
                    pageAction = null
                    stack.replace(null, Qt.resolvedUrl(navGroups[g].items[i].page))
                    return
                }
    }
    function push(page, props) {
        stack.push(Qt.resolvedUrl(page), props || {})
    }
    function openDetail(mediaType, tmdbId) {
        push("DetailPage.qml", { kind: mediaType, tmdbId: tmdbId })
    }
    function search(query) {
        if (!query || !query.trim().length) return
        activeNav = "discover"
        discoverSearchModel.search(query)
        if (stack.currentItem && stack.currentItem.objectName === "searchPage") return
        push("SearchPage.qml")
    }
    function toast(message, tone) { toaster.show(message, tone) }

    // Route: login page until we can browse, otherwise the active nav page.
    function route() {
        var shell = apiClient.connected && apiClient.canBrowse
        if (!shell) {
            if (!stack.currentItem || stack.currentItem.objectName !== "loginPage")
                stack.replace(null, Qt.resolvedUrl("LoginPage.qml"))
        } else if (!stack.currentItem || stack.currentItem.objectName === "loginPage") {
            navigate("discover")
            requestsModel.refreshPending()
        }
    }
    Connections {
        target: apiClient
        function onSessionChanged() { root.route() }
        function onConnectedChanged() { root.route() }
    }
    Component.onCompleted: {
        stack.replace(null, Qt.resolvedUrl("LoginPage.qml"))
        apiClient.checkHealth()
    }

    background: Ground {}

    RowLayout {
        id: shell
        anchors.fill: parent
        spacing: 0

        // The brand palette, cascaded to every Kirigami/QQC2 control below through the
        // attached theme (the item tree, not the window, is what inherits it).
        Kirigami.Theme.inherit: false
        Kirigami.Theme.colorSet: Kirigami.Theme.View
        Kirigami.Theme.backgroundColor: Theme.deep
        Kirigami.Theme.alternateBackgroundColor: Theme.surface
        Kirigami.Theme.textColor: Theme.ink
        Kirigami.Theme.highlightColor: Theme.current
        Kirigami.Theme.highlightedTextColor: Theme.deep
        Kirigami.Theme.positiveTextColor: Theme.healthy
        Kirigami.Theme.neutralTextColor: Theme.warning
        Kirigami.Theme.negativeTextColor: Theme.warning
        Kirigami.Theme.disabledTextColor: Theme.ink28
        Kirigami.Theme.linkColor: Theme.current
        Kirigami.Theme.focusColor: Theme.current

        // ---- sidebar ---------------------------------------------------------------------
        Rectangle {
            id: sidebar
            visible: apiClient.connected && apiClient.canBrowse
            Layout.fillHeight: true
            Layout.preferredWidth: root.railMode ? Theme.sidebarRail : Theme.sidebarWidth
            Behavior on Layout.preferredWidth { NumberAnimation { duration: Theme.motionBase; easing.type: Easing.OutCubic } }
            color: Theme.glassSurfaceStrong
            Rectangle { anchors { right: parent.right; top: parent.top; bottom: parent.bottom } width: 1; color: Theme.glassBorder }

            ColumnLayout {
                anchors { fill: parent; margins: 12 }
                spacing: 4

                // lockup
                RowLayout {
                    Layout.fillWidth: true
                    Layout.bottomMargin: Theme.space3
                    spacing: 10
                    RingMark { markSize: 26 }
                    Text { visible: !root.railMode; text: "The Den"; font.family: Theme.fontCore; font.weight: Font.Black; font.pixelSize: Theme.sizeWordmark; font.letterSpacing: -0.6; color: Theme.ink; Layout.fillWidth: true }
                    HoltButton { visible: !root.compact; kind: "quiet"; small: true; text: root.sidebarCollapsed ? "»" : "«"; onClicked: root.sidebarCollapsed = !root.sidebarCollapsed }
                }

                Repeater {
                    model: root.navGroups
                    delegate: ColumnLayout {
                        id: group
                        required property var modelData
                        visible: !modelData.admin || apiClient.isAdmin
                        Layout.fillWidth: true
                        spacing: 2
                        Eyebrow { visible: !root.railMode; text: group.modelData.name; accent: false; Layout.topMargin: Theme.space2; Layout.leftMargin: 10; Layout.bottomMargin: 4 }
                        Rectangle { visible: root.railMode; Layout.fillWidth: true; Layout.topMargin: 6; Layout.bottomMargin: 6; height: 1; color: Theme.glassBorder }
                        Repeater {
                            model: group.modelData.items
                            delegate: Rectangle {
                                id: navItem
                                required property var modelData
                                readonly property bool active: root.activeNav === modelData.key
                                Layout.fillWidth: true
                                height: 38
                                radius: Theme.radiusMd
                                color: active ? Theme.currentTint : (navMouse.containsMouse ? Theme.glassHighlight : "transparent")
                                Rectangle { visible: navItem.active; width: 2; height: 18; radius: 1; color: Theme.current; anchors { left: parent.left; verticalCenter: parent.verticalCenter } }
                                RowLayout {
                                    anchors { fill: parent; leftMargin: 12; rightMargin: 10 }
                                    spacing: 10
                                    Text { text: navItem.modelData.icon; font.pixelSize: 15; color: navItem.active ? Theme.current : Theme.ink55; Layout.preferredWidth: 18; horizontalAlignment: Text.AlignHCenter }
                                    Text { visible: !root.railMode; text: navItem.modelData.label; font.family: Theme.fontCore; font.pixelSize: 14; font.weight: Font.Bold; color: navItem.active ? Theme.ink : Theme.ink70; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Rectangle {
                                        visible: navItem.modelData.key === "requests" && apiClient.isAdmin && requestsModel.pendingCount > 0
                                        width: pendingText.implicitWidth + 10; height: 18; radius: 9; color: Theme.current
                                        Text { id: pendingText; anchors.centerIn: parent; text: requestsModel.pendingCount; font.family: Theme.fontMono; font.pixelSize: 10; color: Theme.deep }
                                    }
                                }
                                MouseArea { id: navMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.navigate(navItem.modelData.key) }
                                Controls.ToolTip.visible: root.railMode && navMouse.containsMouse
                                Controls.ToolTip.text: navItem.modelData.label
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                // account
                Rectangle {
                    Layout.fillWidth: true
                    height: 48
                    radius: Theme.radiusMd
                    color: accountMouse.containsMouse ? Theme.glassHighlight : "transparent"
                    RowLayout {
                        anchors { fill: parent; leftMargin: 8; rightMargin: 8 }
                        spacing: 10
                        Avatar { initial: apiClient.signedIn ? apiClient.userInitial : "•" }
                        ColumnLayout {
                            visible: !root.railMode
                            spacing: 0
                            Layout.fillWidth: true
                            Text { text: apiClient.signedIn ? apiClient.username : "anonymous"; font.family: Theme.fontCore; font.pixelSize: 13; font.weight: Font.Bold; color: Theme.ink; elide: Text.ElideRight; Layout.fillWidth: true }
                            Meta { text: (apiClient.isAdmin ? "admin" : "user") + " · " + (apiClient.signedIn ? "sign out" : "sign in") }
                        }
                    }
                    MouseArea {
                        id: accountMouse
                        anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: apiClient.signedIn ? apiClient.logout() : stack.replace(null, Qt.resolvedUrl("LoginPage.qml"))
                    }
                }
            }
        }

        // ---- content -----------------------------------------------------------------------
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Rectangle {
                id: topBar
                visible: sidebar.visible
                Layout.fillWidth: true
                height: Theme.topBar
                color: Theme.glassSurface
                Rectangle { anchors { left: parent.left; right: parent.right; bottom: parent.bottom } height: 1; color: Theme.glassBorder }

                RowLayout {
                    anchors { fill: parent; leftMargin: Theme.space4; rightMargin: Theme.space4 }
                    spacing: Theme.space3
                    HoltButton { visible: stack.depth > 1; kind: "quiet"; small: true; text: "← Back"; onClicked: stack.pop() }
                    HoltTextField {
                        id: globalSearch
                        Layout.fillWidth: true
                        Layout.maximumWidth: 520
                        placeholderText: "Search movies and series…"
                        onAccepted: { root.search(text); text = "" }
                    }
                    Item { Layout.fillWidth: true }
                    HoltButton {
                        visible: root.pageAction !== null && root.pageAction !== undefined
                        kind: "primary"
                        text: root.pageAction ? root.pageAction.text : ""
                        onClicked: if (root.pageAction) root.pageAction.trigger()
                    }
                }
            }

            Controls.StackView {
                id: stack
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                replaceEnter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.motionBase } }
                replaceExit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: Theme.motionFast } }
                pushEnter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.motionBase } }
                pushExit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: Theme.motionFast } }
                popEnter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.motionBase } }
                popExit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: Theme.motionFast } }
            }
        }
    }

    // ---- toasts -----------------------------------------------------------------------------
    GlassPanel {
        id: toaster
        property string tone: "info"
        function show(message, kind) { toastText.text = message; tone = kind || "info"; visible = true; toastTimer.restart() }
        visible: false
        strong: true
        z: 100
        padding: 12
        anchors { bottom: parent.bottom; right: parent.right; margins: Theme.space4 }
        border.color: tone === "positive" ? Theme.healthy : tone === "error" ? Theme.warning : Theme.glassBorderStrong
        Text { id: toastText; font.family: Theme.fontCore; font.pixelSize: 13; color: Theme.ink }
        Timer { id: toastTimer; interval: 4000; onTriggered: toaster.visible = false }
    }
}
