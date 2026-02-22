// Obtiene el CSRF token de las cookies
function getCsrfToken() {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : "";
}

document.addEventListener("DOMContentLoaded", () => {

  // ── Toggle activar/desactivar usuario ────────────────────────────────────
  document.querySelectorAll("[data-action='toggle']").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const pk = btn.dataset.pk;

      const response = await fetch(`/users/${pk}/toggle/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": getCsrfToken(),
          "X-Requested-With": "XMLHttpRequest",
        },
      });

      const data = await response.json();

      if (data.success) {
        location.reload();
      }
    });
  });

  // ── Modal crear usuario ───────────────────────────────────────────────────
  const modalCreateUser   = document.getElementById("modalCreateUser");
  const btnNewUser        = document.getElementById("btnNewUser");
  const btnCloseCreateUser  = document.getElementById("btnCloseCreateUser");
  const btnCancelCreateUser = document.getElementById("btnCancelCreateUser");
  const formCreateUser    = document.getElementById("formCreateUser");
  const createUserErrors  = document.getElementById("createUserErrors");

  btnNewUser.addEventListener("click", () => {
    formCreateUser.reset();
    createUserErrors.style.display = "none";
    modalCreateUser.showModal();
  });

  [btnCloseCreateUser, btnCancelCreateUser].forEach((btn) => {
    btn.addEventListener("click", () => modalCreateUser.close());
  });

  modalCreateUser.addEventListener("click", (e) => {
    if (e.target === modalCreateUser) modalCreateUser.close();
  });

  formCreateUser.addEventListener("submit", async (e) => {
    e.preventDefault();
    createUserErrors.style.display = "none";

    const response = await fetch("/users/create/", {
      method: "POST",
      headers: {
        "X-CSRFToken": getCsrfToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: new FormData(formCreateUser),
    });

    const data = await response.json();

    if (data.success) {
      modalCreateUser.close();
      location.reload();
    } else {
      const messages = Object.entries(data.errors)
        .map(([field, errs]) => `<strong>${field}:</strong> ${errs.join(", ")}`)
        .join("<br>");
      createUserErrors.innerHTML = messages;
      createUserErrors.style.display = "block";
    }
  });

  // ── Modal editar usuario ──────────────────────────────────────────────────
  const modalEditUser     = document.getElementById("modalEditUser");
  const btnCloseEditUser  = document.getElementById("btnCloseEditUser");
  const btnCancelEditUser = document.getElementById("btnCancelEditUser");
  const formEditUser      = document.getElementById("formEditUser");
  const editUserErrors    = document.getElementById("editUserErrors");

  function closeEditModal() {
    modalEditUser.close();
  }

  function fillEditForm(data) {
    formEditUser.querySelector("#edit_username").value   = data.username   || "";
    formEditUser.querySelector("#edit_email").value      = data.email      || "";
    formEditUser.querySelector("#edit_first_name").value = data.first_name || "";
    formEditUser.querySelector("#edit_last_name").value  = data.last_name  || "";
    formEditUser.querySelector("#edit_password").value   = "";

    // Pre-seleccionar el rol actual
    const selectRole = formEditUser.querySelector("#edit_role");
    if (data.group) {
      selectRole.value = data.group;
    }
  }

  // Abrir modal al hacer clic en cualquier botón "Editar"
  document.querySelectorAll("[data-action='edit']").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const pk = btn.dataset.pk;
      editUserErrors.style.display = "none";

      try {
        const response = await fetch(`/users/${pk}/data/`, {
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });

        if (!response.ok) {
          alert(`Error al cargar los datos (${response.status})`);
          return;
        }

        const data = await response.json();
        fillEditForm(data);
        formEditUser.dataset.pk = pk;
        modalEditUser.showModal();

      } catch (err) {
        alert("Error de red al cargar los datos del usuario.");
      }
    });
  });

  [btnCloseEditUser, btnCancelEditUser].forEach((btn) => {
    btn.addEventListener("click", closeEditModal);
  });

  modalEditUser.addEventListener("click", (e) => {
    if (e.target === modalEditUser) closeEditModal();
  });

  formEditUser.addEventListener("submit", async (e) => {
    e.preventDefault();
    editUserErrors.style.display = "none";

    const pk = formEditUser.dataset.pk;

    try {
      const response = await fetch(`/users/${pk}/edit/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": getCsrfToken(),
          "X-Requested-With": "XMLHttpRequest",
        },
        body: new FormData(formEditUser),
      });

      const data = await response.json();

      if (data.success) {
        closeEditModal();
        location.reload();
      } else {
        const messages = Object.entries(data.errors)
          .map(([field, errs]) => `<strong>${field}:</strong> ${errs.join(", ")}`)
          .join("<br>");
        editUserErrors.innerHTML = messages;
        editUserErrors.style.display = "block";
      }

    } catch (err) {
      editUserErrors.textContent = "Error de red. Comprueba tu conexión e inténtalo de nuevo.";
      editUserErrors.style.display = "block";
    }
  });

});