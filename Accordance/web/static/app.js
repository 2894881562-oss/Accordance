(function () {
  const focusStates = new WeakMap();

  function formToObject(form) {
    const data = new FormData(form);
    const obj = {};
    for (const [key, value] of data.entries()) {
      if (key === "focus_seed" || key.endsWith("_stroke") || key === "birth_hour" || key === "birth_minute") {
        obj[key] = value === "" ? null : Number(value);
      } else if (key === "force") {
        obj[key] = value === "true";
      } else {
        obj[key] = value;
      }
    }
    return obj;
  }

  function formatSeconds(milliseconds) {
    return (milliseconds / 1000).toFixed(2) + " 秒";
  }

  function getFocusState(ritual) {
    if (!focusStates.has(ritual)) {
      focusStates.set(ritual, { start: 0, timer: 0, running: false, completed: false });
    }
    return focusStates.get(ritual);
  }

  function setFocusText(ritual, milliseconds, stateText) {
    const display = ritual.querySelector("[data-focus-display]");
    const state = ritual.querySelector("[data-focus-state]");
    if (display) {
      display.textContent = formatSeconds(milliseconds);
    }
    if (state) {
      state.textContent = stateText;
    }
  }

  function resetFocus(ritual, stateText) {
    const state = getFocusState(ritual);
    const startButton = ritual.querySelector("[data-focus-start]");
    const stopButton = ritual.querySelector("[data-focus-stop]");
    const seedInput = ritual.closest("form").querySelector("[data-focus-seed]");
    window.clearInterval(state.timer);
    state.start = 0;
    state.timer = 0;
    state.running = false;
    state.completed = false;
    if (seedInput) {
      seedInput.value = "0";
    }
    if (startButton) {
      startButton.disabled = false;
      startButton.textContent = "开始默念";
    }
    if (stopButton) {
      stopButton.disabled = true;
    }
    setFocusText(ritual, 0, stateText);
  }

  function startFocus(ritual) {
    const state = getFocusState(ritual);
    if (state.running) {
      return;
    }
    const startButton = ritual.querySelector("[data-focus-start]");
    const stopButton = ritual.querySelector("[data-focus-stop]");
    const seedInput = ritual.closest("form").querySelector("[data-focus-seed]");
    state.start = performance.now();
    state.running = true;
    state.completed = false;
    if (seedInput) {
      seedInput.value = "0";
    }
    if (startButton) {
      startButton.disabled = true;
    }
    if (stopButton) {
      stopButton.disabled = false;
    }
    setFocusText(ritual, 0, "默念中。心中只保留当前所问之事。");
    state.timer = window.setInterval(function () {
      setFocusText(ritual, performance.now() - state.start, "默念中。心中只保留当前所问之事。");
    }, 100);
  }

  function stopFocus(ritual) {
    const state = getFocusState(ritual);
    if (!state.running) {
      return Number(ritual.closest("form").querySelector("[data-focus-seed]")?.value || 0);
    }
    const elapsed = Math.max(0, Math.round(performance.now() - state.start));
    const startButton = ritual.querySelector("[data-focus-start]");
    const stopButton = ritual.querySelector("[data-focus-stop]");
    const seedInput = ritual.closest("form").querySelector("[data-focus-seed]");
    window.clearInterval(state.timer);
    state.running = false;
    state.completed = true;
    if (seedInput) {
      seedInput.value = String(elapsed);
    }
    if (startButton) {
      startButton.disabled = false;
      startButton.textContent = "重新默念";
    }
    if (stopButton) {
      stopButton.disabled = true;
    }
    setFocusText(ritual, elapsed, "已记录默念停顿，将随本次起卦一并入卦。");
    return elapsed;
  }

  function completeRunningFocus(form) {
    const ritual = form.querySelector("[data-focus-ritual]");
    if (ritual) {
      const state = getFocusState(ritual);
      if (state.running) {
        stopFocus(ritual);
        return true;
      }
      if (!state.completed) {
        setFocusText(ritual, 0, "请先开始默念，意念稳定后再完成默念起卦。");
        ritual.scrollIntoView({ behavior: "smooth", block: "center" });
        return false;
      }
    }
    return true;
  }

  function invalidateFocusForEdit(event) {
    const control = event.target.closest("input, textarea, select");
    if (!control || control.matches('[data-focus-seed], input[type="hidden"]')) {
      return;
    }
    const form = control.closest(".ajax-form");
    if (!form) {
      return;
    }
    form.dataset.revision = String(Number(form.dataset.revision || "0") + 1);
    const target = document.querySelector(form.dataset.target);
    if (target && target.childElementCount && target.dataset.stale !== "true") {
      renderStatus(target, "资料已变更，旧结果已失效，请重新提交。", "muted");
      target.dataset.stale = "true";
    }
    const ritual = form?.querySelector("[data-focus-ritual]");
    if (!ritual) {
      return;
    }
    const state = getFocusState(ritual);
    if (state.running || state.completed) {
      resetFocus(ritual, "资料已变更，请确认内容后重新默念起卦。");
    }
  }

  function renderStatus(target, message, className) {
    const article = document.createElement("article");
    const paragraph = document.createElement("p");
    article.className = "panel";
    paragraph.className = className;
    paragraph.textContent = message;
    paragraph.setAttribute("role", className === "warning" ? "alert" : "status");
    article.appendChild(paragraph);
    target.replaceChildren(article);
  }

  function normalizeErrorDetail(detail, fallback) {
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail)) {
      const messages = detail
        .map(function (item) {
          return item && typeof item.msg === "string" ? item.msg : "";
        })
        .filter(Boolean);
      if (messages.length) {
        return messages.join("；");
      }
    }
    return fallback;
  }

  async function submitForm(form, force) {
    const target = document.querySelector(form.dataset.target);
    if (!target || form.dataset.submitting === "true") {
      return;
    }
    if (!completeRunningFocus(form)) {
      return;
    }
    const payload = formToObject(form);
    const submittedRevision = form.dataset.revision || "0";
    if (force) {
      payload.force = true;
    }
    const submitButton = form.querySelector('button[type="submit"]');
    const wasDisabled = submitButton?.disabled || false;
    form.dataset.submitting = "true";
    target.setAttribute("aria-busy", "true");
    target.dataset.stale = "false";
    if (submitButton) {
      submitButton.disabled = true;
    }
    renderStatus(target, "正在分析...", "muted");
    try {
      const response = await fetch(form.dataset.endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "text/html"
        },
        body: JSON.stringify(payload)
      });
      if (!response.ok) {
        let message = "请求失败，请检查输入后重试。";
        try {
          const error = await response.json();
          message = normalizeErrorDetail(error.detail, message);
        } catch (error) {}
        if ((form.dataset.revision || "0") === submittedRevision) {
          renderStatus(target, message, "warning");
        }
        return;
      }
      const html = await response.text();
      if ((form.dataset.revision || "0") !== submittedRevision) {
        return;
      }
      target.innerHTML = html;
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      if ((form.dataset.revision || "0") === submittedRevision) {
        renderStatus(target, "网络连接失败，请确认服务仍在运行后重试。", "warning");
      }
    } finally {
      form.dataset.submitting = "false";
      target.setAttribute("aria-busy", "false");
      if (submitButton) {
        submitButton.disabled = wasDisabled;
      }
    }
  }

  document.addEventListener("submit", function (event) {
    const confirmForm = event.target.closest("[data-confirm-message]");
    if (confirmForm) {
      if (!window.confirm(confirmForm.dataset.confirmMessage)) {
        event.preventDefault();
      }
      return;
    }
    const form = event.target.closest(".ajax-form");
    if (!form) {
      return;
    }
    event.preventDefault();
    submitForm(form, false);
  });

  document.addEventListener("input", invalidateFocusForEdit);
  document.addEventListener("change", invalidateFocusForEdit);

  document.addEventListener("click", function (event) {
    const startButton = event.target.closest("[data-focus-start]");
    if (startButton) {
      const ritual = startButton.closest("[data-focus-ritual]");
      if (ritual) {
        startFocus(ritual);
      }
      return;
    }

    const stopButton = event.target.closest("[data-focus-stop]");
    if (stopButton) {
      const ritual = stopButton.closest("[data-focus-ritual]");
      if (ritual) {
        stopFocus(ritual);
      }
      return;
    }

    const button = event.target.closest(".continue-force");
    if (!button) {
      return;
    }
    const form = document.querySelector(".ajax-form");
    if (form) {
      submitForm(form, true);
    }
  });
})();
