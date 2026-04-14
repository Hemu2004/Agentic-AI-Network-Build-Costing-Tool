(function () {
  const STORAGE_ID = 'fttp_user_id';
  const STORAGE_EMAIL = 'fttp_user_email';

  function getUserId() {
    return localStorage.getItem(STORAGE_ID) || '';
  }

  function getUserEmail() {
    return localStorage.getItem(STORAGE_EMAIL) || '';
  }

  function isLoggedIn() {
    return !!localStorage.getItem(STORAGE_ID);
  }

  function setAuth(userId, email) {
    localStorage.setItem(STORAGE_ID, userId);
    localStorage.setItem(STORAGE_EMAIL, email || '');
  }

  function clearAuth() {
    localStorage.removeItem(STORAGE_ID);
    localStorage.removeItem(STORAGE_EMAIL);
  }

  function emailInitial(email) {
    const m = (email || '').trim();
    if (!m) return '';
    return m.charAt(0).toUpperCase();
  }

  function applyAuthDisplay(email) {
    const uid = getUserId();
    const emailEl = document.getElementById('auth-user-email');
    const avatarEl = document.getElementById('auth-user-avatar');
    const badgeEl = document.querySelector('.auth-user-badge');
    const e = (email || '').trim();
    if (avatarEl) {
      if (e) avatarEl.textContent = emailInitial(e);
      else if (uid) avatarEl.textContent = 'U';
      else avatarEl.textContent = '?';
    }
    if (emailEl) {
      if (e) {
        emailEl.textContent = e;
        emailEl.title = e;
      } else if (uid) {
        emailEl.textContent = 'Signed in';
        emailEl.title = 'User id: ' + uid;
      } else {
        emailEl.textContent = '—';
        emailEl.title = '';
      }
    }
    if (badgeEl) badgeEl.title = e || (uid ? 'Signed in' : '');
  }

  async function initAuthBar() {
    let email = getUserEmail();
    const uid = getUserId();
    if (!email && uid) {
      try {
        const r = await fetch('/api/auth/me?user_id=' + encodeURIComponent(uid));
        if (r.ok) {
          const d = await r.json();
          if (d && d.email) {
            localStorage.setItem(STORAGE_EMAIL, d.email);
            email = d.email;
          }
        }
      } catch (err) {
        /* offline or server error */
      }
    }
    applyAuthDisplay(email);

    const logoutBtn = document.getElementById('auth-logout');
    if (logoutBtn) {
      logoutBtn.onclick = function () {
        clearAuth();
        window.location.href = '/static/login.html';
      };
    }
  }

  window.getUserId = getUserId;
  window.getUserEmail = getUserEmail;
  window.isLoggedIn = isLoggedIn;
  window.setAuth = setAuth;
  window.clearAuth = clearAuth;
  window.initAuthBar = initAuthBar;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initAuthBar();
    });
  } else {
    initAuthBar();
  }
})();
