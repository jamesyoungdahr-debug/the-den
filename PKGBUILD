# Maintainer: you <you@example.com>
#
# Builds from this checkout directly (no VCS/network source fetch) -- run
# `makepkg -si` from the repo root. pip installs the Python dependencies from
# PyPI during build(), which is fine for a personal/distro-local package but
# is not how packages meant for the official Arch repos or AUR are expected
# to behave (they must not reach the network during build()).
pkgname=the-den
pkgver=0.3.1
pkgrel=1
pkgdesc="Unified movie/TV library manager with a built-in torrent client (Sonarr+Radarr+Prowlarr+qBittorrent replacement)"
arch=('any')
url="https://github.com/jamesyoungdahr-debug/the-den"
license=('unknown')
# libtorrent-rasterbar ships the Python bindings the built-in torrent client is made of;
# the venv is created with --system-site-packages so it can import them.
depends=('python' 'libtorrent-rasterbar')
makedepends=('python-virtualenv')
backup=('etc/the-den/the-den.env')
install=the-den.install
# No compiled binaries of our own here -- the bundled interpreter's debug symbols
# aren't ours to strip, and makepkg's debug-package step chokes on the venv's
# non-ASCII '𝜋thon' symlink (a real Python 3.14 venv easter egg) anyway.
options=('!debug' '!strip')

package() {
    # This PKGBUILD has no source array, so $startdir is the repo checkout itself.
    local app_dir="$pkgdir/opt/the-den"
    install -dm755 "$app_dir"
    cp -r "$startdir/app" "$startdir/migrations" "$app_dir/"
    install -Dm644 "$startdir/requirements.txt" "$app_dir/requirements.txt"
    install -Dm644 "$startdir/alembic.ini" "$app_dir/alembic.ini"

    python -m venv --system-site-packages "$app_dir/.venv"
    "$app_dir/.venv/bin/python" -m pip install --no-cache-dir -q -r "$app_dir/requirements.txt"

    install -Dm644 "$startdir/deploy/the-den.service" "$pkgdir/usr/lib/systemd/system/the-den.service"
    install -Dm644 "$startdir/deploy/the-den-sysusers.conf" "$pkgdir/usr/lib/sysusers.d/the-den.conf"
    install -Dm644 "$startdir/deploy/the-den-tmpfiles.conf" "$pkgdir/usr/lib/tmpfiles.d/the-den.conf"
    install -Dm640 "$startdir/deploy/the-den.env.example" "$pkgdir/etc/the-den/the-den.env"
}
