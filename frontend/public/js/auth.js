/**
 * KrishiMitra AI — Authentication Module (auth.js)
 * =================================================
 * Handles OTP login, password login, registration, JWT token
 * management, auto-refresh, navbar state, and guest mode.
 *
 * Design:
 *   - Token storage: localStorage (km_access_token, km_refresh_token, km_user)
 *   - Auto-refresh: 55 minutes after login (access token lives 60 min)
 *   - OTP flow: phone → request → 6-digit boxes → verify → logged in
 *   - Guest mode: close modal, session_id from app.js used as anonymous id
 *   - No alert() — all errors shown inline via .auth-error-msg elements
 *
 * API endpoints used:
 *   POST /api/users/otp/request/  { phone_number }
 *   POST /api/users/otp/verify/   { phone_number, otp_code, session_id }
 *   POST /api/token/              { username, password }  (simplejwt)
 *   POST /api/token/refresh/      { refresh }
 *   POST /api/users/register/     { username, password, name, phone_number, state, language }
 *   POST /api/users/logout/       { refresh }
 *   GET  /api/users/me/
 */

(function (window) {
  'use strict';

  /* ── Constants ──────────────────────────────────────────────── */
  var LS_ACCESS  = 'km_access_token';
  var LS_REFRESH = 'km_refresh_token';
  var LS_USER    = 'km_user';
  var REFRESH_MS = 55 * 60 * 1000;   // refresh 5 min before 60-min expiry
  var OTP_RESEND_S = 60;              // resend OTP countdown seconds

  /* ── KM_Auth object ─────────────────────────────────────────── */
  var KM_Auth = {
    _user:          null,
    _accessToken:   null,
    _refreshToken:  null,
    _refreshTimer:  null,
    _countdownTimer: null,
    _currentPhone:  null,   // phone used in ongoing OTP flow
    _bsModal:       null,   // Bootstrap modal instance

    /* ── init ─────────────────────────────────────────────────── */
    init: function () {
      try {
        var tok  = localStorage.getItem(LS_ACCESS);
        var ref  = localStorage.getItem(LS_REFRESH);
        var user = localStorage.getItem(LS_USER);
        if (tok && user) {
          this._accessToken  = tok;
          this._refreshToken = ref;
          this._user         = JSON.parse(user);
          this._updateNavbar();
          this._scheduleRefresh();
        }
      } catch (e) { /* ignore parse errors */ }

      // Wire OTP digit box keyboard navigation
      this._wireOtpInputs();
    },

    /* ── openModal ───────────────────────────────────────────── */
    openModal: function (tab) {
      tab = tab || 'phone';
      var el = document.getElementById('authModal');
      if (!el) return;
      if (!this._bsModal) {
        this._bsModal = new bootstrap.Modal(el, { backdrop: true });
      }
      this.switchTab(tab);
      this._clearAllErrors();
      this._bsModal.show();
    },

    /* ── closeModal ──────────────────────────────────────────── */
    closeModal: function () {
      if (this._bsModal) this._bsModal.hide();
    },

    /* ── switchTab ───────────────────────────────────────────── */
    switchTab: function (tab) {
      var tabs   = ['phone', 'password', 'register'];
      var btnIds = { phone: 'tabBtnPhone', password: 'tabBtnPassword', register: 'tabBtnRegister' };
      var panIds = { phone: 'authTabPhone', password: 'authTabPassword', register: 'authTabRegister' };
      tabs.forEach(function (t) {
        var btn = document.getElementById(btnIds[t]);
        var pan = document.getElementById(panIds[t]);
        if (btn) btn.classList.toggle('active', t === tab);
        if (pan) pan.style.display = (t === tab) ? '' : 'none';
      });
    },

    /* ── requestOtp ──────────────────────────────────────────── */
    requestOtp: function () {
      var self = this;
      var phone = (document.getElementById('authPhoneInput') || {}).value || '';
      phone = phone.replace(/\D/g, '').slice(0, 10);

      if (!/^[6-9]\d{9}$/.test(phone)) {
        self._setError('otpPhoneError', 'कृपया 10-अंकीय मोबाइल नंबर दर्ज करें (6-9 से शुरू)');
        return;
      }
      self._setError('otpPhoneError', '');
      self._setLoading('btnSendOtp', 'spinnerSendOtp', true);

      self._post('/api/users/otp/request/', { phone_number: phone })
        .then(function (data) {
          if (data.success) {
            self._currentPhone = phone;
            // Show OTP step
            var step1 = document.getElementById('otpStep1');
            var step2 = document.getElementById('otpStep2');
            if (step1) step1.style.display = 'none';
            if (step2) step2.style.display = '';
            var disp = document.getElementById('otpPhoneDisplay');
            if (disp) disp.textContent = '+91 ' + phone;
            // Focus first digit
            var first = document.querySelector('#otpInputGroup .otp-digit');
            if (first) setTimeout(function () { first.focus(); }, 100);
            // Clear digits
            document.querySelectorAll('#otpInputGroup .otp-digit').forEach(function (i) { i.value = ''; });
            // Dev OTP hint
            if (data.dev_otp) {
              self._setSuccess('otpVerifySuccess', '🛠️ Dev OTP: ' + data.dev_otp);
            }
            // Start resend countdown
            self._startResendCountdown();
          } else {
            self._setError('otpPhoneError', data.error || 'OTP भेजने में समस्या');
          }
        })
        .catch(function (err) {
          self._setError('otpPhoneError', err.error_hi || err.error || 'नेटवर्क समस्या');
        })
        .finally(function () {
          self._setLoading('btnSendOtp', 'spinnerSendOtp', false);
        });
    },

    /* ── verifyOtp ───────────────────────────────────────────── */
    verifyOtp: function () {
      var self = this;
      var digits = '';
      document.querySelectorAll('#otpInputGroup .otp-digit').forEach(function (i) {
        digits += i.value || '';
      });
      if (digits.length !== 6) {
        self._setError('otpVerifyError', 'कृपया 6 अंक दर्ज करें');
        return;
      }
      self._setError('otpVerifyError', '');
      self._setLoading('btnVerifyOtp', 'spinnerVerifyOtp', true);

      var sessionId = (window._getSessionId && window._getSessionId()) || '';
      self._post('/api/users/otp/verify/', {
        phone_number: self._currentPhone,
        otp_code:     digits,
        session_id:   sessionId,
      })
        .then(function (data) {
          self._onLoginSuccess(data);
        })
        .catch(function (err) {
          self._setError('otpVerifyError', err.error_hi || err.error || 'गलत OTP। दोबारा जांचें।');
        })
        .finally(function () {
          self._setLoading('btnVerifyOtp', 'spinnerVerifyOtp', false);
        });
    },

    /* ── loginPassword ───────────────────────────────────────── */
    loginPassword: function () {
      var self = this;
      var username = ((document.getElementById('authUsernameInput') || {}).value || '').trim();
      var password = ((document.getElementById('authPasswordInput') || {}).value || '').trim();

      if (!username || !password) {
        self._setError('passwordLoginError', 'Username और Password दोनों जरूरी हैं');
        return;
      }
      self._setError('passwordLoginError', '');
      self._setLoading('btnLoginPassword', 'spinnerLoginPassword', true);

      // Use simplejwt's token endpoint
      self._post('/api/token/', { username: username, password: password })
        .then(function (data) {
          // simplejwt returns {access, refresh} — fetch /me/ for user info
          var access  = data.access;
          var refresh = data.refresh;
          return self._get('/api/users/me/', access).then(function (user) {
            self._onLoginSuccess({ access: access, refresh: refresh, user: user });
          });
        })
        .catch(function (err) {
          var msg = (err.detail || err.error || 'गलत username या password');
          if (msg === 'No active account found with the given credentials') {
            msg = 'गलत username या password';
          }
          self._setError('passwordLoginError', msg);
        })
        .finally(function () {
          self._setLoading('btnLoginPassword', 'spinnerLoginPassword', false);
        });
    },

    /* ── register ────────────────────────────────────────────── */
    register: function () {
      var self = this;
      var username  = ((document.getElementById('regUsernameInput') || {}).value || '').trim();
      var password  = ((document.getElementById('regPasswordInput') || {}).value || '').trim();
      var name      = ((document.getElementById('regNameInput')     || {}).value || '').trim();
      var phone     = ((document.getElementById('regPhoneInput')    || {}).value || '').replace(/\D/g, '');
      var state     = ((document.getElementById('regStateInput')    || {}).value || '').trim();
      var sessionId = (window._getSessionId && window._getSessionId()) || '';

      if (!username) { self._setError('registerError', 'Username जरूरी है'); return; }
      if (!password) { self._setError('registerError', 'Password जरूरी है'); return; }
      if (password.length < 8) { self._setError('registerError', 'Password कम से कम 8 अक्षर का होना चाहिए'); return; }
      self._setError('registerError', '');
      self._setLoading('btnRegister', 'spinnerRegister', true);

      self._post('/api/users/register/', {
        username:     username,
        password:     password,
        name:         name,
        phone_number: phone,
        state:        state,
        language:     (window._currentLang || 'hi'),
        session_id:   sessionId,
      })
        .then(function (data) {
          self._onLoginSuccess(data);
        })
        .catch(function (err) {
          self._setError('registerError', err.error || 'पंजीकरण में समस्या आई');
        })
        .finally(function () {
          self._setLoading('btnRegister', 'spinnerRegister', false);
        });
    },

    /* ── backToPhoneStep ─────────────────────────────────────── */
    backToPhoneStep: function () {
      var step1 = document.getElementById('otpStep1');
      var step2 = document.getElementById('otpStep2');
      if (step1) step1.style.display = '';
      if (step2) step2.style.display = 'none';
      this._clearAllErrors();
      if (this._countdownTimer) clearInterval(this._countdownTimer);
    },

    /* ── resendOtp ───────────────────────────────────────────── */
    resendOtp: function () {
      var step1 = document.getElementById('otpStep1');
      var step2 = document.getElementById('otpStep2');
      var inp   = document.getElementById('authPhoneInput');
      if (step1) step1.style.display = '';
      if (step2) step2.style.display = 'none';
      if (inp && this._currentPhone) inp.value = this._currentPhone;
      this._clearAllErrors();
      this.requestOtp();
    },

    /* ── continueAsGuest ─────────────────────────────────────── */
    continueAsGuest: function () {
      this.closeModal();
      if (window.showToast) showToast('👤 Guest मोड में जारी रखें', 'info', 2000);
    },

    /* ── logout ──────────────────────────────────────────────── */
    logout: function () {
      var self = this;
      // Best-effort blacklist the refresh token
      if (self._refreshToken) {
        self._post('/api/users/logout/', { refresh: self._refreshToken }).catch(function () {});
      }
      // Clear local state
      self._accessToken  = null;
      self._refreshToken = null;
      self._user         = null;
      try {
        localStorage.removeItem(LS_ACCESS);
        localStorage.removeItem(LS_REFRESH);
        localStorage.removeItem(LS_USER);
      } catch (e) {}
      if (self._refreshTimer) { clearTimeout(self._refreshTimer); self._refreshTimer = null; }
      self._updateNavbar();
      if (window.showToast) showToast('✅ लॉगआउट सफल', 'success', 2000);
    },

    /* ── refreshToken ────────────────────────────────────────── */
    refreshToken: function () {
      var self = this;
      if (!self._refreshToken) return;
      self._post('/api/token/refresh/', { refresh: self._refreshToken })
        .then(function (data) {
          if (data.access) {
            self._accessToken = data.access;
            try { localStorage.setItem(LS_ACCESS, data.access); } catch (e) {}
            self._scheduleRefresh();
          }
        })
        .catch(function () {
          // Refresh token expired — silent logout
          self.logout();
          self.openModal('phone');
          if (window.showToast) showToast('Session समाप्त हो गया। फिर से लॉगिन करें।', 'warning');
        });
    },

    /* ── isLoggedIn ──────────────────────────────────────────── */
    isLoggedIn: function () {
      return !!(this._accessToken && this._user);
    },

    /* ── getAuthHeaders ──────────────────────────────────────── */
    getAuthHeaders: function () {
      if (!this._accessToken) return {};
      return { 'Authorization': 'Bearer ' + this._accessToken };
    },

    /* ── togglePasswordVisibility ────────────────────────────── */
    togglePasswordVisibility: function (inputId, btn) {
      var inp = document.getElementById(inputId);
      if (!inp) return;
      var isText = inp.type === 'text';
      inp.type = isText ? 'password' : 'text';
      var icon = btn.querySelector('i');
      if (icon) {
        icon.className = isText ? 'fas fa-eye' : 'fas fa-eye-slash';
      }
    },

    /* ── _onLoginSuccess ─────────────────────────────────────── */
    _onLoginSuccess: function (data) {
      this._accessToken  = data.access;
      this._refreshToken = data.refresh;
      this._user         = data.user;
      try {
        localStorage.setItem(LS_ACCESS,  data.access);
        localStorage.setItem(LS_REFRESH, data.refresh);
        localStorage.setItem(LS_USER,    JSON.stringify(data.user));
      } catch (e) {}
      this._scheduleRefresh();
      this._updateNavbar();
      this.closeModal();
      var name = (data.user && data.user.name) ? data.user.name : 'किसान';
      if (window.showToast) showToast('🌾 नमस्ते ' + name + '! लॉगिन सफल', 'success');
    },

    /* ── _updateNavbar ───────────────────────────────────────── */
    _updateNavbar: function () {
      var loginBtn = document.getElementById('navLoginBtn');
      var userPill = document.getElementById('navUserPill');
      var userName = document.getElementById('navUserName');
      var userPhone = document.getElementById('navUserPhone');

      if (this.isLoggedIn()) {
        if (loginBtn) loginBtn.classList.add('d-none');
        if (userPill) userPill.classList.remove('d-none');
        if (userName && this._user) {
          var displayName = this._user.name || this._user.username || 'किसान';
          // Truncate long names
          userName.textContent = displayName.length > 14 ? displayName.slice(0, 12) + '…' : displayName;
        }
        if (userPhone && this._user && this._user.phone) {
          var phone = this._user.phone;
          // Show last 4 digits only for privacy: ••••••6789
          userPhone.textContent = '••••••' + phone.slice(-4);
        }
      } else {
        if (loginBtn) loginBtn.classList.remove('d-none');
        if (userPill) userPill.classList.add('d-none');
      }
    },

    /* ── _scheduleRefresh ────────────────────────────────────── */
    _scheduleRefresh: function () {
      var self = this;
      if (self._refreshTimer) clearTimeout(self._refreshTimer);
      self._refreshTimer = setTimeout(function () {
        self.refreshToken();
      }, REFRESH_MS);
    },

    /* ── _startResendCountdown ───────────────────────────────── */
    _startResendCountdown: function () {
      var self = this;
      var btn  = document.getElementById('btnResendOtp');
      var span = document.getElementById('otpCountdown');
      var secs = OTP_RESEND_S;
      if (btn) btn.disabled = true;
      if (self._countdownTimer) clearInterval(self._countdownTimer);
      self._countdownTimer = setInterval(function () {
        secs--;
        if (span) span.textContent = secs > 0 ? secs + 's बाद दोबारा भेजें' : '';
        if (secs <= 0) {
          clearInterval(self._countdownTimer);
          if (btn)  btn.disabled = false;
          if (span) span.textContent = '';
        }
      }, 1000);
    },

    /* ── _wireOtpInputs ──────────────────────────────────────── */
    _wireOtpInputs: function () {
      // Wire once on DOMContentLoaded; modal may not be in DOM yet — use delegation
      document.addEventListener('input', function (e) {
        if (!e.target.classList.contains('otp-digit')) return;
        var val = e.target.value.replace(/\D/g, '');
        e.target.value = val ? val[0] : '';
        if (val && e.target.nextElementSibling && e.target.nextElementSibling.classList.contains('otp-digit')) {
          e.target.nextElementSibling.focus();
        }
        // Auto-verify when all 6 filled
        var all = document.querySelectorAll('#otpInputGroup .otp-digit');
        var code = '';
        all.forEach(function (i) { code += i.value || ''; });
        if (code.length === 6) KM_Auth.verifyOtp();
      });
      document.addEventListener('keydown', function (e) {
        if (!e.target.classList.contains('otp-digit')) return;
        if (e.key === 'Backspace' && !e.target.value) {
          var prev = e.target.previousElementSibling;
          if (prev && prev.classList.contains('otp-digit')) { prev.focus(); prev.value = ''; }
        }
        if (e.key === 'ArrowLeft') {
          var p = e.target.previousElementSibling;
          if (p && p.classList.contains('otp-digit')) p.focus();
        }
        if (e.key === 'ArrowRight') {
          var n = e.target.nextElementSibling;
          if (n && n.classList.contains('otp-digit')) n.focus();
        }
      });
    },

    /* ── _setError ───────────────────────────────────────────── */
    _setError: function (id, msg) {
      var el = document.getElementById(id);
      if (el) { el.textContent = msg; el.style.display = msg ? '' : 'none'; }
    },

    /* ── _setSuccess ─────────────────────────────────────────── */
    _setSuccess: function (id, msg) {
      var el = document.getElementById(id);
      if (el) { el.textContent = msg; el.style.display = msg ? '' : 'none'; }
    },

    /* ── _clearAllErrors ─────────────────────────────────────── */
    _clearAllErrors: function () {
      var ids = ['otpPhoneError','otpVerifyError','otpVerifySuccess',
                 'passwordLoginError','passwordLoginSuccess',
                 'registerError','registerSuccess'];
      ids.forEach(function (id) {
        var el = document.getElementById(id);
        if (el) { el.textContent = ''; el.style.display = 'none'; }
      });
    },

    /* ── _setLoading ─────────────────────────────────────────── */
    _setLoading: function (btnId, spinnerId, loading) {
      var btn     = document.getElementById(btnId);
      var spinner = document.getElementById(spinnerId);
      if (btn)     btn.disabled     = loading;
      if (spinner) spinner.classList.toggle('d-none', !loading);
    },

    /* ── _post ───────────────────────────────────────────────── */
    _post: function (path, body) {
      var url = (window.apiFetch ? window.apiFetch(path) : path);
      return fetch(url, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
      }).then(function (res) {
        return res.json().then(function (data) {
          if (!res.ok) return Promise.reject(data);
          return data;
        });
      });
    },

    /* ── _get ────────────────────────────────────────────────── */
    _get: function (path, token) {
      var url     = (window.apiFetch ? window.apiFetch(path) : path);
      var headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = 'Bearer ' + token;
      return fetch(url, { headers: headers }).then(function (res) {
        return res.json().then(function (data) {
          if (!res.ok) return Promise.reject(data);
          return data;
        });
      });
    },
  };

  /* ── Expose globally ─────────────────────────────────────────── */
  window.KM_Auth = KM_Auth;

  /* ── Auto-init on DOM ready ──────────────────────────────────── */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { KM_Auth.init(); });
  } else {
    KM_Auth.init();
  }

})(window);
