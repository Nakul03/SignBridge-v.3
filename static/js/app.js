(function () {
  "use strict";

  const video = document.getElementById("video");
  const canvas = document.getElementById("canvas");
  const ctx = canvas ? canvas.getContext("2d") : null;
  const btnCam = document.getElementById("btn-cam");
  const btnStop = document.getElementById("btn-stop");
  const btnTts = document.getElementById("btn-tts");
  const camSection = document.getElementById("cam-section");
  const camStatus = document.getElementById("cam-status");
  const outputText = document.getElementById("output-text");
  const outputConf = document.getElementById("output-confidence");
  const outputBox = document.getElementById("output-box");
  const langSelect = document.getElementById("lang");
  const sentenceBox = document.getElementById("sentence-box");
  const btnSpeakSentence = document.getElementById("btn-speak-sentence");
  const btnClearSentence = document.getElementById("btn-clear-sentence");
  const btnNextWord = document.getElementById("btn-next-word");
  const brailleCheck = document.getElementById("braille-vibrate");
  const suggestionList = document.getElementById("suggestion-list");

  // Camera only works over HTTPS or localhost (secure context)
  function canUseCamera() {
    if (!window.isSecureContext) return false;
    if (!navigator.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== "function") return false;
    return true;
  }

  let stream = null;
  let animationId = null;
  let cameraRunning = false;
  let lastSign = null;
  let lastConf = 0;
  const SEND_INTERVAL_MS = 140;
  const MIN_CONF = 0.55;
  const MIN_CONF_SPACE = 0.82;
  const MIN_STABLE_COUNT = 4;
  let lastSendTime = 0;
  const SMOOTH_COUNT = 7;
  const SPACE_REQUIRED_COUNT = 6;
  const SPACE_MUST_LEAD_BY = 4;
  let recentPredictions = [];
  let sentenceWords = [];
  let currentWord = [];
  let logicalSentence = null;
  let lastAddedSign = null;
  let lastSpaceCommitTime = 0;
  const SPACE_COOLDOWN_MS = 900;

  const WORD_SUGGESTIONS = [
    "HELLO", "HELP", "HOME", "HOUSE", "HOW", "GOOD", "MORNING", "NIGHT", "NAME",
    "PLEASE", "SORRY", "THANK YOU", "WELCOME", "WATER", "FOOD", "FRIEND",
    "FAMILY", "SCHOOL", "WORK", "LOVE", "YES", "NO", "WAIT", "STOP", "GO", "COME"
  ];

  const SENTENCE_SUGGESTIONS = [
    "HELLO HOW ARE YOU",
    "PLEASE HELP ME",
    "WHAT IS YOUR NAME",
    "I NEED WATER",
    "I NEED FOOD",
    "GOOD MORNING",
    "THANK YOU",
    "PLEASE WAIT",
    "I LOVE MY FAMILY",
    "WHERE IS MY FRIEND",
    "I DO NOT UNDERSTAND",
    "I WANT TO GO HOME"
  ];

  const STARTER_SUGGESTIONS = [
    "HELLO",
    "PLEASE HELP ME",
    "WHAT IS YOUR NAME",
    "I NEED WATER",
    "THANK YOU",
    "GOOD MORNING"
  ];

  function setStatus(msg) {
    camStatus.textContent = msg;
  }

  function getLang() {
    return langSelect.value || "en";
  }

  // Build current word with no spaces between signs (words connect until you show Space)
  function currentWordSegment() {
    return currentWord.map(function (s) { return String(s).replace(/\s+/g, ""); }).join("");
  }

  function currentSentenceText() {
    const sentence = sentenceWords.join(" ");
    const current = currentWordSegment();
    return sentence + (sentence && current ? " " : "") + current;
  }

  function isSingleCharacterSign(sign) {
    return /^[A-Z0-9]$/.test(String(sign || "").trim());
  }

  function displayForSign(sign) {
    const display = typeof getDisplaySign !== "undefined" ? getDisplaySign(sign, getLang()) : sign;
    return String(display || "").trim();
  }

  function renderSuggestions() {
    if (!suggestionList) return;
    const current = currentWordSegment().toUpperCase();
    const fullText = currentSentenceText().toUpperCase().trim();
    const suggestions = [];

    if (!current && !fullText) {
      STARTER_SUGGESTIONS.forEach(function (value) {
        suggestions.push({ kind: value.indexOf(" ") === -1 ? "word" : "sentence", value: value });
      });
    }

    if (current) {
      WORD_SUGGESTIONS.forEach(function (word) {
        if (word.replace(/\s+/g, "").startsWith(current.replace(/\s+/g, "")) && word !== current) {
          suggestions.push({ kind: "word", value: word });
        }
      });

      if (suggestions.length < 3) {
        WORD_SUGGESTIONS.forEach(function (word) {
          if (word.indexOf(current[0]) === 0 && word !== current) {
            suggestions.push({ kind: "word", value: word });
          }
        });
      }
    }

    if (fullText) {
      SENTENCE_SUGGESTIONS.forEach(function (sentence) {
        if (sentence.startsWith(fullText) && sentence !== fullText) {
          suggestions.push({ kind: "sentence", value: sentence });
        }
      });
    }

    const unique = [];
    suggestions.forEach(function (item) {
      if (!unique.some(function (existing) { return existing.kind === item.kind && existing.value === item.value; })) {
        unique.push(item);
      }
    });

    if (!unique.length) {
      suggestionList.innerHTML = '<p class="suggestion-empty">Show signs to get word and sentence suggestions.</p>';
      return;
    }

    suggestionList.innerHTML = unique.slice(0, 6).map(function (item) {
      return '<button type="button" class="suggestion-chip" data-kind="' +
        item.kind + '" data-value="' + item.value.replace(/"/g, "&quot;") + '">' +
        item.value + '</button>';
    }).join("");
  }

  function applySuggestion(kind, value) {
    if (!value) return;
    const cleanValue = value.trim();
    if (kind === "sentence") {
      sentenceWords = cleanValue.split(/\s+/);
      currentWord = [];
    } else {
      currentWord = [];
      if (!sentenceWords.length || sentenceWords[sentenceWords.length - 1] !== cleanValue) {
        sentenceWords.push(cleanValue);
      }
    }
    lastAddedSign = null;
    updateSentenceDisplay();
  }

  function showOutput(sign, confidence) {
    const lang = getLang();
    const display = typeof getDisplaySign !== "undefined" ? getDisplaySign(sign, lang) : sign;
    outputText.textContent = display || "-";
    outputText.classList.toggle("pop", !!sign && sign !== lastSign);

    var isSpace = sign && sign.toLowerCase() === "space";
    var confOkForLetter = sign && sign !== lastAddedSign && confidence >= MIN_CONF;
    var confOkForSpace = isSpace && confidence >= MIN_CONF_SPACE;
    if (confOkForLetter || confOkForSpace) {
      var brailleEl = document.getElementById("braille-vibrate");
      if (typeof vibrateForSign === "function" && brailleEl && brailleEl.checked) {
        vibrateForSign(sign);
      }
      if (isSpace && confOkForSpace) {
        var now = Date.now();
        if (now - lastSpaceCommitTime >= SPACE_COOLDOWN_MS && sign !== lastAddedSign && currentWord.length > 0) {
          sentenceWords.push(currentWordSegment());
          currentWord = [];
          lastSpaceCommitTime = now;
        }
        lastAddedSign = sign;
        logicalSentence = null;
        updateSentenceDisplay();
      } else if (!isSpace && confOkForLetter) {
        const cleanDisplay = displayForSign(sign);
        if (isSingleCharacterSign(sign)) {
          currentWord.push(cleanDisplay);
        } else {
          const pendingWord = currentWordSegment();
          if (pendingWord) sentenceWords.push(pendingWord);
          sentenceWords.push(cleanDisplay);
          currentWord = [];
        }
        lastAddedSign = sign;
        logicalSentence = null;
        updateSentenceDisplay();
      }
    }

    if (!sign) lastAddedSign = null;
    lastSign = sign;
    lastConf = confidence;
    if (confidence > 0) {
      outputConf.textContent = "Confidence: " + Math.round(confidence * 100) + "%";
      outputConf.removeAttribute("aria-hidden");
    } else {
      outputConf.textContent = "";
      outputConf.setAttribute("aria-hidden", "true");
    }
  }

  function doSpeak(text, langCode) {
    if (!text || !text.trim()) return;
    if (!window.speechSynthesis) return;
    var ttsLang = typeof getTTSLang !== "undefined" ? getTTSLang(langCode) : "en-IN";
    window.speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance(text.trim());
    u.lang = ttsLang;
    u.rate = 0.92;
    u.volume = 1;
    u.pitch = 1;
    function speakNow() {
      var voices = window.speechSynthesis.getVoices();
      var preferred = voices.filter(function (v) { return v.lang === ttsLang || (v.lang && v.lang.startsWith(ttsLang.split("-")[0])); })[0];
      if (preferred) u.voice = preferred;
      try {
        window.speechSynthesis.speak(u);
      } catch (e) {
        u.lang = "en-IN";
        window.speechSynthesis.speak(u);
      }
    }
    setTimeout(speakNow, 150);
  }

  function speakCurrent() {
    var text = outputText.textContent;
    if (!text || text === "-") return;
    doSpeak(text, getLang());
  }

  function updateSentenceDisplay() {
    if (!sentenceBox) return;
    const displayText = currentSentenceText();
    sentenceBox.textContent = displayText || "-";
    sentenceBox.classList.toggle("empty", !displayText);
    renderSuggestions();
  }

  function speakSentence() {
    const textToSpeak = currentSentenceText();
    if (!textToSpeak || !textToSpeak.trim()) return;
    doSpeak(textToSpeak, getLang());
  }

  function clearSentence() {
    sentenceWords = [];
    currentWord = [];
    logicalSentence = null;
    lastAddedSign = null;
    updateSentenceDisplay();
  }

  function captureAndSend() {
    if (!stream || !video.videoWidth) return;
    const now = Date.now();
    if (now - lastSendTime < SEND_INTERVAL_MS) return;
    lastSendTime = now;

    const w = video.videoWidth;
    const h = video.videoHeight;
    const offscreen = document.createElement("canvas");
    offscreen.width = w;
    offscreen.height = h;
    offscreen.getContext("2d").drawImage(video, 0, 0);
    const dataUrl = offscreen.toDataURL("image/jpeg", 0.85);

    fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: dataUrl }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.error) {
          setStatus("Error: " + data.error);
          return;
        }
        const sign = data.sign != null ? String(data.sign).trim() : null;
        const conf = Number(data.confidence) || 0;
        recentPredictions.push({ sign: sign || null, conf });
        if (recentPredictions.length > SMOOTH_COUNT) recentPredictions.shift();
        const bySign = {};
        recentPredictions.forEach((p) => {
          if (p.sign && p.conf >= MIN_CONF) {
            const s = p.sign.toLowerCase() === "space" ? "Space" : p.sign;
            bySign[s] = (bySign[s] || 0) + 1;
          }
        });
        let best = null;
        let bestCount = 0;
        Object.keys(bySign).forEach((s) => {
          if (bySign[s] > bestCount) {
            bestCount = bySign[s];
            best = s;
          }
        });
        // Only show/commit a sign when it's stable (appears in enough frames) — reduces inaccurate flips
        if (best !== null && best !== "Space" && bestCount < MIN_STABLE_COUNT) {
          best = null;
          bestCount = 0;
        }
        var rejectedDueToSpace = false;
        // Only accept Space when you clearly hold the sign — no space between words otherwise
        if (best === "Space") {
          var secondBestCount = 0;
          Object.keys(bySign).forEach(function (s) {
            if (s !== "Space" && bySign[s] > secondBestCount) secondBestCount = bySign[s];
          });
          var spaceWinsClearly = (bestCount - secondBestCount) >= SPACE_MUST_LEAD_BY;
          if (bestCount < SPACE_REQUIRED_COUNT || !spaceWinsClearly) {
            best = null;
            bestCount = 0;
            rejectedDueToSpace = true;
          } else {
            var spaceConf = recentPredictions
              .filter(function (p) { return p.sign && p.sign.toLowerCase() === "space"; })
              .reduce(function (a, p) { return a + p.conf; }, 0) / bestCount;
            if (spaceConf < MIN_CONF_SPACE) {
              best = null;
              bestCount = 0;
              rejectedDueToSpace = true;
            }
          }
        }
        // If we rejected Space (not instability), show the next-best sign so the display doesn't go blank
        if (best === null && rejectedDueToSpace && Object.keys(bySign).length > 0) {
          var nextBest = null;
          var nextBestCount = 0;
          Object.keys(bySign).forEach(function (s) {
            if (s !== "Space" && bySign[s] > nextBestCount) {
              nextBestCount = bySign[s];
              nextBest = s;
            }
          });
          if (nextBest !== null) {
            best = nextBest;
            bestCount = nextBestCount;
          }
        }
        const smoothConf = bestCount
          ? recentPredictions
              .filter((p) => (p.sign && p.sign.toLowerCase() === "space" ? "Space" : p.sign) === best)
              .reduce((a, p) => a + p.conf, 0) / bestCount
          : 0;
        showOutput(best, best ? smoothConf : 0);
      })
      .catch(() => setStatus("Network error"));
  }

  function drawOverlay() {
    if (!ctx || !canvas.width || !canvas.height) return;
    ctx.save();
    ctx.font = "bold 32px DM Sans, system-ui, sans-serif";
    ctx.fillStyle = "rgba(30, 58, 95, 0.9)";
    ctx.strokeStyle = "#fbbf24";
    ctx.lineWidth = 2;
    const text = outputText.textContent;
    if (text && text !== "—") {
      const x = 20;
      const y = 50;
      ctx.strokeText(text, x, y);
      ctx.fillText(text, x, y);
    }
    ctx.restore();
  }

  function tick() {
    if (!stream || !video || !video.videoWidth) return;
    captureAndSend();
    if (!canvas || !ctx) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);
    drawOverlay();
    animationId = requestAnimationFrame(tick);
  }

  function startCamera() {
    if (stream) return;
    if (!canUseCamera()) {
      setStatus("Camera needs a secure page. Please open this site at: http://127.0.0.1:5000 (do not use file://).");
      return;
    }
    if (!video || !camStatus) return;
    setStatus("Requesting camera permission… Allow when the browser asks.");
    // Scroll so user sees the camera area and permission prompt
    if (camSection) camSection.scrollIntoView({ behavior: "smooth", block: "center" });
    navigator.mediaDevices
      .getUserMedia({ video: { width: 640, height: 480 }, audio: false })
      .then((s) => {
        stream = s;
        cameraRunning = true;
        btnCam.textContent = "Stop Camera";
        video.srcObject = s;
        video.onloadedmetadata = function onMeta() {
          video.play().then(function () {
            setStatus("Show your hand(s) — A–Z or 0–9");
            recentPredictions = [];
            lastSign = null;
            showOutput(null, 0);
            animationId = requestAnimationFrame(tick);
            if (typeof testVibrate === "function") {
              var br = document.getElementById("braille-vibrate");
              if (br && br.checked) testVibrate();
            }
          }).catch(function () {
            setStatus("Video play failed — try clicking the page first.");
            animationId = requestAnimationFrame(tick);
          });
        };
        video.onerror = function () {
          setStatus("Video error. Try another browser or allow camera.");
        };
      })
      .catch((err) => {
        var msg = err.message || err.name || "Permission denied";
        if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
          msg = "Camera blocked. Please allow camera access for this site and try again.";
        } else if (err.name === "NotFoundError") {
          msg = "No camera found. Connect a camera and refresh.";
        }
        setStatus("Camera error: " + msg);
        camStatus.setAttribute("role", "alert");
      });
  }

  function stopCamera() {
    if (animationId) {
      cancelAnimationFrame(animationId);
      animationId = null;
    }
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
      stream = null;
    }
    cameraRunning = false;
    btnCam.textContent = "Start Camera";
    video.srcObject = null;
    video.removeAttribute("src");
    video.load();
    if (ctx && canvas) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      canvas.width = 0;
      canvas.height = 0;
    }
    recentPredictions = [];
    lastSign = null;
    lastConf = 0;
    showOutput(null, 0);
    if (camStatus) setStatus("Camera stopped. Press Start Camera to begin again.");
    btnCam.focus();
  }

  btnCam.addEventListener("click", function () {
    if (!camSection || !camStatus) return;
    if (cameraRunning || stream) {
      stopCamera();
      return;
    }
    camSection.classList.remove("hidden");
    camStatus.setAttribute("role", "status");
    camStatus.textContent = "Opening…";
    startCamera();
  });

  btnStop.addEventListener("click", stopCamera);

  if (brailleCheck) {
    brailleCheck.addEventListener("change", function () {
      if (brailleCheck.checked && typeof testVibrate === "function") testVibrate();
    });
  }

  btnTts.addEventListener("click", speakCurrent);

  if (btnSpeakSentence) btnSpeakSentence.addEventListener("click", speakSentence);
  if (btnClearSentence) btnClearSentence.addEventListener("click", clearSentence);
  if (suggestionList) {
    suggestionList.addEventListener("click", function (event) {
      const chip = event.target.closest(".suggestion-chip");
      if (!chip) return;
      applySuggestion(chip.getAttribute("data-kind"), chip.getAttribute("data-value"));
    });
  }

  function nextWord() {
    var word = currentWordSegment();
    if (!word && sentenceWords.length > 0) {
      word = sentenceWords[sentenceWords.length - 1];
      if (word) {
        sentenceWords.pop();
        updateSentenceDisplay();
      }
    }
    if (word) {
      doSpeak(word, getLang());
      sentenceWords.push(word);
      currentWord = [];
      lastAddedSign = null;
      updateSentenceDisplay();
    }
  }
  if (btnNextWord) btnNextWord.addEventListener("click", nextWord);

  langSelect.addEventListener("change", function () {
    if (lastSign) {
      const lang = getLang();
      const display = typeof getDisplaySign !== "undefined" ? getDisplaySign(lastSign, lang) : lastSign;
      outputText.textContent = display;
    }
  });

  showOutput(null, 0);
  updateSentenceDisplay();

  // Show warning if camera won't work (e.g. file:// or no getUserMedia)
  (function initCameraWarning() {
    var warning = document.getElementById("secure-warning");
    if (!warning) return;
    if (!window.isSecureContext || !navigator.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== "function") {
      warning.classList.remove("hidden");
    }
  })();
})();

