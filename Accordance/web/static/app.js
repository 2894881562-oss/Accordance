(function () {
  function formToObject(form) {
    const data = new FormData(form);
    const obj = {};
    for (const [key, value] of data.entries()) {
      if (key === "focus_seed" || key.endsWith("_stroke")) {
        obj[key] = value === "" ? null : Number(value);
      } else if (key === "force") {
        obj[key] = value === "true";
      } else {
        obj[key] = value;
      }
    }
    return obj;
  }

  async function submitForm(form, force) {
    const target = document.querySelector(form.dataset.target);
    const payload = formToObject(form);
    if (force) {
      payload.force = true;
    }
    target.innerHTML = '<article class="panel"><p class="muted">正在分析...</p></article>';
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
        message = error.detail || message;
      } catch (err) {}
      target.innerHTML = '<article class="panel"><p class="warning">' + message + '</p></article>';
      return;
    }
    target.innerHTML = await response.text();
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  document.addEventListener("submit", function (event) {
    const form = event.target.closest(".ajax-form");
    if (!form) {
      return;
    }
    event.preventDefault();
    submitForm(form, false);
  });

  document.addEventListener("click", function (event) {
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
