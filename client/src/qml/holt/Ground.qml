import QtQuick
import QtQuick.Shapes

// The ground layer under every page: deep background with two soft ambient glows
// (purple top-left, teal bottom-right) and a faint ring, like the web's body::before.
// Drawn with radial gradients, so no offscreen blur pass is needed.
Rectangle {
    id: ground
    color: Theme.deep

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeWidth: 0
            fillGradient: RadialGradient {
                centerX: ground.width * 0.18; centerY: ground.height * 0.08
                focalX: centerX; focalY: centerY
                centerRadius: Math.max(ground.width, ground.height) * 0.55
                GradientStop { position: 0.0; color: Theme.glowCurrent }
                GradientStop { position: 1.0; color: "transparent" }
            }
            startX: 0; startY: 0
            PathLine { x: ground.width; y: 0 }
            PathLine { x: ground.width; y: ground.height }
            PathLine { x: 0; y: ground.height }
            PathLine { x: 0; y: 0 }
        }
        ShapePath {
            strokeWidth: 0
            fillGradient: RadialGradient {
                centerX: ground.width * 0.9; centerY: ground.height * 0.95
                focalX: centerX; focalY: centerY
                centerRadius: Math.max(ground.width, ground.height) * 0.5
                GradientStop { position: 0.0; color: Theme.glowHealthy }
                GradientStop { position: 1.0; color: "transparent" }
            }
            startX: 0; startY: 0
            PathLine { x: ground.width; y: 0 }
            PathLine { x: ground.width; y: ground.height }
            PathLine { x: 0; y: ground.height }
            PathLine { x: 0; y: 0 }
        }
    }

    Rectangle {
        width: Math.min(ground.width, ground.height) * 0.9
        height: width
        radius: width / 2
        x: ground.width * 0.55
        y: -height * 0.35
        color: "transparent"
        border.width: 1
        border.color: Theme.ring
    }
}
