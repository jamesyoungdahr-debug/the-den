import QtQuick
import org.kde.kirigami as Kirigami

// Every page's base: a Kirigami.ScrollablePage with no background of its own, so the
// window's ground layer (deep + ambient glows) shows through the glass panels.
Kirigami.ScrollablePage {
    background: null
    padding: Theme.space4
    Kirigami.Theme.inherit: true
}
