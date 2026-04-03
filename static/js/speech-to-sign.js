/**
 * Speech to Indian Sign Language (ISL).
 * Uses Web Speech API for speech-to-text, then displays ISL images/GIFs
 * from the dataset: https://github.com/satyam9090/Automatic-Indian-Sign-Language-Translator-ISL
 */
(function () {
  "use strict";

  var btnRecord = document.getElementById("btn-speech-record");
  var btnStop = document.getElementById("btn-speech-stop");
  var speechStatus = document.getElementById("speech-status");
  var speechText = document.getElementById("speech-text");
  var islDisplay = document.getElementById("isl-display");

  var islWords = {};
  var phraseKeys = [];
  var recognition = null;
  var isListening = false;
  var displayQueue = [];
  var DISPLAY_DELAY_MS = 1800;
  var LETTER_DELAY_MS = 600;

  function setStatus(msg) {
    if (speechStatus) speechStatus.textContent = msg;
  }

  function escapeHtml(s) {
    var div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  function loadIslWords() {
    fetch("/data/isl-words.json")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        islWords = data;
        phraseKeys = Object.keys(data).filter(function (k) { return k.length > 1; }).sort(function (a, b) { return b.length - a.length; });
      })
      .catch(function () {
        phraseKeys = [];
      });
  }
  loadIslWords();

  function textToSignItems(text) {
    var items = [];
    var t = (text || "").toLowerCase().replace(/\s+/g, " ").trim();
    if (!t) return items;
    var i = 0;
    while (i < t.length) {
      while (t[i] === " ") i++;
      if (i >= t.length) break;
      var matched = false;
      for (var p = 0; p < phraseKeys.length; p++) {
        var phrase = phraseKeys[p];
        var rest = t.slice(i);
        if (rest.indexOf(phrase) === 0) {
          var file = islWords[phrase];
          if (file) {
            items.push({ type: "word", key: phrase, file: file });
            i += phrase.length;
            matched = true;
            break;
          }
        }
      }
      if (matched) continue;
      var wordEnd = t.indexOf(" ", i);
      if (wordEnd === -1) wordEnd = t.length;
      var word = t.slice(i, wordEnd);
      i = wordEnd + 1;
      if (islWords[word]) {
        items.push({ type: "word", key: word, file: islWords[word] });
      } else {
        for (var c = 0; c < word.length; c++) {
          var ch = word[c];
          if (/[a-z]/.test(ch)) {
            items.push({ type: "letter", char: ch, file: ch + ".jpg" });
          }
        }
      }
    }
    return items;
  }

  function showNextInQueue() {
    if (displayQueue.length === 0) return;
    var item = displayQueue.shift();
    var url = item.type === "letter"
      ? "/speech-to-sign/letters/" + encodeURIComponent(item.file)
      : "/speech-to-sign/words/" + encodeURIComponent(item.file);
    var delay = item.type === "letter" ? LETTER_DELAY_MS : DISPLAY_DELAY_MS;
    var wrap = document.createElement("div");
    wrap.className = "isl-item";
    var label = document.createElement("span");
    label.className = "isl-item-label";
    label.textContent = item.type === "letter" ? item.char.toUpperCase() : item.key;
    var media = document.createElement(item.file.toLowerCase().endsWith(".gif") ? "img" : "img");
    media.src = url;
    media.alt = "ISL sign: " + escapeHtml(item.type === "letter" ? item.char : item.key);
    media.className = "isl-media";
    media.onerror = function () {
      wrap.classList.add("isl-error");
      label.textContent = (item.type === "letter" ? item.char : item.key) + " (image not found)";
    };
    wrap.appendChild(media);
    wrap.appendChild(label);
    if (islDisplay) {
      islDisplay.appendChild(wrap);
      islDisplay.scrollTop = islDisplay.scrollHeight;
    }
    if (displayQueue.length > 0) {
      setTimeout(showNextInQueue, delay);
    }
  }

  function showSignsForText(text) {
    var items = textToSignItems(text);
    if (items.length === 0) {
      if (islDisplay) islDisplay.innerHTML = "<p class=\"isl-empty\">No ISL assets for this text. Add letters and words from the dataset.</p>";
      return;
    }
    if (islDisplay) islDisplay.innerHTML = "";
    displayQueue = items.slice();
    showNextInQueue();
  }

  function startListening() {
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setStatus("Speech recognition not supported in this browser. Try Chrome or Edge.");
      return;
    }
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-IN";

    recognition.onstart = function () {
      isListening = true;
      if (btnRecord) btnRecord.classList.add("hidden");
      if (btnStop) btnStop.classList.remove("hidden");
      setStatus("Listening… speak now. Say \"goodbye\" or click Stop to finish.");
    };
    recognition.onend = function () {
      if (isListening) recognition.start();
    };
    recognition.onresult = function (e) {
      var last = e.results.length - 1;
      var transcript = "";
      for (var i = 0; i < e.results.length; i++) {
        if (e.results[i].isFinal) transcript += e.results[i][0].transcript;
      }
      if (transcript) {
        speechText.textContent = transcript;
        if (transcript.toLowerCase().indexOf("goodbye") !== -1) {
          stopListening();
        } else if (e.results[last].isFinal) {
          showSignsForText(transcript);
        }
      }
    };
    recognition.onerror = function (e) {
      if (e.error === "not-allowed") setStatus("Microphone access denied. Allow and try again.");
      else if (e.error !== "aborted") setStatus("Error: " + (e.error || "unknown"));
    };

    try {
      recognition.start();
    } catch (err) {
      setStatus("Could not start: " + (err.message || err));
    }
  }

  function stopListening() {
    isListening = false;
    if (recognition) {
      try { recognition.stop(); } catch (e) {}
      recognition = null;
    }
    if (btnRecord) btnRecord.classList.remove("hidden");
    if (btnStop) btnStop.classList.add("hidden");
    setStatus("Stopped. Click \"Start listening\" to speak again.");
  }

  if (btnRecord) btnRecord.addEventListener("click", function () {
    if (speechText) speechText.textContent = "—";
    if (islDisplay) islDisplay.innerHTML = "";
    startListening();
  });
  if (btnStop) btnStop.addEventListener("click", stopListening);
})();
