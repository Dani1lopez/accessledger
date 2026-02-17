(() => {
  const q = document.getElementById("q");
  const table = document.getElementById("resourcesTable");
  const pill = document.getElementById("countPill");

  if (!table || !pill) return;

  const rows = Array.from(table.querySelectorAll("tbody tr.row"));

  const setCount = (n) => {
    pill.textContent = `${n} recurso${n === 1 ? "" : "s"}`;
  };

  const filter = (value) => {
    const term = value.trim().toLowerCase();
    let visible = 0;

    rows.forEach((tr) => {
      const text = tr.innerText.toLowerCase();
      const show = term === "" || text.includes(term);
      tr.style.display = show ? "" : "none";
      if (show) visible += 1;
    });

    setCount(visible);
  };

  // Initial count (if there are no data rows, keep pill as —)
  if (rows.length > 0) setCount(rows.length);

  if (q) {
    q.addEventListener("input", (e) => filter(e.target.value));

    // ⌘K / Ctrl+K focus
    document.addEventListener("keydown", (e) => {
      const isK = e.key.toLowerCase() === "k";
      const isCmdK = (e.metaKey || e.ctrlKey) && isK;
      if (!isCmdK) return;

      e.preventDefault();
      q.focus();
      q.select();
    });
  }
})();


(() => {
  const card = document.querySelector(".auth__card");
  const form = document.querySelector(".auth__form");
  const btn = document.querySelector(".btn--primary");

  // Solo en la página de login
  if (!card || !form || !btn) return;

  // 1) Tilt sutil (solo desktop/ratón)
  const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const isCoarsePointer = window.matchMedia("(pointer: coarse)").matches;

  if (!prefersReduced && !isCoarsePointer) {
    const clamp = (n, min, max) => Math.max(min, Math.min(max, n));

    const onMove = (e) => {
      const r = card.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width;  // 0..1
      const py = (e.clientY - r.top) / r.height;  // 0..1
      const rx = clamp((0.5 - py) * 6, -6, 6);    // grados
      const ry = clamp((px - 0.5) * 8, -8, 8);

      card.style.transform = `perspective(900px) rotateX(${rx}deg) rotateY(${ry}deg) translateY(-1px)`;
    };

    const onLeave = () => {
      card.style.transform = "";
    };

    card.addEventListener("mousemove", onMove);
    card.addEventListener("mouseleave", onLeave);
  }

  // 2) “Focus ring” extra elegante al entrar en inputs
  form.addEventListener("focusin", (e) => {
    const input = e.target.closest("input");
    if (!input) return;
    card.classList.add("auth__card--focus");
  });

  form.addEventListener("focusout", () => {
    // Si el foco sale del form entero, quitamos
    setTimeout(() => {
      if (!form.contains(document.activeElement)) {
        card.classList.remove("auth__card--focus");
      }
    }, 0);
  });

  // 3) Estado "Entrando…" al submit (evita doble click)
  form.addEventListener("submit", () => {
    btn.disabled = true;
    btn.classList.add("btn--loading");
    btn.textContent = "Entrando…";
  });
})();
