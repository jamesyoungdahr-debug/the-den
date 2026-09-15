/* Watch-page player. No framework, no build step. */
(function () {
  var root = document.querySelector(".den-watch");
  if (!root) return;

  var infoUrl = root.getAttribute("data-info-url");
  var video = root.querySelector("video.den-video");
  var messageBox = root.querySelector("[data-message]");
  var messageTitle = root.querySelector("[data-message-title]");
  var messageBody = root.querySelector("[data-message-body]");
  var tryAnywayBtn = root.querySelector("[data-try-anyway]");
  var convertBtn = root.querySelector("[data-convert]");
  var resumeBox = root.querySelector("[data-resume-box]");
  var resumeTimeEl = root.querySelector("[data-resume-time]");
  var resumeBtn = root.querySelector("[data-resume]");
  var startOverBtn = root.querySelector("[data-start-over]");
  var nextBox = root.querySelector("[data-next-box]");
  var nextLabel = root.querySelector("[data-next-label]");
  var nextLink = root.querySelector("[data-next-link]");
  var watchedBtn = root.querySelector("[data-toggle-watched]");
  var techEl = root.querySelector("[data-tech]");
  var notesEl = root.querySelector("[data-notes]");
  var notesList = root.querySelector("ul[data-notes-list]");

  var state = {};

  /* fmtTime: h:mm:ss when an hour or more, else m:ss */
  function fmtTime(ms) {
    var s = Math.floor(ms / 1000);
    var h = Math.floor(s / 3600);
    if (h >= 1) {
      return h + ":" + pad(Math.floor((s % 3600) / 60)) + ":" + pad(s % 60);
    }
    return Math.floor(s / 60) + ":" + pad(s % 60);
  }

  function pad(n) {
    return n < 10 ? "0" + n : "" + n;
  }

  /* showMessage */
  function showMessage(title, body, allowTry) {
    messageTitle.textContent = title;
    messageBody.textContent = body;
    tryAnywayBtn.hidden = !allowTry;
    messageBox.hidden = false;
  }

  /* seekTo: set currentTime now or on loadedmetadata */
  function seekTo(seconds) {
    if (video.readyState >= 1) {
      video.currentTime = seconds;
    } else {
      var handler = function () {
        video.removeEventListener("loadedmetadata", handler);
        video.currentTime = seconds;
      };
      video.addEventListener("loadedmetadata", handler);
    }
  }

  /* send progress event */
  function sendEvent(event, beacon) {
    if (!isFinite(video.duration) || video.duration <= 0) return;
    var body = JSON.stringify({
      position_ms: Math.round(video.currentTime * 1000),
      duration_ms: Math.round(video.duration * 1000),
      event: event,
      device: "web"
    });
    if (beacon && navigator.sendBeacon) {
      navigator.sendBeacon(infoUrl + "/progress", new Blob([body], { type: "application/json" }));
      return;
    }
    fetch(infoUrl + "/progress", {
      method: "POST",
      credentials: "same-origin",
      keepalive: true,
      headers: { "Content-Type": "application/json" },
      body: body
    }).then(function (resp) {
      if (!resp.ok) return;
      return resp.json();
    }).then(function (newState) {
      if (newState) {
        state = newState;
        watchedBtn.textContent = newState.played ? "Mark as unwatched" : "Mark as watched";
      }
    }).catch(function () {});
  }

  /* Fetch info and boot everything */
  fetch(infoUrl, { credentials: "same-origin", headers: { Accept: "application/json" } })
    .then(function (resp) {
      if (!resp.ok) {
        return resp.json().then(function (err) {
          return Promise.reject(new Error((err && err.detail) || ("Error " + resp.status)));
        }, function () {
          return Promise.reject(new Error("Error " + resp.status));
        });
      }
      return resp.json();
    })
    .then(function (info) {
      /* Tech line */
      var parts = [];
      if (info.video) {
        parts.push(info.video.width + "\u00d7" + info.video.height);
        var codecStr = info.video.codec;
        if (info.video.bit_depth > 8) codecStr += " 10-bit";
        if (info.video.hdr && info.video.hdr !== "sdr") codecStr += " HDR";
        parts.push(codecStr);
      }
      var defaultAudio = null;
      if (info.audio) {
        for (var i = 0; i < info.audio.length; i++) {
          if (info.audio[i].default) { defaultAudio = info.audio[i]; break; }
        }
        if (!defaultAudio && info.audio.length > 0) defaultAudio = info.audio[0];
      }
      if (defaultAudio) {
        parts.push(defaultAudio.codec + " " + defaultAudio.channels + "ch");
      }
      if (!info.probed) {
        parts.push("Codec details unavailable");
      }
      techEl.textContent = parts.join(" \u00b7 ");

      /* Notes */
      var items = info.notes ? info.notes.slice() : [];
      if (info.unavailable_subtitles && info.unavailable_subtitles.length > 0) {
        items.push("Not shown: " + info.unavailable_subtitles.join(", "));
      }
      if (items.length > 0) {
        for (var j = 0; j < items.length; j++) {
          var li = document.createElement("li");
          li.textContent = items[j];
          notesList.appendChild(li);
        }
        notesEl.hidden = false;
      }

      /* Subtitles */
      if (info.subtitles) {
        for (var k = 0; k < info.subtitles.length; k++) {
          var s = info.subtitles[k];
          var track = document.createElement("track");
          track.kind = "subtitles";
          track.label = s.label || "";
          track.srclang = s.language || "";
          track.src = s.url;
          if (s.default) track.default = true;
          video.appendChild(track);
        }
      }

      /* Watched button */
      state = info.state || {};
      watchedBtn.textContent = state.played ? "Mark as unwatched" : "Mark as watched";
      watchedBtn.hidden = false;

      /* canPlay check */
      var canPlay = "maybe";
      if (info.type) {
        canPlay = video.canPlayType(info.type);
        if (canPlay === "" && info.type.indexOf("video/x-matroska") === 0) {
          canPlay = video.canPlayType(info.type.replace("video/x-matroska", "video/webm"));
        }
      }

      /* start: set src and offer resume */
      function start() {
        video.src = info.stream_url;
        var pos = state.position_ms || 0;
        if (pos > 0) {
          resumeTimeEl.textContent = fmtTime(pos);
          resumeBox.hidden = false;
        }
      }

      /* Resume / Start over */
      resumeBtn.addEventListener("click", function () {
        resumeBox.hidden = true;
        seekTo((state.position_ms || 0) / 1000);
        playQuietly();
      });
      startOverBtn.addEventListener("click", function () {
        resumeBox.hidden = true;
        seekTo(0);
        playQuietly();
      });

      /* play() rejects when a pause or a new source interrupts it; that's not an error worth logging */
      function playQuietly() {
        var promise = video.play();
        if (promise && promise.catch) promise.catch(function () {});
      }

      /* If user presses play while resume box is shown, just hide it */
      video.addEventListener("play", function () {
        if (!resumeBox.hidden) {
          resumeBox.hidden = true;
        }
      }, { once: false });

      /* When the browser cannot take the file, play_info says why and whether a converted copy
         is already cached. Converting is opt-in: it costs the server real time, so it happens
         because somebody asked, never automatically. */
      function startConverted() {
        video.src = info.converted_url;
        var pos = state.position_ms || 0;
        if (pos > 0) {
          resumeTimeEl.textContent = fmtTime(pos);
          resumeBox.hidden = false;
        }
      }

      function pollConvert() {
        fetch(info.convert_url, { credentials: "same-origin" })
          .then(function (r) { return r.ok ? r.json() : null; })
          .then(function (s) {
            if (!s) { setTimeout(pollConvert, 3000); return; }
            if (s.state === "ready") {
              messageBox.hidden = true;
              startConverted();
              playQuietly();
              return;
            }
            if (s.state === "failed") {
              showMessage("Converting failed", s.error || "ffmpeg could not convert this file. The server log has the detail.", false);
              return;
            }
            if (s.state === "none") {
              showMessage("Converting stopped", "The server is no longer working on this file. Try again.", false);
              return;
            }
            messageBody.textContent = "Converting for this browser" +
              (s.progress == null ? "" : " \u2014 " + Math.round(s.progress * 100) + "%") +
              " (you can leave this page; the server keeps working)";
            setTimeout(pollConvert, 1500);
          })
          .catch(function () { setTimeout(pollConvert, 3000); });
      }

      if (info.converted) {
        startConverted();
      } else if (canPlay === "") {
        var why = info.playback && info.playback.reason ? info.playback.reason : "this file is not one a browser plays";
        showMessage(
          "Your browser can't play this file directly",
          (info.notes && info.notes.length ? info.notes.join(" ") + " " : "") +
            "The Den can convert it: " + why + ".",
          true
        );
        convertBtn.hidden = false;
        convertBtn.addEventListener("click", function () {
          convertBtn.hidden = true;
          messageBody.textContent = "Starting\u2026";
          fetch(info.convert_url, { method: "POST", credentials: "same-origin" })
            .then(function () { pollConvert(); })
            .catch(function () { messageBody.textContent = "Could not start the conversion. The server log has the detail."; });
        });
        tryAnywayBtn.addEventListener("click", function () {
          messageBox.hidden = true;
          start();
        });
      } else {
        start();
      }

      /* Progress reporting events */
      var firstPlaySent = false;
      video.addEventListener("play", function () {
        if (!firstPlaySent) {
          firstPlaySent = true;
          sendEvent("start", false);
        }
      });

      var progressInterval = setInterval(function () {
        if (!video.paused && !video.ended) {
          sendEvent("progress", false);
        }
      }, 10000);

      video.addEventListener("pause", function () {
        if (!video.ended) {
          sendEvent("pause", false);
        }
      });

      video.addEventListener("seeked", function () {
        sendEvent("seek", false);
      });

      video.addEventListener("ended", function () {
        sendEvent("stop", false);
        clearInterval(progressInterval);
        if (info.next) {
          nextLabel.textContent = info.next.label;
          nextLink.href = info.next.href;
          nextBox.hidden = false;
        }
      });

      /* pagehide sends stop with beacon */
      window.addEventListener("pagehide", function () {
        sendEvent("stop", true);
        clearInterval(progressInterval);
      });

      /* visibilitychange hidden sends pause with beacon */
      document.addEventListener("visibilitychange", function () {
        if (document.visibilityState === "hidden") {
          sendEvent("pause", true);
        }
      });

      /* video error */
      video.addEventListener("error", function () {
        showMessage(
          "Playback failed",
          "The browser stopped with media error " + (video.error ? video.error.code : "?") + ". " + (info.notes ? info.notes.join(" ") : ""),
          false
        );
      });

    })
    .catch(function (err) {
      showMessage("This title can't be played", err.message || String(err), false);
    });

  /* Watched toggle */
  watchedBtn.addEventListener("click", function () {
    var currentPlayed = state.played;
    fetch(infoUrl + "/watched", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ played: !currentPlayed })
    }).then(function (resp) {
      if (!resp.ok) throw new Error("not ok");
      return resp.json();
    }).then(function (newState) {
      state = newState;
      watchedBtn.textContent = newState.played ? "Mark as unwatched" : "Mark as watched";
      window.denToast(newState.played ? "Marked as watched" : "Marked as unwatched", "positive");
    }).catch(function () {
      window.denToast("Couldn't update watched state", "warning");
    });
  });

})();
