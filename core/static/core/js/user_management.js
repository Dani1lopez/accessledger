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
});