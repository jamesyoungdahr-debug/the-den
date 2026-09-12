# Maintainer: you <you@example.com>
#
# Builds from this checkout directly (no VCS/network source fetch) — run
# `makepkg -si` from this directory (client/ in the the-den repo).
pkgname=the-den-client
pkgver=0.1.0
pkgrel=1
pkgdesc="Native KDE desktop companion app for The Den — talks to its JSON API instead of a browser"
arch=('any')
url="https://github.com/jamesyoungdahr-debug/the-den"
license=('unknown')
depends=('python' 'pyside6' 'kirigami' 'qqc2-desktop-style')

package() {
    # This PKGBUILD has no source array, so $startdir is the repo checkout itself.
    local app_dir="$pkgdir/opt/the-den-client"
    install -dm755 "$app_dir"
    cp -r "$startdir/src" "$app_dir/"

    install -Dm755 "$startdir/deploy/the-den-client" "$pkgdir/usr/bin/the-den-client"
    install -Dm644 "$startdir/deploy/the-den-client.desktop" "$pkgdir/usr/share/applications/the-den-client.desktop"
    install -Dm644 "$startdir/assets/logo.svg" "$pkgdir/usr/share/icons/hicolor/scalable/apps/the-den-client.svg"
}
