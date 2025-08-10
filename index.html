<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Instagram Monitor</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root { color-scheme: dark; }
    body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu; margin:0; background:#0b0d10; color:#e7edf3}
    .wrap{max-width:900px; margin:40px auto; padding:0 16px}
    header{display:flex; align-items:center; justify-content:space-between; gap:16px}
    .badges{display:flex; gap:8px; align-items:center}
    .badge{font-size:12px; padding:4px 8px; border-radius:999px; background:#1a2230; color:#9db2c5; border:1px solid #203046}
    .grid{display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin-top:16px}
    .card{background:#0f1622; border:1px solid #1c2a3b; border-radius:16px; padding:16px}
    .title{font-weight:600; color:#9db2c5; font-size:12px; letter-spacing:.4px; text-transform:uppercase}
    .num{font-size:34px; font-weight:700; margin-top:6px}
    .row{display:flex; gap:14px; align-items:center; margin-top:12px}
    .chip{padding:6px 10px; border-radius:999px; border:1px solid #1c2a3b; background:#0f1622; color:#cfe2f2; cursor:pointer; transition:all 0.2s ease}
    .chip:hover{background:#1a2230; border-color:#2a4a5c}
    .input{flex:1; background:#0f1622; border:1px solid #1c2a3b; color:#cfe2f2; padding:10px 12px; border-radius:10px; transition:border-color 0.2s ease}
    .input:focus{outline:none; border-color:#1f6feb}
    button{background:#1f6feb; color:white; border:none; padding:10px 12px; border-radius:10px; cursor:pointer; transition:background 0.2s ease}
    button:hover{background:#0969da}
    button:disabled{background:#656d76; cursor:not-allowed}
    .muted{color:#9db2c5; font-size:12px}
    .verified{display:none}
    a{color:#8ab4ff; text-decoration:none}
    a:hover{text-decoration:underline}
    .loading{opacity:0.6; pointer-events:none}
    
    /* FIXED: Enhanced avatar styling with loading states */
    #avatar {
      transition: opacity 0.3s ease;
      border-radius: 50%;
      border: 1px solid #1c2a3b;
      background: #0f1622;
      object-fit: cover;
    }
    
    #avatar.loading {
      opacity: 0.6;
    }
    
    #avatar.error {
      background: #1a2230 url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjQiIGhlaWdodD0iNjQiIHZpZXdCb3g9IjAgMCA2NCA2NCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMzIiIGN5PSIyNCIgcj0iMTIiIGZpbGw9IiM2NTZkNzYiLz4KPHBhdGggZD0iTTEyIDUyQzEyIDQxIDIwIDMyIDMyIDMyUzUyIDQxIDUyIDUyIiBmaWxsPSIjNjU2ZDc2Ii8+Cjwvc3ZnPgo=') center/32px no-repeat;
    }
    
    @media (max-width: 600px) {
      .wrap{margin:20px auto; padding:0 12px}
      header{flex-direction:column; align-items:stretch; gap:12px}
      .grid{grid-template-columns:1fr; gap:10px}
      .row{flex-wrap:wrap}
      .chip{font-size:11px; padding:5px 8px}
    }
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="row">
        <img id="avatar" 
             alt="Profile Picture" 
             width="64" 
             height="64"
             referrerpolicy="no-referrer"
             crossorigin="anonymous"
             loading="lazy" />
        <div>
          <h1 id="name" style="margin:0 0 6px 0;">Instagram Monitor</h1>
          <div class="muted">
            <span id="username">@username</span>
            <span id="verifiedBadge" class="badge verified" style="background:#0969da; color:white">✓ Verified</span>
          </div>
        </div>
      </div>
      <div class="badges">
        <span id="methodBadge" class="badge">unknown</span>
        <span id="demoBadge" class="badge" style="background:#fd7e14; color:white">Demo Data</span>
      </div>
    </header>

    <div class="row" style="margin-top:18px;">
      <input id="searchInput" class="input" placeholder="Search username (no @)" />
      <button id="searchBtn">Search</button>
    </div>

    <div class="row" style="margin-top:10px;">
      <button class="chip" data-user="therock">therock</button>
      <button class="chip" data-user="cristiano">cristiano</button>
      <button class="chip" data-user="selenagomez">selenagomez</button>
      <button class="chip" data-user="taylorswift">taylorswift</button>
      <button class="chip" data-user="kimkardashian">kimkardashian</button>
      <a id="rawDataLink" class="chip" href="#" target="_blank" rel="noopener">Raw Data</a>
    </div>

    <div class="grid">
      <div class="card">
        <div class="title">Followers</div>
        <div id="followers" class="num">0</div>
      </div>
      <div class="card">
        <div class="title">Following</div>
        <div id="following" class="num">0</div>
      </div>
      <div class="card">
        <div class="title">Posts</div>
        <div id="posts" class="num">0</div>
      </div>
    </div>

    <div class="muted" style="margin-top:16px; text-align:center">
      Last updated: <span id="lastUpdated">—</span> •
      Profile: <a id="profileLink" href="#" target="_blank" rel="noopener">open on Instagram</a> •
      <a href="https://github.com/arandomguyhere/instagram_monitor/actions" target="_blank" rel="noopener">Monitor Actions</a>
    </div>
  </div>

  <script>
    // Robust BASE: '' on user site; '/<repo>' on project site
    const parts = location.pathname.split('/').filter(Boolean);
    const BASE = parts.length ? `/${parts[0]}` : '';

    const $  = (q) => document.querySelector(q);
    const txt = (q, v) => { const el=$(q); if (el) el.textContent = v; };
    const show = (q, on=true) => { const el=$(q); if (el) el.style.display = on?'':'none'; };
    const fmt = (n) => (Number(n)||0).toLocaleString();

    async function fetchJson(url){
      const res = await fetch(url, { cache: 'no-store' });
      if (!res.ok) throw new Error(`${url} -> ${res.status}`);
      return res.json();
    }

    async function loadProfile(user){
      const base = `${BASE}/data/${encodeURIComponent(user)}`;
      const ts = `?ts=${Date.now()}`;

      // Try summary first, then quick_stats as a fallback
      try {
        const d = await fetchJson(`${base}/monitoring_summary.json${ts}`);
        d.__source = 'summary';
        return d;
      } catch {}
      
      try {
        const q = await fetchJson(`${base}/quick_stats.json${ts}`);
        q.__source = 'quick';
        // normalize fields used by render()
        q.timestamp = q.last_updated || null;
        q.profile_url = q.profile_url || `https://instagram.com/${q.username}`;
        q.data_collection_method = q.method || 'unknown';
        return q;
      } catch {}
      
      // If both fail, throw to trigger fallback
      throw new Error('No data found');
    }

    // FIXED: Completely rewritten render function with proper avatar handling
    function render(d){
      txt('#name', d.full_name || d.username);
      txt('#username', '@' + d.username);
      txt('#followers', fmt(d.followers));
      txt('#following', fmt(d.following));
      txt('#posts', fmt(d.posts));
      txt('#lastUpdated', d.timestamp ? new Date(d.timestamp).toLocaleString() : '—');

      const link = $('#profileLink');
      if (link) link.href = d.profile_url || `https://instagram.com/${d.username}`;

      // FIXED: Robust avatar loading with proper error handling
      loadAvatar(d);

      const method = d.data_collection_method || d.method || 'unknown';
      txt('#methodBadge', method.replace(/_/g,' '));
      show('#verifiedBadge', !!d.is_verified);
      show('#demoBadge', false);

      // Raw Data link points to the file actually used
      const raw = $('#rawDataLink');
      if (raw) {
        const filename = d.__source === 'summary' ? 'monitoring_summary.json' : 'quick_stats.json';
        raw.href = `${BASE}/data/${encodeURIComponent(d.username)}/${filename}`;
      }
    }

    // FIXED: New robust avatar loading function
    function loadAvatar(data) {
      const img = $('#avatar');
      if (!img) return;
      
      // Reset state
      img.className = 'loading';
      img.onerror = null;
      img.onload = null;
      
      // Define fallback chain
      const avatarUrls = [
        data.profile_pic_url_hd,
        data.profile_pic_url,
        // Create a proxy URL to bypass CORS issues
        data.profile_pic_url_hd ? `https://images.weserv.nl/?url=${encodeURIComponent(data.profile_pic_url_hd)}&w=150&h=150` : null,
        data.profile_pic_url ? `https://images.weserv.nl/?url=${encodeURIComponent(data.profile_pic_url)}&w=150&h=150` : null,
        'assets/instagram_profile_pic_empty.jpeg'
      ].filter(Boolean);
      
      let currentIndex = 0;
      
      function tryNextUrl() {
        if (currentIndex >= avatarUrls.length) {
          console.error('All avatar URLs failed');
          img.className = 'error';
          return;
        }
        
        const url = avatarUrls[currentIndex];
        console.log(`Trying avatar URL ${currentIndex + 1}/${avatarUrls.length}:`, url);
        
        img.onerror = () => {
          console.warn(`Avatar URL ${currentIndex + 1} failed:`, url);
          currentIndex++;
          tryNextUrl();
        };
        
        img.onload = () => {
          console.log(`Avatar loaded successfully from URL ${currentIndex + 1}:`, url);
          img.className = '';
        };
        
        img.src = url;
      }
      
      tryNextUrl();
    }

    function renderFallback(user) {
      show('#demoBadge', true);
      txt('#name', 'No Data Available');
      txt('#username', '@' + user);
      txt('#followers','—'); 
      txt('#following','—'); 
      txt('#posts','—');
      txt('#lastUpdated','—');
      
      const link = $('#profileLink'); 
      if (link) link.href = `https://instagram.com/${user}`;
      
      // FIXED: Use proper fallback for missing data
      const img = $('#avatar'); 
      if (img) {
        img.className = 'error';
        img.onerror = null;
        img.onload = null;
        img.src = 'assets/instagram_profile_pic_empty.jpeg';
      }
      
      txt('#methodBadge','no data');
      show('#verifiedBadge', false);
      
      const raw = $('#rawDataLink'); 
      if (raw) raw.href = `${BASE}/data/${encodeURIComponent(user)}/quick_stats.json`;
    }

    async function showUser(user){
      if (!user) return;
      
      const searchInput = $('#searchInput');
      const searchBtn = $('#searchBtn');
      const wrap = $('.wrap');
      
      if (searchInput) searchInput.value = user;
      if (searchBtn) searchBtn.disabled = true;
      if (wrap) wrap.classList.add('loading');
      
      try {
        const data = await loadProfile(user);
        render(data);
        console.log(`✅ Loaded data for @${user} from ${data.__source}`);
      } catch (e) {
        console.warn(`⚠️ No data found for @${user}:`, e.message);
        renderFallback(user);
      } finally {
        if (searchBtn) searchBtn.disabled = false;
        if (wrap) wrap.classList.remove('loading');
      }
    }

    function initializeApp() {
      // Search button click
      $('#searchBtn')?.addEventListener('click', () => {
        const input = $('#searchInput');
        const user = (input?.value || '').trim().replace('@', '');
        if (user) showUser(user);
      });
      
      // Enter key in search input
      $('#searchInput')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          $('#searchBtn')?.click();
        }
      });
      
      // Quick search chips
      document.querySelectorAll('[data-user]').forEach(el => {
        el.addEventListener('click', () => {
          const user = el.getAttribute('data-user');
          if (user) showUser(user);
        });
      });
      
      // Load initial user from URL or default
      const urlParams = new URLSearchParams(location.search);
      const initial = urlParams.get('u') || urlParams.get('user') || 'therock';
      showUser(initial);
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initializeApp);
    } else {
      initializeApp();
    }
  </script>
</body>
</html>
