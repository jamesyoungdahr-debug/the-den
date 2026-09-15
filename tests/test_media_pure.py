"""M49 checks without a database: probe summaries, codec strings and notes, subtitle conversion. Run from the repo root."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import media_probe, playability, subtitle_tracks

fails = []

def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ("" if ok else f"  got={got!r} want={want!r}"))
    if not ok:
        fails.append(name)

# Section 1: media_probe.summarise

RAW = {
    "format": {"format_name": "matroska,webm", "duration": "5025.123", "bit_rate": "8000000"},
    "streams": [
        {"index": 0, "codec_type": "video", "codec_name": "h264", "profile": "High", "level": 41, "pix_fmt": "yuv420p", "width": 1920, "height": 1080, "disposition": {"default": 1}},
        {"index": 1, "codec_type": "audio", "codec_name": "dts", "channels": 6, "channel_layout": "5.1(side)", "tags": {"language": "eng", "title": "DTS-HD MA"}, "disposition": {"default": 1}},
        {"index": 2, "codec_type": "audio", "codec_name": "aac", "channels": 2, "tags": {"LANGUAGE": "jpn"}, "disposition": {"default": 0}},
        {"index": 3, "codec_type": "subtitle", "codec_name": "subrip", "tags": {"language": "eng"}, "disposition": {"forced": 1}},
        {"index": 4, "codec_type": "subtitle", "codec_name": "hdmv_pgs_subtitle", "tags": {"language": "ger"}, "disposition": {}},
        {"index": 5, "codec_type": "video", "codec_name": "mjpeg", "disposition": {"attached_pic": 1}}
    ],
    "chapters": [{"start_time": "0.000000", "end_time": "300.500000", "tags": {"title": "Opening"}}]
}

S = media_probe.summarise(RAW, 12345)

check("container", S["container"], "matroska,webm")
check("duration_ms", S["duration_ms"], 5025123)
check("bit_rate", S["bit_rate"], 8000000)
check("size", S["size"], 12345)
check("video codec", S["video"]["codec"], "h264")
check("video index (attached pic skipped)", S["video"]["index"], 0)
check("video level", S["video"]["level"], 41)
check("bit_depth", S["video"]["bit_depth"], 8)
check("hdr", S["video"]["hdr"], "sdr")
check("len(audio)", len(S["audio"]), 2)
check("audio[0] default", S["audio"][0]["default"], True)
check("audio[1] language (case-insensitive tag keys)", S["audio"][1]["language"], "jpn")
check("audio[0] title", S["audio"][0]["title"], "DTS-HD MA")
check("subtitles[0] kind text", S["subtitles"][0]["kind"], "text")
check("subtitles[0] forced", S["subtitles"][0]["forced"], True)
check("subtitles[1] kind image", S["subtitles"][1]["kind"], "image")
check("chapters", S["chapters"], [{"start_ms": 0, "end_ms": 300500, "title": "Opening"}])

# HDR and bit depth helpers
check("_hdr smpte2084 -> hdr10", media_probe._hdr({"color_transfer": "smpte2084"}), "hdr10")
check("_hdr arib-std-b67 -> hlg", media_probe._hdr({"color_transfer": "arib-std-b67"}), "hlg")
check("_hdr smpte2084 + DOVI -> dv", media_probe._hdr({"color_transfer": "smpte2084", "side_data_list": [{"side_data_type": "DOVI configuration record"}]}), "dv")
check("_hdr empty -> sdr", media_probe._hdr({}), "sdr")
check("_bit_depth yuv420p10le -> 10", media_probe._bit_depth({"pix_fmt": "yuv420p10le"}), 10)
check("_bit_depth bits_per_raw_sample 12 -> 12", media_probe._bit_depth({"bits_per_raw_sample": "12"}), 12)
check("_bit_depth yuv420p -> 8", media_probe._bit_depth({"pix_fmt": "yuv420p"}), 8)

# Video level -99 gives None
RAW_NEG_LEVEL = dict(RAW)
RAW_NEG_LEVEL["streams"] = list(RAW["streams"])
RAW_NEG_LEVEL["streams"][0] = dict(RAW["streams"][0])
RAW_NEG_LEVEL["streams"][0]["level"] = -99
S_NEG = media_probe.summarise(RAW_NEG_LEVEL, 12345)
check("summarise level -99 -> None", S_NEG["video"]["level"], None)

# Empty probe
EMPTY_S = media_probe.summarise({}, 0)
check("empty summarise video is None", EMPTY_S["video"], None)
check("empty summarise audio []", EMPTY_S["audio"], [])
check("empty summarise subtitles []", EMPTY_S["subtitles"], [])
check("empty summarise chapters []", EMPTY_S["chapters"], [])
check("empty summarise duration_ms is None", EMPTY_S["duration_ms"], None)

# Section 2: playability

check("video_codec_string h264 High 41", playability.video_codec_string({"codec": "h264", "profile": "High", "level": 41}), "avc1.640029")
check("video_codec_string h264 Main 30", playability.video_codec_string({"codec": "h264", "profile": "Main", "level": 30}), "avc1.4D001E")
check("video_codec_string h264 Weird is None", playability.video_codec_string({"codec": "h264", "profile": "Weird", "level": 30}), None)
check("video_codec_string hevc Main 10 150", playability.video_codec_string({"codec": "hevc", "profile": "Main 10", "level": 150}), "hvc1.2.4.L150.B0")
check("video_codec_string hevc level None is None", playability.video_codec_string({"codec": "hevc", "profile": "Main", "level": None}), None)
check("video_codec_string vp9 10-bit", playability.video_codec_string({"codec": "vp9", "bit_depth": 10}), "vp09.02.10.10")
check("video_codec_string av1 8-bit", playability.video_codec_string({"codec": "av1", "bit_depth": 8}), "av01.0.08M.08")
check("video_codec_string mpeg2video is None", playability.video_codec_string({"codec": "mpeg2video"}), None)

check("audio_codec_string AAC", playability.audio_codec_string("AAC"), "mp4a.40.2")
check("audio_codec_string dts is None", playability.audio_codec_string("dts"), None)

check("mime_type mp4 .mp4", playability.mime_type("mov,mp4,m4a,3gp,3g2,mj2", ".mp4"), "video/mp4")
check("mime_type matroska .webm", playability.mime_type("matroska,webm", ".webm"), "video/webm")
check("mime_type matroska .mkv", playability.mime_type("matroska,webm", ".mkv"), "video/x-matroska")
check("mime_type None .mkv", playability.mime_type(None, ".mkv"), "video/x-matroska")
check("mime_type avi .avi", playability.mime_type("avi", ".avi"), "video/x-msvideo")

MP4 = {"container": "mov,mp4,m4a,3gp,3g2,mj2", "video": {"codec": "h264", "profile": "High", "level": 41, "bit_depth": 8, "hdr": "sdr"}, "audio": [{"codec": "aac", "default": True}], "subtitles": []}

check("browser_type MP4 .mp4", playability.browser_type(MP4, ".mp4"), 'video/mp4; codecs="avc1.640029,mp4a.40.2"')
check("direct_play_notes MP4 empty", playability.direct_play_notes(MP4), [])

check("browser_type S .mkv (dts no codec string)", playability.browser_type(S, ".mkv"), "video/x-matroska")

check("browser_type MP4 no audio", playability.browser_type({**MP4, "audio": []}, ".mp4"), 'video/mp4; codecs="avc1.640029"')

notes = playability.direct_play_notes(S)
check("direct_play_notes S: dts warning", any("Audio codec dts does not play in web browsers." in n for n in notes), True)
check("direct_play_notes S: default audio only", any("Only the default audio track plays until transcoding arrives." in n for n in notes), True)
check("direct_play_notes S: PGS subtitles", any("Picture-based subtitles (PGS or VobSub) can't be shown yet." in n for n in notes), True)

hevc_mp4 = {**MP4, "video": {"codec": "hevc", "profile": "Main 10", "level": 150, "bit_depth": 10, "hdr": "hdr10"}}
notes_hevc = playability.direct_play_notes(hevc_mp4)
check("direct_play_notes HEVC: hardware decoding note", any("HEVC video plays only in browsers with hardware HEVC decoding." in n for n in notes_hevc), True)
check("direct_play_notes HEVC: HDR tone mapping note", any("HDR video is shown without tone mapping, so colours may look washed out on SDR screens." in n for n in notes_hevc), True)

h264_10bit = {**MP4, "video": {"codec": "h264", "profile": "High 10", "level": 51, "bit_depth": 10, "hdr": "sdr"}}
notes_h264_10 = playability.direct_play_notes(h264_10bit)
check("direct_play_notes H.264 10-bit warning", any("10-bit H.264 does not play in web browsers." in n for n in notes_h264_10), True)

eac3_mp4 = {**MP4, "audio": [{"codec": "eac3", "default": True}]}
notes_eac3 = playability.direct_play_notes(eac3_mp4)
check("direct_play_notes eac3 warning", any("Audio codec eac3 plays only in some browsers." in n for n in notes_eac3), True)

# Section 3: subtitle_tracks

check("parse_tail en", subtitle_tracks.parse_tail("en"), {"language": "en", "forced": False, "sdh": False})
check("parse_tail en.forced", subtitle_tracks.parse_tail("en.forced"), {"language": "en", "forced": True, "sdh": False})
check("parse_tail eng.sdh", subtitle_tracks.parse_tail("eng.sdh"), {"language": "eng", "forced": False, "sdh": True})
check("parse_tail pt-br", subtitle_tracks.parse_tail("pt-br"), {"language": "pt-br", "forced": False, "sdh": False})
check("parse_tail empty string", subtitle_tracks.parse_tail(""), {"language": None, "forced": False, "sdh": False})

check("track_label en forced", subtitle_tracks.track_label("en", None, True, False), "EN (forced)")
check("track_label None", subtitle_tracks.track_label(None), "Unknown")
check("track_label with title", subtitle_tracks.track_label("en", "Commentary"), "Commentary")

SRT = b"\xef\xbb\xbf1\r\n1:02:03,456 --> 01:02:05,000\r\n{\\an8}Hello\r\n\r\n2\r\n01:02:06,000 --> 01:02:07,000\r\nWorld\r\n"
vtt = subtitle_tracks.srt_to_webvtt(SRT)

check("srt_to_webvtt starts with WEBVTT", vtt.startswith("WEBVTT\n\n"), True)
check("srt_to_webvtt timestamp converted", "01:02:03.456 --> 01:02:05.000" in vtt, True)
check("srt_to_webvtt no ASS tags", "{\\an8}" not in vtt, True)
check("srt_to_webvtt no CR", "\r" not in vtt, True)
check("srt_to_webvtt contains Hello", "Hello" in vtt, True)
check("srt_to_webvtt ends with newline", vtt.endswith("\n"), True)

cp1252_vtt = subtitle_tracks.srt_to_webvtt("1\n00:00:01,000 --> 00:00:02,000\nCaf\xe9\n".encode("cp1252"))
check("srt_to_webvtt cp1252 encoding", "Café" in cp1252_vtt, True)

already_vtt = subtitle_tracks.srt_to_webvtt(b"WEBVTT\n\n00:01.000 --> 00:02.000\nHi")
check("srt_to_webvtt already VTT passthrough", already_vtt, "WEBVTT\n\n00:01.000 --> 00:02.000\nHi\n")

embedded = subtitle_tracks.embedded_track_lists(S)
check("embedded_track_lists S embedded tracks", embedded[0], [{"id": "e3", "source": "embedded", "language": "eng", "label": "ENG (forced)", "forced": True, "default": False}])
check("embedded_track_lists S external labels", embedded[1], ["GER"])

check("embedded_track_lists None", subtitle_tracks.embedded_track_lists(None), ([], []))

print(f"\n{len(fails)} FAILURE(S)" if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
