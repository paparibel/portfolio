async function loadNavbar() {
  const nav = document.getElementById("navbar");
  const token = localStorage.getItem("access_token");

  let html = `
    <button onclick="location.href='/login'">🔐 Zaloguj</button>
    <button onclick="location.href='/register'">📝 Rejestracja</button>
  `;

  if (token) {
    try {
      const res = await fetch("/api/me", {
        headers: { Authorization: "Bearer " + token }
      });

      if (res.ok) {
        const data = await res.json();
        const username = data.logged_in_as;

        html = `
          <span>👋 Witaj, <strong>${username}</strong></span>
          <button onclick="location.href='/logout'">🚪 Wyloguj</button>
          <div class="tiles">
            <button>📄 Moje CV</button>
            <button>📬 Napisz wiadomość</button>
            <button>💻 Moje projekty</button>
            <button>🧠 Umiejętności</button>
            <button>🎯 Cele</button>
          </div>
        `;

        if (username === "admin") {
          html += `
            <div class="admin-tiles">
              <button onclick="location.href='/admin'">🛡️ Panel admina</button>
              <button>📊 Statystyki</button>
              <button>📥 Wiadomości</button>
              <button>⚙️ Ustawienia</button>
            </div>
          `;
        }
      }
    } catch (err) {
      console.warn("Token nieważny:", err);
      localStorage.removeItem("access_token");
    }
  }

  nav.innerHTML = html;
}

function logout() {
  localStorage.removeItem("access_token");
  location.reload();
}

document.addEventListener("DOMContentLoaded", loadNavbar);
