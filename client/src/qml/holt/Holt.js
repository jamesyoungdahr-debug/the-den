// Shared helpers for the HoltOS Glass QML components and pages.
.pragma library

var TMDB_POSTER = "https://image.tmdb.org/t/p/w342"
var TMDB_BACKDROP = "https://image.tmdb.org/t/p/w1280"
var TMDB_PROFILE = "https://image.tmdb.org/t/p/w185"

function posterUrl(path) {
    if (!path) return ""
    return path.indexOf("http") === 0 ? path : TMDB_POSTER + path
}

function backdropUrl(path) {
    if (!path) return ""
    return path.indexOf("http") === 0 ? path : TMDB_BACKDROP + path
}

function profileUrl(path) {
    if (!path) return ""
    return path.indexOf("http") === 0 ? path : TMDB_PROFILE + path
}

function pad(n) {
    return n < 10 ? "0" + n : String(n)
}

function bytes(n) {
    n = Number(n) || 0
    var units = ["B", "KiB", "MiB", "GiB", "TiB"]
    var i = 0
    while (n >= 1024 && i < units.length - 1) { n /= 1024; i++ }
    return (i === 0 ? n : n.toFixed(i >= 3 ? 2 : 1)) + " " + units[i]
}

function rate(n) {
    return bytes(n) + "/s"
}

function eta(seconds) {
    if (seconds === null || seconds === undefined || seconds < 0) return "--"
    if (seconds < 60) return seconds + "s"
    if (seconds < 3600) return Math.round(seconds / 60) + "m"
    if (seconds < 86400) return Math.floor(seconds / 3600) + "h " + Math.round((seconds % 3600) / 60) + "m"
    return Math.round(seconds / 86400) + "d"
}

// The web's badge vocabulary: status -> (tone, label)
function statusBadge(status) {
    switch (status) {
    case "available": return { tone: "available", label: "available" }
    case "partial": return { tone: "partial", label: "partial" }
    case "wanted": return { tone: "pending", label: "in library" }
    case "requested": return { tone: "pending", label: "requested" }
    case "pending": return { tone: "pending", label: "pending" }
    case "approved": return { tone: "processing", label: "approved" }
    case "declined": return { tone: "error", label: "declined" }
    default: return { tone: "", label: "" }
    }
}

function torrentBadge(t) {
    if (t.error) return { tone: "error", label: "error" }
    if (t.group === "stopped") return { tone: "missing", label: "stopped" }
    if (t.group === "seeding") return { tone: "available", label: t.recordStatus === "imported" ? "imported" : "seeding" }
    if (t.state === "checking") return { tone: "partial", label: "checking" }
    if (t.state === "metadata") return { tone: "pending", label: "metadata" }
    return { tone: "processing", label: "downloading" }
}

function relativeDay(iso) {
    if (!iso) return ""
    var d = new Date(iso.substr(0, 10))
    var today = new Date(); today.setHours(0, 0, 0, 0)
    var days = Math.round((d - today) / 86400000)
    if (days === 0) return "today"
    if (days === 1) return "tomorrow"
    if (days === -1) return "yesterday"
    if (days > 1 && days < 7) return "in " + days + " days"
    if (days < -1 && days > -7) return (-days) + " days ago"
    return iso.substr(0, 10)
}
