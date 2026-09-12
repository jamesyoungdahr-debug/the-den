
import QtQuick
import QtQuick.Controls as Controls
Controls.ApplicationWindow {
    id: root
    width: 1200; height: 800; visible: true
    property alias pageStack: stack
    property var pageAction: null
    property string activeNav: ""
    property var lastToast: null
    property var lastNav: null
    function navigate(key) { lastNav = key }
    function push(page, props) { stack.push(Qt.resolvedUrl("/mnt/c/projects/The den/client/src/qml/" + page), props || {}) }
    function openDetail(t, id) { lastNav = "detail:" + t + ":" + id }
    function search(q) { lastNav = "search:" + q }
    function toast(m, t) { lastToast = m }
    function loadPage(page, propsJson) { stack.replace(null, Qt.resolvedUrl("/mnt/c/projects/The den/client/src/qml/" + page), JSON.parse(propsJson)) }
    function currentName() { return stack.currentItem ? stack.currentItem.objectName : "" }
    Controls.StackView { id: stack; anchors.fill: parent }
}
