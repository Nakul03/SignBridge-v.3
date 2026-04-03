/**
 * Preset braille-style vibration patterns for sign language output.
 * Each sign maps to a short pattern: [ms on, ms off, ms on, ...].
 * Used with navigator.vibrate() when a sign is detected (if supported).
 */
(function (global) {
  "use strict";

  // Braille-inspired: short = dot, long = dash. Patterns in milliseconds.
  var PATTERNS = {
    A: [80],
    B: [80, 40, 80],
    C: [80, 40, 80, 40, 80],
    D: [80, 40, 80, 40, 80, 40, 80],
    E: [80, 40, 80, 40, 80, 40, 80, 40, 80],
    F: [80, 40, 80, 40, 80, 40, 80, 40, 80, 40, 80],
    G: [80, 40, 80, 40, 80, 40, 80, 40, 80, 40, 80, 40, 80],
    H: [80, 40, 80, 40, 80, 40, 80, 40, 80, 40, 80, 40, 80, 40, 80],
    I: [80, 40, 80],
    J: [80, 40, 80, 40, 80],
    K: [80, 80],
    L: [80, 40, 80, 40, 80, 80],
    M: [80, 80, 40, 80],
    N: [80, 80, 40, 80, 40, 80],
    O: [80, 80, 40, 80, 40, 80, 40, 80],
    P: [80, 80, 40, 80, 40, 80, 40, 80, 40, 80],
    Q: [80, 80, 40, 80, 40, 80, 40, 80, 40, 80, 40, 80],
    R: [80, 40, 80, 80],
    S: [80, 40, 80, 40, 80, 80],
    T: [80, 40, 80, 80, 40, 80],
    U: [80, 40, 80, 40, 80, 80, 40, 80],
    V: [80, 40, 80, 40, 80, 40, 80, 80],
    W: [80, 40, 80, 80, 40, 80, 40, 80],
    X: [80, 40, 80, 40, 80, 40, 80, 40, 80, 80],
    Y: [80, 40, 80, 80, 40, 80, 40, 80, 40, 80],
    Z: [80, 80, 40, 80, 40, 80],
    "0": [100, 50, 100, 50, 100],
    "1": [100],
    "2": [100, 50, 100],
    "3": [100, 50, 100, 50, 100],
    "4": [100, 50, 100, 50, 100, 50, 100],
    "5": [100, 50, 100, 50, 100, 50, 100, 50, 100],
    "6": [100, 80, 100],
    "7": [100, 80, 100, 80, 100],
    "8": [100, 80, 100, 80, 100, 80, 100],
    "9": [100, 80, 100, 80, 100, 80, 100, 80, 100],
    Space: [30],
    Hi: [80, 60, 80],
    Hello: [80, 50, 80, 50, 80],
    Bye: [80, 60, 80, 60, 80],
    ThankYou: [80, 40, 80, 40, 80, 80],
    Welcome: [80, 40, 80, 40, 80, 40, 80, 80],
    Yes: [80, 80],
    No: [80, 60, 80, 60, 80],
    Please: [80, 40, 80, 40, 80],
    Sorry: [80, 60, 80, 60, 80, 60, 80],
    Help: [80, 40, 80, 80],
    Good: [80, 40, 80, 40, 80],
    Morning: [80, 50, 80, 50, 80, 50, 80],
    Night: [80, 60, 80, 60, 80],
    Love: [80, 80, 80],
    Water: [80, 40, 80, 40, 80],
    Food: [80, 40, 80, 80, 80],
    Name: [80, 60, 80, 60, 80],
    What: [80, 80, 80, 80],
    Where: [80, 40, 80, 80, 80],
    When: [80, 80, 80],
    Why: [80, 80, 80, 80],
    How: [80, 60, 80, 80],
    You: [80, 80, 80],
    We: [80, 60, 80],
    They: [80, 60, 80, 60, 80],
    Me: [80, 80],
    My: [80, 60, 80],
    Your: [80, 80, 60, 80],
    Friend: [80, 40, 80, 40, 80, 40, 80],
    Family: [80, 40, 80, 40, 80, 40, 80, 40, 80],
    Home: [80, 80, 80],
    School: [80, 40, 80, 40, 80, 80],
    Work: [80, 60, 80, 60, 80],
    Come: [80, 40, 80, 80],
    Go: [80, 80],
    Stop: [80, 80, 80],
    Wait: [80, 60, 80, 60, 80],
    Again: [80, 40, 80, 40, 80],
    Slow: [80, 80, 80],
    Understand: [80, 40, 80, 40, 80, 40, 80],
    DontUnderstand: [80, 60, 80, 60, 80, 60, 80, 60, 80],
    Deaf: [80, 80, 80, 80],
    Hearing: [80, 40, 80, 40, 80, 40, 80]
  };

  var MAX_PATTERN_LEN = 12;
  var MAX_TOTAL_MS = 2000;

  function toVibratePattern(arr) {
    if (!Array.isArray(arr) || arr.length === 0) return [50];
    var out = [];
    var total = 0;
    for (var i = 0; i < arr.length && i < MAX_PATTERN_LEN && total < MAX_TOTAL_MS; i++) {
      var ms = Math.max(10, Math.min(500, Math.round(Number(arr[i]) || 50)));
      out.push(ms);
      total += ms;
    }
    return out.length ? out : [50];
  }

  function vibrateForSign(sign) {
    if (!sign) return;
    var key = String(sign).trim();
    if (key.toLowerCase() === "space") key = "Space";
    var pattern = PATTERNS[key];
    if (!pattern) pattern = [60];
    var safePattern = toVibratePattern(pattern);
    if (global.navigator && typeof global.navigator.vibrate === "function") {
      try {
        var ok = global.navigator.vibrate(safePattern);
        if (!ok) global.navigator.vibrate(50);
      } catch (e) {
        try { global.navigator.vibrate(50); } catch (e2) {}
      }
    }
    if (!global.navigator || typeof global.navigator.vibrate !== "function") {
      try {
        if (global.document) {
          var box = global.document.getElementById("output-box");
          if (box) {
            box.classList.add("braille-flash");
            setTimeout(function () { box.classList.remove("braille-flash"); }, 120);
          }
        }
      } catch (e2) {}
    }
  }

  function testVibrate() {
    if (global.navigator && typeof global.navigator.vibrate === "function") {
      try {
        global.navigator.vibrate(30);
      } catch (e) {}
    }
  }

  global.vibrateForSign = vibrateForSign;
  global.testVibrate = testVibrate;
  global.BRAILLE_PATTERNS = PATTERNS;
})(typeof window !== "undefined" ? window : this);
