import QtQuick

// Loading placeholder with a slow shimmer.
Rectangle {
    radius: Theme.radiusMd
    color: Theme.glassSurface
    border.width: 1
    border.color: Theme.glassBorder
    SequentialAnimation on opacity {
        loops: Animation.Infinite
        NumberAnimation { to: 0.45; duration: 900; easing.type: Easing.InOutSine }
        NumberAnimation { to: 1.0; duration: 900; easing.type: Easing.InOutSine }
    }
}
