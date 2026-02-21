// Obtiene el CSRF token de las cookies
function getCsrfToken() {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : "";
}

// Toggle activar/desactivar usuario
document.addEventListener("DOMContentLoaded", () => {
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
  // Modal crear usuario
const modalCreateUser = document.getElementById("modalCreateUser");
const btnNewUser = document.getElementById("btnNewUser");
const btnCloseCreateUser = document.getElementById("btnCloseCreateUser");
const btnCancelCreateUser = document.getElementById("btnCancelCreateUser");
const formCreateUser = document.getElementById("formCreateUser");
const createUserErrors = document.getElementById("createUserErrors");

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

  const formData = new FormData(formCreateUser);

  const response = await fetch("/users/create/", {
    method: "POST",
    headers: {
      "X-CSRFToken": getCsrfToken(),
      "X-Requested-With": "XMLHttpRequest",
    },
    body: formData,
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
});