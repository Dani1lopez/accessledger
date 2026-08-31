/**
 * AccessLedger — Delegated Event Handlers
 *
 * Single delegated listener on #main routes all interactive UI behavior.
 * Survives HTMX content swaps without per-swap rebinding.
 * Modal backdrop close uses direct listeners (not delegated) to avoid
 * stopPropagation() interference with nested dialogs.
 */
(function () {
  'use strict';

  var main = document.getElementById('main');
  if (!main) return;

  // ══════════════════════════════════════════════════════════════════════
  // Helpers
  // ══════════════════════════════════════════════════════════════════════

  function getCsrfToken() {
    var value = '; ' + document.cookie;
    var parts = value.split('; csrftoken=');
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(String(str)));
    return div.innerHTML;
  }

  function clearFieldErrors(scope) {
    var container = scope || document;
    var errors = container.querySelectorAll('.field-error');
    for (var i = 0; i < errors.length; i++) {
      errors[i].textContent = '';
    }
  }

  function showFieldErrors(scope, errors, errBoxEl) {
    var hasGeneral = false;
    var keys = Object.keys(errors || {});
    for (var i = 0; i < keys.length; i++) {
      var field = keys[i];
      var messages = errors[field];
      var safeMsg = messages.map(function (m) { return escapeHtml(m); }).join(', ');
      var fieldEl = scope.querySelector('.field-error[data-field="' + field + '"]');
      if (fieldEl) {
        fieldEl.textContent = safeMsg;
      } else {
        errBoxEl.textContent += safeMsg + ' ';
        hasGeneral = true;
      }
    }
    if (hasGeneral) errBoxEl.style.display = 'block';
  }

  function formatCell(val) {
    if (val === null || val === undefined) return '\u2014';
    if (typeof val === 'object') return JSON.stringify(val);
    return String(val);
  }

  // ══════════════════════════════════════════════════════════════════════
  // Audit diff helpers
  // ══════════════════════════════════════════════════════════════════════

  function parseSnapshot(str) {
    if (!str || str === 'None') return {};
    try {
      var fixed = str
        .replace(/'/g, '"')
        .replace(/True/g, 'true')
        .replace(/False/g, 'false')
        .replace(/None/g, 'null');
      return JSON.parse(fixed);
    } catch (e) {
      return {};
    }
  }

  function computeDiff(before, after) {
    var keys = [];
    var seen = {};
    if (before) Object.keys(before).forEach(function (k) {
      if (!seen[k]) { seen[k] = true; keys.push(k); }
    });
    if (after) Object.keys(after).forEach(function (k) {
      if (!seen[k]) { seen[k] = true; keys.push(k); }
    });

    var diffs = [];
    keys.forEach(function (key) {
      var oldVal = (before && before[key] !== undefined) ? before[key] : null;
      var newVal = (after && after[key] !== undefined) ? after[key] : null;
      if (JSON.stringify(oldVal) !== JSON.stringify(newVal)) {
        diffs.push({ key: key, oldVal: oldVal, newVal: newVal });
      }
    });
    return diffs;
  }

  function renderDiffTable(diff) {
    var tbody = document.getElementById('diffTableBody');
    var empty = document.getElementById('diffEmpty');
    if (!tbody) return;

    tbody.innerHTML = '';
    if (diff.length === 0) {
      if (empty) empty.style.display = 'block';
      return;
    }
    if (empty) empty.style.display = 'none';

    diff.forEach(function (d) {
      var tr = document.createElement('tr');

      var tdF = document.createElement('td');
      tdF.className = 'diff-field';
      tdF.textContent = d.key;

      var tdO = document.createElement('td');
      var spanO = document.createElement('span');
      spanO.className = 'diff-old';
      spanO.textContent = formatCell(d.oldVal);
      tdO.appendChild(spanO);

      var tdN = document.createElement('td');
      var spanN = document.createElement('span');
      spanN.className = 'diff-new';
      spanN.textContent = formatCell(d.newVal);
      tdN.appendChild(spanN);

      tr.appendChild(tdF);
      tr.appendChild(tdO);
      tr.appendChild(tdN);
      tbody.appendChild(tr);
    });
  }

  // ══════════════════════════════════════════════════════════════════════
  // Search / filter (shared for Resources and Users pages)
  // ══════════════════════════════════════════════════════════════════════

  function handleSearch(input) {
    var resourcesTable = document.getElementById('resourcesTable');
    var usersTable = document.getElementById('usersTable');
    var table = resourcesTable || usersTable;
    var pill = document.getElementById('countPill');
    if (!table || !pill) return;

    var rows = table.querySelectorAll('tbody tr.row');
    var term = input.value.trim().toLowerCase();
    var visible = 0;

    for (var i = 0; i < rows.length; i++) {
      var show = term === '' || rows[i].innerText.toLowerCase().indexOf(term) !== -1;
      rows[i].style.display = show ? '' : 'none';
      if (show) visible++;
    }

    if (resourcesTable) {
      pill.textContent = visible + ' recurso' + (visible === 1 ? '' : 's');
    } else {
      pill.textContent = visible + ' usuario' + (visible === 1 ? '' : 's');
    }
  }

  function initSearchCounts() {
    var q = document.getElementById('q');
    if (q) handleSearch(q);
  }

  // ══════════════════════════════════════════════════════════════════════
  // Delegated click handler on #main
  // ══════════════════════════════════════════════════════════════════════

  main.addEventListener('click', function (e) {
    // 1) Modal close buttons (highest priority — generic across all modals)
    var closeBtn = e.target.closest('.modal__close, .modal__btn-cancel');
    if (closeBtn) {
      var dlg = closeBtn.closest('dialog');
      if (dlg) dlg.close();
      return;
    }

    // 2) User toggle activate/deactivate
    var toggleBtn = e.target.closest('[data-action="toggle"]');
    if (toggleBtn) { onToggle(toggleBtn); return; }

    // 3) User edit modal
    var editUserBtn = e.target.closest('[data-action="edit"]');
    if (editUserBtn) { onEditUser(editUserBtn); return; }

    // 4) Audit log detail
    var detailBtn = e.target.closest('.btn-detail');
    if (detailBtn) { onAuditDetail(detailBtn); return; }

    // 5) Modal open buttons (identified by element id)
    var btn = e.target.closest(
      '#btnNewResource, #btnEditResource, #btnDeleteResource, #btnNewGrant, #btnNewUser'
    );
    if (!btn) return;

    switch (btn.id) {
      case 'btnNewResource':   onNewResource(); break;
      case 'btnEditResource':  onEditResource(btn); break;
      case 'btnDeleteResource': onDeleteResource(btn); break;
      case 'btnNewGrant':      onNewGrant(btn); break;
      case 'btnNewUser':       onNewUser(); break;
    }
  });

  // ══════════════════════════════════════════════════════════════════════
  // Delegated submit handler on #main
  // ══════════════════════════════════════════════════════════════════════

  main.addEventListener('submit', function (e) {
    var form = e.target;
    switch (form.id) {
      case 'formNewResource':   e.preventDefault(); onSubmitNewResource(e, form); break;
      case 'formEditResource':  e.preventDefault(); onSubmitEditResource(e, form); break;
      case 'formDeleteResource': e.preventDefault(); onSubmitDeleteResource(e, form); break;
      case 'formCreateUser':    e.preventDefault(); onSubmitCreateUser(e, form); break;
      case 'formEditUser':      e.preventDefault(); onSubmitEditUserForm(e, form); break;
      case 'formGrantCreate':   e.preventDefault(); onSubmitGrantCreate(e, form); break;
    }
  });

  // ══════════════════════════════════════════════════════════════════════
  // Delegated input handler on #main (search)
  // ══════════════════════════════════════════════════════════════════════

  main.addEventListener('input', function (e) {
    if (e.target.id === 'q') handleSearch(e.target);
  });

  // ══════════════════════════════════════════════════════════════════════
  // Direct backdrop listeners on <dialog> elements (NOT delegated)
  // ══════════════════════════════════════════════════════════════════════

  function attachBackdropHandlers() {
    var dialogs = document.querySelectorAll('dialog');
    for (var i = 0; i < dialogs.length; i++) {
      if (dialogs[i]._alBackdropAttached) continue;
      dialogs[i]._alBackdropAttached = true;
      dialogs[i].addEventListener('click', function (ev) {
        if (ev.target === this) this.close();
      });
    }
  }

  attachBackdropHandlers();
  document.body.addEventListener('htmx:afterSettle', attachBackdropHandlers);

  // ══════════════════════════════════════════════════════════════════════
  // ⌘K / Ctrl+K — focus search input (document-level, not on #main)
  // ══════════════════════════════════════════════════════════════════════

  document.addEventListener('keydown', function (e) {
    var isK = e.key.toLowerCase() === 'k';
    var isCmdK = (e.metaKey || e.ctrlKey) && isK;
    if (!isCmdK) return;
    var q = document.getElementById('q');
    if (!q) return;
    e.preventDefault();
    q.focus();
    q.select();
  });

  // ══════════════════════════════════════════════════════════════════════
  // Initialise search counts after HTMX swaps (pill text from template
  // may be stale after swap; recalculates from current DOM rows)
  // ══════════════════════════════════════════════════════════════════════

  document.body.addEventListener('htmx:afterSettle', initSearchCounts);

  // ══════════════════════════════════════════════════════════════════════
  // Handler implementations
  // ══════════════════════════════════════════════════════════════════════

  // ── Toggle user active/inactive ─────────────────────────────────────

  function onToggle(btn) {
    fetch('/users/' + btn.dataset.pk + '/toggle/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCsrfToken(),
        'X-Requested-With': 'XMLHttpRequest',
      },
    })
      .then(function (r) { return r.json(); })
      .then(function (d) { if (d.success) location.reload(); });
  }

  // ── Edit user modal ────────────────────────────────────────────────

  function onEditUser(btn) {
    var errBox = document.getElementById('editUserErrors');
    if (errBox) { errBox.style.display = 'none'; errBox.textContent = ''; }

    fetch('/users/' + btn.dataset.pk + '/data/', {
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    })
      .then(function (r) {
        if (!r.ok) { alert('Error al cargar los datos (' + r.status + ')'); throw new Error('abort'); }
        return r.json();
      })
      .then(function (data) {
        var form = document.getElementById('formEditUser');
        if (!form) return;
        form.querySelector('#edit_username').value = data.username || '';
        form.querySelector('#edit_email').value = data.email || '';
        form.querySelector('#edit_first_name').value = data.first_name || '';
        form.querySelector('#edit_last_name').value = data.last_name || '';
        form.querySelector('#edit_password').value = '';
        var roleSel = form.querySelector('#edit_role');
        if (roleSel && data.group) roleSel.value = data.group;
        form.dataset.pk = btn.dataset.pk;
        var modal = document.getElementById('modalEditUser');
        if (modal) modal.showModal();
      })
      .catch(function (e) {
        if (e.message !== 'abort') alert('Error de red al cargar los datos del usuario.');
      });
  }

  // ── New resource modal ─────────────────────────────────────────────

  function onNewResource() {
    var modal = document.getElementById('modalNewResource');
    var form = document.getElementById('formNewResource');
    var errBox = document.getElementById('modalErrors');
    if (!modal || !form) return;

    if (errBox) { errBox.style.display = 'none'; errBox.textContent = ''; }
    clearFieldErrors(modal);
    form.reset();
    modal.showModal();
  }

  // ── Edit resource modal (on resource detail page) ──────────────────

  function onEditResource(btn) {
    var modal = document.getElementById('modalEditResource');
    var form = document.getElementById('formEditResource');
    var errBox = document.getElementById('editModalErrors');
    if (!modal || !form) return;

    if (errBox) { errBox.style.display = 'none'; errBox.textContent = ''; }
    clearFieldErrors(modal);

    fetch(btn.dataset.urlData, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    })
      .then(function (r) {
        if (!r.ok) { alert('Error al cargar los datos (' + r.status + ')'); throw new Error('abort'); }
        return r.json();
      })
      .then(function (data) {
        form.querySelector('#edit_name').value = data.name || '';
        form.querySelector('#edit_resource_type').value = data.resource_type || '';
        form.querySelector('#edit_environment').value = data.environment || '';
        form.querySelector('#edit_url').value = data.url || '';
        form.querySelector('#edit_is_active').checked = data.is_active === true;
        form.dataset.urlUpdate = btn.dataset.urlUpdate;
        modal.showModal();
      })
      .catch(function (e) {
        if (e.message !== 'abort') alert('Error de red al cargar los datos del recurso.');
      });
  }

  // ── Delete resource modal ──────────────────────────────────────────

  function onDeleteResource(btn) {
    var modal = document.getElementById('modalDeleteResource');
    var nameEl = document.getElementById('deleteResourceName');
    var form = document.getElementById('formDeleteResource');
    if (!modal) return;

    if (nameEl) nameEl.textContent = btn.dataset.name;
    if (form) form.dataset.urlDelete = btn.dataset.urlDelete;
    modal.showModal();
  }

  // ── New grant modal ────────────────────────────────────────────────

  function onNewGrant(btn) {
    var modal = document.getElementById('modalGrantCreate');
    var form = document.getElementById('formGrantCreate');
    var errBox = document.getElementById('grantModalErrors');
    var selectUser = document.getElementById('grant_user');
    if (!modal) return;

    if (errBox) { errBox.style.display = 'none'; errBox.textContent = ''; }
    clearFieldErrors(modal);
    if (form) { form.reset(); form.dataset.urlCreate = btn.dataset.urlCreate; }

    if (selectUser && btn.dataset.urlUsers) {
      selectUser.innerHTML = '<option value="">Cargando\u2026</option>';
      fetch(btn.dataset.urlUsers, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      })
        .then(function (r) {
          if (!r.ok) throw new Error(String(r.status));
          return r.json();
        })
        .then(function (data) {
          selectUser.innerHTML = '<option value="">\u2014 Selecciona un usuario \u2014</option>';
          data.users.forEach(function (u) {
            var opt = document.createElement('option');
            opt.value = u.id;
            opt.textContent = u.username;
            selectUser.appendChild(opt);
          });
        })
        .catch(function () {
          selectUser.innerHTML = '<option value="">Error al cargar usuarios</option>';
        });
    }

    modal.showModal();
  }

  // ── New user modal ─────────────────────────────────────────────────

  function onNewUser() {
    var modal = document.getElementById('modalCreateUser');
    var form = document.getElementById('formCreateUser');
    var errBox = document.getElementById('createUserErrors');
    if (!modal || !form) return;

    form.reset();
    if (errBox) errBox.style.display = 'none';
    modal.showModal();
  }

  // ── Audit detail modal ─────────────────────────────────────────────

  function onAuditDetail(btn) {
    var modal = document.getElementById('modalAuditDetail');
    if (!modal) return;

    var actionEl = document.getElementById('detailAction');
    var objectEl = document.getElementById('detailObject');
    if (actionEl) actionEl.textContent = btn.dataset.action;
    if (objectEl) objectEl.textContent = btn.dataset.object;

    renderDiffTable(computeDiff(
      parseSnapshot(btn.dataset.before),
      parseSnapshot(btn.dataset.after)
    ));
    modal.showModal();
  }

  // ══════════════════════════════════════════════════════════════════════
  // Form submission handlers
  // ══════════════════════════════════════════════════════════════════════

  function onSubmitNewResource(e, form) {
    var errBox = document.getElementById('modalErrors');
    clearFieldErrors();
    if (errBox) { errBox.style.display = 'none'; errBox.textContent = ''; }

    submitForm({
      url: form.action,
      body: new FormData(form),
      onSuccess: function () {
        var dlg = form.closest('dialog');
        if (dlg) dlg.close();
        location.reload();
      },
      onError: function (errors, status) {
        if (status && status !== 400) {
          if (errBox) { errBox.textContent = 'Error del servidor (' + status + '). Int\u00e9ntalo de nuevo.'; errBox.style.display = 'block'; }
          return;
        }
        showFieldErrors(document, errors, errBox || document.createElement('div'));
      },
      onNetworkError: function () {
        if (errBox) { errBox.textContent = 'Error de red. Comprueba tu conexi\u00f3n e int\u00e9ntalo de nuevo.'; errBox.style.display = 'block'; }
      },
    });
  }

  function onSubmitEditResource(e, form) {
    var urlUpdate = form.dataset.urlUpdate;
    var errBox = document.getElementById('editModalErrors');
    clearFieldErrors(document.getElementById('modalEditResource'));
    if (errBox) { errBox.style.display = 'none'; errBox.textContent = ''; }

    submitForm({
      url: urlUpdate,
      body: new FormData(form),
      onSuccess: function () {
        var dlg = form.closest('dialog');
        if (dlg) dlg.close();
        location.reload();
      },
      onError: function (errors, status) {
        if (status && status !== 400) {
          if (errBox) { errBox.textContent = 'Error del servidor (' + status + '). Int\u00e9ntalo de nuevo.'; errBox.style.display = 'block'; }
          return;
        }
        var modal = document.getElementById('modalEditResource');
        showFieldErrors(modal || document, errors, errBox || document.createElement('div'));
      },
      onNetworkError: function () {
        if (errBox) { errBox.textContent = 'Error de red. Comprueba tu conexi\u00f3n e int\u00e9ntalo de nuevo.'; errBox.style.display = 'block'; }
      },
    });
  }

  function onSubmitDeleteResource(e, form) {
    var urlDelete = form.dataset.urlDelete;
    submitForm({
      url: urlDelete,
      onSuccess: function () { location.href = '/resources/'; },
      onError: function (errors, status) {
        alert('Error al borrar (' + status + '). Int\u00e9ntalo de nuevo.');
      },
      onNetworkError: function () {
        alert('Error de red. Comprueba tu conexi\u00f3n e int\u00e9ntalo de nuevo.');
      },
    });
  }

  function onSubmitCreateUser(e, form) {
    var errBox = document.getElementById('createUserErrors');
    if (errBox) { errBox.style.display = 'none'; errBox.textContent = ''; }

    submitForm({
      url: '/users/create/',
      body: new FormData(form),
      onSuccess: function () {
        var dlg = form.closest('dialog');
        if (dlg) dlg.close();
        location.reload();
      },
      onError: function (errors) {
        var messages = Object.keys(errors || {}).map(function (field) {
          return escapeHtml(field) + ': ' + errors[field].map(function (m) { return escapeHtml(m); }).join(', ');
        }).join(' | ');
        if (errBox) { errBox.textContent = messages; errBox.style.display = 'block'; }
      },
      onNetworkError: function () {
        if (errBox) { errBox.textContent = 'Error de red. Comprueba tu conexi\u00f3n e int\u00e9ntalo de nuevo.'; errBox.style.display = 'block'; }
      },
    });
  }

  function onSubmitEditUserForm(e, form) {
    var pk = form.dataset.pk;
    var errBox = document.getElementById('editUserErrors');
    if (errBox) { errBox.style.display = 'none'; errBox.textContent = ''; }

    submitForm({
      url: '/users/' + pk + '/edit/',
      body: new FormData(form),
      onSuccess: function () {
        var dlg = form.closest('dialog');
        if (dlg) dlg.close();
        location.reload();
      },
      onError: function (errors) {
        var messages = Object.keys(errors || {}).map(function (field) {
          return escapeHtml(field) + ': ' + errors[field].map(function (m) { return escapeHtml(m); }).join(', ');
        }).join(' | ');
        if (errBox) { errBox.textContent = messages; errBox.style.display = 'block'; }
      },
      onNetworkError: function () {
        if (errBox) { errBox.textContent = 'Error de red. Comprueba tu conexi\u00f3n e int\u00e9ntalo de nuevo.'; errBox.style.display = 'block'; }
      },
    });
  }

  function onSubmitGrantCreate(e, form) {
    var urlCreate = form.dataset.urlCreate;
    var errBox = document.getElementById('grantModalErrors');
    clearFieldErrors(document.getElementById('modalGrantCreate'));
    if (errBox) { errBox.style.display = 'none'; errBox.textContent = ''; }

    submitForm({
      url: urlCreate,
      body: new FormData(form),
      onSuccess: function () {
        var dlg = form.closest('dialog');
        if (dlg) dlg.close();
        location.reload();
      },
      onCsrfExpired: function () {
        if (errBox) { errBox.textContent = 'Sesi\u00f3n expirada, recarga la p\u00e1gina.'; errBox.style.display = 'block'; }
      },
      onError: function (errors, status) {
        if (status && status !== 400) {
          if (errBox) { errBox.textContent = 'Error del servidor (' + status + '). Int\u00e9ntalo de nuevo.'; errBox.style.display = 'block'; }
          return;
        }
        var modal = document.getElementById('modalGrantCreate');
        showFieldErrors(modal || document, errors, errBox || document.createElement('div'));
      },
      onNetworkError: function () {
        if (errBox) { errBox.textContent = 'Error de red. Comprueba tu conexi\u00f3n e int\u00e9ntalo de nuevo.'; errBox.style.display = 'block'; }
      },
    });
  }

  // ══════════════════════════════════════════════════════════════════════
  // Generic fetch-based form submission
  // ══════════════════════════════════════════════════════════════════════

  function submitForm(opts) {
    var headers = {
      'X-CSRFToken': getCsrfToken(),
      'X-Requested-With': 'XMLHttpRequest',
    };
    var init = { method: 'POST', headers: headers };
    if (opts.body) init.body = opts.body;

    // r.json() must NOT be called before checking r.status === 403:
    // Django returns an HTML body for CSRF failures, which throws
    // SyntaxError when parsed as JSON. We branch on 403 first and
    // surface a localized "Sesión expirada, recarga la página."
    // message via the standard errBox UX (REQ-AR-008 Scenario 8.1).
    fetch(opts.url, init)
      .then(function (r) {
        if (r.status === 403) {
          if (typeof opts.onCsrfExpired === 'function') {
            opts.onCsrfExpired();
          } else {
            opts.onError({ csrf_expired: ['Sesión expirada, recarga la página.'] }, 403);
          }
          throw new Error('abort');
        }
        if (!r.ok && r.status !== 400) {
          opts.onError(null, r.status);
          throw new Error('abort');
        }
        return r.json();
      })
      .then(function (data) {
        if (data.success) {
          opts.onSuccess();
        } else {
          opts.onError(data.errors || {});
        }
      })
      .catch(function (e) {
        if (e.message !== 'abort') opts.onNetworkError();
      });
  }

  // ══════════════════════════════════════════════════════════════════════
  // Set initial search count on first load
  // ══════════════════════════════════════════════════════════════════════

  initSearchCounts();

})();
