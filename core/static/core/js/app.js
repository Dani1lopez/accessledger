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

document.addEventListener('DOMContentLoaded', () => {
  'use strict';
  const modal = document.getElementById('modalNewResource');
  const btnOpen   = document.getElementById('btnNewResource');
  const btnClose  = document.getElementById('btnCloseModal');
  const btnCancel = document.getElementById('btnCancelModal');
  const form      = document.getElementById('formNewResource');
  const errBox    = document.getElementById('modalErrors');

  if (!modal) return; // el usuario no tiene permisos o no está en esta página

  // ── Helpers ──────────────────────────────────────────────────────────────

  function getCsrfToken() {
    const value = `; ${document.cookie}`;
    const parts = value.split('; csrftoken=');
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
  }

  function openModal() {
    clearErrors();
    form.reset();
    modal.showModal();
  }

  function closeModal() {
    modal.close();
  }

  function clearErrors() {
    errBox.style.display = 'none';
    errBox.textContent = '';
    document.querySelectorAll('.field-error').forEach(el => el.textContent = '');
  }

  // Prevenir XSS: nunca insertar HTML del servidor directamente en el DOM
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(String(str)));
    return div.innerHTML;
  }

  function showErrors(errors) {
    let hasGeneral = false;

    for (const [field, messages] of Object.entries(errors)) {
      const safeMsg = messages.map(m => escapeHtml(m)).join(', ');
      const fieldEl = document.querySelector(`.field-error[data-field="${field}"]`);
      if (fieldEl) {
        fieldEl.textContent = safeMsg; // textContent es seguro, no interpreta HTML
      } else {
        errBox.textContent += safeMsg + ' ';
        hasGeneral = true;
      }
    }

    if (hasGeneral) errBox.style.display = 'block';
  }

  // ── Eventos ──────────────────────────────────────────────────────────────

  btnOpen.addEventListener('click', openModal);
  btnClose.addEventListener('click', closeModal);
  btnCancel.addEventListener('click', closeModal);

  // Cerrar al hacer clic en el backdrop
  modal.addEventListener('click', function (e) {
    if (e.target === modal) closeModal();
  });

  // Submit con fetch
  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    clearErrors();

    try {
      const response = await fetch(form.action, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCsrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: new FormData(form),
      });

      if (!response.ok && response.status !== 400) {
        errBox.textContent = `Error del servidor (${response.status}). Inténtalo de nuevo.`;
        errBox.style.display = 'block';
        return;
      }

      const data = await response.json();

      if (data.success) {
        closeModal();
        window.location.reload();
      } else {
        showErrors(data.errors || {});
      }

    } catch (err) {
      errBox.textContent = 'Error de red. Comprueba tu conexión e inténtalo de nuevo.';
      errBox.style.display = 'block';
    }
  });

});

document.addEventListener('DOMContentLoaded', () => {
  'use strict';

  const modal      = document.getElementById('modalEditResource');
  const btnEdit    = document.getElementById('btnEditResource');
  const btnClose   = document.getElementById('btnCloseEditModal');
  const btnCancel  = document.getElementById('btnCancelEditModal');
  const form       = document.getElementById('formEditResource');
  const errBox     = document.getElementById('editModalErrors');

  if (!modal || !btnEdit) return; // no estamos en resource_detail o sin permisos

  // ── Helpers ──────────────────────────────────────────────────────────────

  function getCsrfToken() {
    const value = `; ${document.cookie}`;
    const parts = value.split('; csrftoken=');
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
  }

  function closeModal() {
    modal.close();
  }

  function clearErrors() {
    errBox.style.display = 'none';
    errBox.textContent = '';
    modal.querySelectorAll('.field-error').forEach(el => el.textContent = '');
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(String(str)));
    return div.innerHTML;
  }

  function showErrors(errors) {
    let hasGeneral = false;
    for (const [field, messages] of Object.entries(errors)) {
      const safeMsg = messages.map(m => escapeHtml(m)).join(', ');
      const fieldEl = modal.querySelector(`.field-error[data-field="${field}"]`);
      if (fieldEl) {
        fieldEl.textContent = safeMsg;
      } else {
        errBox.textContent += safeMsg + ' ';
        hasGeneral = true;
      }
    }
    if (hasGeneral) errBox.style.display = 'block';
  }

  function fillForm(data) {
    form.querySelector('#edit_name').value          = data.name        || '';
    form.querySelector('#edit_resource_type').value = data.resource_type || '';
    form.querySelector('#edit_environment').value   = data.environment  || '';
    form.querySelector('#edit_url').value           = data.url          || '';
    form.querySelector('#edit_is_active').checked   = data.is_active    === true;
  }

  // ── Abrir modal cargando datos via fetch ──────────────────────────────────

  btnEdit.addEventListener('click', async () => {
    clearErrors();

    const urlData   = btnEdit.dataset.urlData;
    const urlUpdate = btnEdit.dataset.urlUpdate;

    try {
      const response = await fetch(urlData, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });

      if (!response.ok) {
        alert(`Error al cargar los datos (${response.status})`);
        return;
      }

      const data = await response.json();
      fillForm(data);
      form.dataset.urlUpdate = urlUpdate; // guardamos la URL de submit en el form
      modal.showModal();

    } catch (err) {
      alert('Error de red al cargar los datos del recurso.');
    }
  });

  // ── Cerrar modal ──────────────────────────────────────────────────────────

  btnClose.addEventListener('click', closeModal);
  btnCancel.addEventListener('click', closeModal);
  modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

  // ── Submit ────────────────────────────────────────────────────────────────

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearErrors();

    const urlUpdate = form.dataset.urlUpdate;

    try {
      const response = await fetch(urlUpdate, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCsrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: new FormData(form),
      });

      if (!response.ok && response.status !== 400) {
        errBox.textContent = `Error del servidor (${response.status}). Inténtalo de nuevo.`;
        errBox.style.display = 'block';
        return;
      }

      const data = await response.json();

      if (data.success) {
        closeModal();
        window.location.reload();
      } else {
        showErrors(data.errors || {});
      }

    } catch (err) {
      errBox.textContent = 'Error de red. Comprueba tu conexión e inténtalo de nuevo.';
      errBox.style.display = 'block';
    }
  });

});

