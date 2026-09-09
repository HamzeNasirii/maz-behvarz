document.addEventListener("DOMContentLoaded", function () {
    var nav = document.querySelector('nav[aria-label="ناوبری اصلی"]');
    if (!nav) return;

    var allDetails = nav.querySelectorAll("details");
    var storageKey = "sidebar-open-group";

    // بازیابی گروه بازشده‌ی قبلی (اگر ذخیره شده) — این باید قبل از
    // اضافه‌کردن Event Listenerها انجام شود تا با toggle تازه تداخل نکند.
    var savedIndex = localStorage.getItem(storageKey);
    if (savedIndex !== null) {
        allDetails.forEach(function (detail, index) {
            detail.open = (String(index) === savedIndex);
        });
    }

    allDetails.forEach(function (detail, index) {
        detail.addEventListener("toggle", function () {
            if (detail.open) {
                allDetails.forEach(function (other, otherIndex) {
                    if (other !== detail) {
                        other.open = false;
                    }
                });
                localStorage.setItem(storageKey, String(index));
            } else {
                // اگر همان گروه ذخیره‌شده بسته شد، مقدار ذخیره‌شده را هم پاک کن
                if (localStorage.getItem(storageKey) === String(index)) {
                    localStorage.removeItem(storageKey);
                }
            }
        });
    });
});

document.addEventListener("DOMContentLoaded", function () {
    var toggleBtn = document.querySelector("[data-theme-toggle]");
    if (!toggleBtn) return;

    var icon = toggleBtn.querySelector("[data-theme-icon]");

    function updateIcon() {
        var current = document.documentElement.getAttribute("data-theme");
        if (icon) icon.textContent = current === "dark" ? "☀️" : "🌙";
        toggleBtn.setAttribute("aria-pressed", current === "dark" ? "true" : "false");
    }

    updateIcon();

    toggleBtn.addEventListener("click", function () {
        var current = document.documentElement.getAttribute("data-theme");
        var next = current === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        localStorage.setItem("theme", next);
        updateIcon();
    });
});

document.addEventListener("DOMContentLoaded", function () {
    var toggleBtn = document.querySelector("[data-sidebar-toggle]");
    var sidebar = document.querySelector("[data-sidebar]");
    if (!toggleBtn || !sidebar) return;

    toggleBtn.addEventListener("click", function () {
        sidebar.classList.toggle("dashboard__sidebar--open");
    });

    document.addEventListener("click", function (e) {
        var isClickInsideSidebar = sidebar.contains(e.target);
        var isClickOnToggle = toggleBtn.contains(e.target);
        if (!isClickInsideSidebar && !isClickOnToggle && sidebar.classList.contains("dashboard__sidebar--open")) {
            sidebar.classList.remove("dashboard__sidebar--open");
        }
    });
});

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".custom-file-picker").forEach(function (wrapper) {
        var input = wrapper.querySelector("input[type=file]");
        if (!input) return;

        wrapper.addEventListener("dragover", function (e) {
            e.preventDefault();
            wrapper.classList.add("custom-file-picker--dragover");
        });
        wrapper.addEventListener("dragleave", function () {
            wrapper.classList.remove("custom-file-picker--dragover");
        });
        wrapper.addEventListener("drop", function (e) {
            e.preventDefault();
            wrapper.classList.remove("custom-file-picker--dragover");
            if (e.dataTransfer.files.length) {
                input.files = e.dataTransfer.files;
                input.dispatchEvent(new Event("change"));
            }
        });
    });
});

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".data-table").forEach(function (table) {
        var headers = Array.from(table.querySelectorAll("tr:first-child th")).map(function (th) {
            return th.textContent.trim();
        });
        table.querySelectorAll("tr").forEach(function (row, rowIndex) {
            if (rowIndex === 0) return; // ردیف هدر
            Array.from(row.children).forEach(function (cell, cellIndex) {
                if (headers[cellIndex]) {
                    cell.setAttribute("data-label", headers[cellIndex]);
                }
            });
        });
    });
});

document.addEventListener("DOMContentLoaded", function () {
    var searchInput = document.getElementById("board-user-search-input");
    var hiddenUserInput = document.getElementById("id_user");
    if (!searchInput || !hiddenUserInput) return;

    var suggestionsBox = document.getElementById("board-user-search-suggestions");
    var selectedDisplay = document.getElementById("board-user-selected");
    var timer = null;

    searchInput.addEventListener("input", function () {
        clearTimeout(timer);
        var q = searchInput.value.trim();
        if (q.length < 2) { suggestionsBox.style.display = "none"; return; }

        timer = setTimeout(function () {
            fetch("/management/board/user-search/?q=" + encodeURIComponent(q))
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    suggestionsBox.innerHTML = "";
                    if (data.results.length === 0) { suggestionsBox.style.display = "none"; return; }
                    data.results.forEach(function (item) {
                        var a = document.createElement("a");
                        a.href = "#";
                        a.className = "org-search-suggestions__item";
                        a.textContent = item.name + " (" + item.national_code + ")";
                        a.addEventListener("click", function (e) {
                            e.preventDefault();
                            hiddenUserInput.value = item.pk;
                            selectedDisplay.textContent = "انتخاب‌شده: " + item.name;
                            searchInput.value = "";
                            suggestionsBox.style.display = "none";
                        });
                        suggestionsBox.appendChild(a);
                    });
                    suggestionsBox.style.display = "block";
                });
        }, 250);
    });

    document.addEventListener("click", function (e) {
        if (e.target !== searchInput && !suggestionsBox.contains(e.target)) suggestionsBox.style.display = "none";
    });
});