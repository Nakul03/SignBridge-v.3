(function () {
  "use strict";

  var main = document.getElementById("main-content");
  var navLinks = document.querySelectorAll(".nav-link[data-tab]");
  var panes = document.querySelectorAll(".tab-pane");

  function switchTab(tabId) {
    tabId = tabId || "home";
    navLinks.forEach(function (a) {
      a.classList.toggle("active", a.getAttribute("data-tab") === tabId);
    });
    panes.forEach(function (p) {
      var id = p.id;
      var paneTab = id.replace("tab-", "");
      p.classList.toggle("active", paneTab === tabId);
    });
    if (tabId === "education" && !window.signGridLoaded) {
      loadSignGrid();
    }
  }

  navLinks.forEach(function (a) {
    a.addEventListener("click", function (e) {
      e.preventDefault();
      switchTab(a.getAttribute("data-tab"));
    });
  });

  window.addEventListener("hashchange", function () {
    var hash = (window.location.hash || "#home").slice(1);
    if (hash === "home" || hash === "education" || hash === "detector" || hash === "speech-to-sign") switchTab(hash);
  });
  if (window.location.hash) switchTab(window.location.hash.slice(1));

  // ——— Education: sign grid from sign-info.json ———
  window.signGridLoaded = false;
  function loadSignGrid() {
    var grid = document.getElementById("sign-grid");
    if (!grid) return;
    fetch("/data/sign-info.json")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var html = "";
        function addCard(label, info, group) {
          var imgSrc = "/education/" + encodeURIComponent(label) + ".png";
          html += '<div class="sign-card">';
          html += '<div class="sign-card-label">' + escapeHtml(label) + '</div>';
          html += '<div class="sign-card-img-wrap"><img src="' + imgSrc + '" alt="Sign ' + escapeHtml(label) + '" onerror="this.style.display=\'none\'; this.nextElementSibling.style.display=\'block\';" /><span class="sign-card-placeholder" style="display:none;">' + escapeHtml(label) + '</span></div>';
          html += '<p class="sign-card-info">' + escapeHtml(info) + '</p>';
          html += '</div>';
        }
        function escapeHtml(s) {
          var div = document.createElement("div");
          div.textContent = s;
          return div.innerHTML;
        }
        if (data.letters) {
          Object.keys(data.letters).forEach(function (k) { addCard(k, data.letters[k], "letters"); });
        }
        if (data.digits) {
          Object.keys(data.digits).forEach(function (k) { addCard(k, data.digits[k], "digits"); });
        }
        if (data.words) {
          Object.keys(data.words).forEach(function (k) { addCard(k, data.words[k], "words"); });
        }
        grid.innerHTML = html;
        window.signGridLoaded = true;
      })
      .catch(function () {
        grid.innerHTML = "<p>Could not load sign reference. Check static/data/sign-info.json.</p>";
      });
  }

  // ——— Education: chatbox (Ollama sign-language chatbot) ———
  var chatMessages = document.getElementById("chat-messages");
  var chatInput = document.getElementById("chat-input");
  var chatSend = document.getElementById("chat-send");
  var chatHistory = [];

  function addChatMessage(role, text) {
    if (!chatMessages) return;
    var div = document.createElement("div");
    div.className = "chat-msg chat-msg-" + role;
    var who = role === "user" ? "You" : "Sign assistant";
    div.innerHTML = "<strong>" + escapeHtml(who) + ":</strong> " + escapeHtml(text).replace(/\n/g, "<br>");
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }
  function escapeHtml(s) {
    var div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  function sendChat() {
    var msg = (chatInput && chatInput.value) ? chatInput.value.trim() : "";
    if (!msg) return;
    addChatMessage("user", msg);
    chatInput.value = "";
    chatHistory.push({ user: msg, assistant: "" });
    if (chatSend) chatSend.disabled = true;

    fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg, history: chatHistory.slice(0, -1) })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var reply = data.reply || (data.error ? "Error: " + data.error : "No reply.");
        if (chatHistory.length) chatHistory[chatHistory.length - 1].assistant = reply;
        addChatMessage("assistant", reply);
      })
      .catch(function () {
        if (chatHistory.length) chatHistory[chatHistory.length - 1].assistant = "Network error.";
        addChatMessage("assistant", "Network error. Is the server running and Ollama available?");
      })
      .finally(function () {
        if (chatSend) chatSend.disabled = false;
      });
  }

  if (chatSend) chatSend.addEventListener("click", sendChat);
  if (chatInput) chatInput.addEventListener("keydown", function (e) { if (e.key === "Enter") sendChat(); });
})();