document.addEventListener('DOMContentLoaded', () => {
  'use strict';

  const modal      = document.getElementById('modalDeleteResource');
  const btnDelete  = document.getElementById('btnDeleteResource');
  const btnClose   = document.getElementById('btnCloseDeleteModal');
  const btnCancel  = document.getElementById('btnCancelDeleteModal');
  const form       = document.getElementById('formDeleteResource');
  const nameEl     = document.getElementById('deleteResourceName');

  if (!modal || !btnDelete) return;

  function getCsrfToken() {
    const value = `; ${document.cookie}`;
    const parts = value.split('; csrftoken=');
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
  }

  function closeModal() {
    modal.close();
  }

  // Abrir modal con nombre del recurso
  btnDelete.addEventListener('click', () => {
    nameEl.textContent = btnDelete.dataset.name;
    form.dataset.urlDelete = btnDelete.dataset.urlDelete;
    modal.showModal();
  });

  btnClose.addEventListener('click', closeModal);
  btnCancel.addEventListener('click', closeModal);
  modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

  // Submit con fetch
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const urlDelete = form.dataset.urlDelete;

    try {
      const response = await fetch(urlDelete, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCsrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
        },
      });

      if (response.ok) {
        window.location.href = '/resources/';
      } else {
        alert(`Error al borrar (${response.status}). Inténtalo de nuevo.`);
      }

    } catch (err) {
      alert('Error de red. Comprueba tu conexión e inténtalo de nuevo.');
    }
  });

});
document.addEventListener('DOMContentLoaded', () => {
  'use strict';

  const modal      = document.getElementById('modalGrantCreate');
  const btnNew     = document.getElementById('btnNewGrant');
  const btnClose   = document.getElementById('btnCloseGrantModal');
  const btnCancel  = document.getElementById('btnCancelGrantModal');
  const form       = document.getElementById('formGrantCreate');
  const errBox     = document.getElementById('grantModalErrors');
  const selectUser = document.getElementById('grant_user');

  if (!modal || !btnNew) return;

  function getCsrfToken() {
    const value = `; ${document.cookie}`;
    const parts = value.split('; csrftoken=');
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
  }

  function closeModal() {
    modal.close();
  }

  function clearErrors() {
    errBox.style.display = 'none';
    errBox.textContent = '';
    modal.querySelectorAll('.field-error').forEach(el => el.textContent = '');
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(String(str)));
    return div.innerHTML;
  }

  function showErrors(errors) {
    let hasGeneral = false;
    for (const [field, messages] of Object.entries(errors)) {
      const safeMsg = messages.map(m => escapeHtml(m)).join(', ');
      const fieldEl = modal.querySelector(`.field-error[data-field="${field}"]`);
      if (fieldEl) {
        fieldEl.textContent = safeMsg;
      } else {
        errBox.textContent += safeMsg + ' ';
        hasGeneral = true;
      }
    }
    if (hasGeneral) errBox.style.display = 'block';
  }

  async function loadUsers(urlUsers) {
    selectUser.innerHTML = '<option value="">Cargando…</option>';
    try {
      const response = await fetch(urlUsers, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });
      if (!response.ok) throw new Error(`${response.status}`);
      const data = await response.json();
      selectUser.innerHTML = '<option value="">— Selecciona un usuario —</option>';
      data.users.forEach(u => {
        const opt = document.createElement('option');
        opt.value = u.id;
        opt.textContent = u.username;
        selectUser.appendChild(opt);
      });
    } catch (err) {
      selectUser.innerHTML = '<option value="">Error al cargar usuarios</option>';
    }
  }

  btnNew.addEventListener('click', async () => {
    clearErrors();
    form.reset();
    const urlCreate = btnNew.dataset.urlCreate;
    const urlUsers  = btnNew.dataset.urlUsers;
    form.dataset.urlCreate = urlCreate;
    await loadUsers(urlUsers);
    modal.showModal();
  });

  btnClose.addEventListener('click', closeModal);
  btnCancel.addEventListener('click', closeModal);
  modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearErrors();

    const urlCreate = form.dataset.urlCreate;

    try {
      const response = await fetch(urlCreate, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCsrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: new FormData(form),
      });

      if (!response.ok && response.status !== 400) {
        errBox.textContent = `Error del servidor (${response.status}). Inténtalo de nuevo.`;
        errBox.style.display = 'block';
        return;
      }

      const data = await response.json();

      if (data.success) {
        closeModal();
        window.location.reload();
      } else {
        showErrors(data.errors || {});
      }

    } catch (err) {
      errBox.textContent = 'Error de red. Comprueba tu conexión e inténtalo de nuevo.';
      errBox.style.display = 'block';
    }
  });
});