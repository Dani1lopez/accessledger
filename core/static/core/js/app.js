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
