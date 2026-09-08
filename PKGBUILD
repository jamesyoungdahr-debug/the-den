# Maintainer: you <you@example.com>
#
# Builds from this checkout directly (no VCS/network source fetch) — run
# `makepkg -si` from the repo root. pip installs the Python dependencies from
# PyPI during build(), which is fine for a personal/distro-local package but
# is not how packages meant for the official Arch repos or AUR are expected
# to behave (they must not reach the network during build()).
pkgname=the-den
pkgver=0.1.0
pkgrel=1
pkgdesc="Unified movie/TV library manager (Sonarr+Radarr+Prowlarr replacement)"
arch=('any')
url="https://example.invalid/the-den"
license=('unknown')
depends=('python')
makedepends=('python-virtualenv')
optdepends=('qbittorrent-nox: default download client')
backup=('etc/the-den/the-den.env')
install=the-den.install

package() {
    # This PKGBUILD has no source array, so $startdir is the repo checkout itself.
    local app_dir="$pkgdir/opt/the-den"
    install -dm755 "$app_dir"
    cp -r "$startdir/app" "$startdir/migrations" "$app_dir/"
    install -Dm644 "$startdir/requirements.txt" "$app_dir/requirements.txt"
    install -Dm644 "$startdir/alembic.ini" "$app_dir/alembic.ini"

    python -m venv "$app_dir/.venv"
    "$app_dir/.venv/bin/python" -m pip install --no-cache-dir -q -r "$app_dir/requirements.txt"

    install -Dm644 "$startdir/deploy/the-den.service" "$pkgdir/usr/lib/systemd/system/the-den.service"
    install -Dm644 "$startdir/deploy/the-den-sysusers.conf" "$pkgdir/usr/lib/sysusers.d/the-den.conf"
    install -Dm644 "$startdir/deploy/the-den-tmpfiles.conf" "$pkgdir/usr/lib/tmpfiles.d/the-den.conf"
    install -Dm640 "$startdir/deploy/the-den.env.example" "$pkgdir/etc/the-den/the-den.env"
}
