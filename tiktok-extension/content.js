// content.js - TikTok Scraper Pro (Versión robusta)
// Funciona directamente en TikTok

(function() {
  if (window.tiktokScraperActive) return;
  window.tiktokScraperActive = true;

  let scraping = false;
  let extractedData = { profile: null, videos: [], totalComments: 0 };

  // Send messages to popup
  function postMessage(action, data = {}) {
    try {
      chrome.runtime.sendMessage({ ...data, action });
    } catch(e) { console.log('Message error:', e); }
  }

  function log(msg, type = 'info') {
    console.log(`[Scraper] ${msg}`);
    postMessage('log', { message: msg, type });
  }

  function updateProgress(percent) {
    postMessage('progress', { percent });
  }

  function updateStats(videos, comments) {
    postMessage('stats', { videos, comments });
  }

  // Get TikTok JSON data
  function getTikTokJSON() {
    const script = document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__');
    if (script && script.textContent) {
      try {
        return JSON.parse(script.textContent).__DEFAULT_SCOPE__;
      } catch(e) { return null; }
    }
    return null;
  }

  // Extract profile info
  function getProfile() {
    const data = getTikTokJSON();
    if (!data) return null;
    
    const userDetail = data['webapp.user-detail'];
    if (!userDetail) return null;
    
    const user = userDetail.userInfo?.user || {};
    const stats = userDetail.userInfo?.stats || {};
    
    return {
      username: user.uniqueId || '',
      nickname: user.nickname || '',
      avatar: user.avatarLarger || '',
      bio: user.signature || '',
      followers: stats.followerCount || 0,
      following: stats.followingCount || 0,
      videos: stats.awemeCount || 0,
      verified: user.verified || false
    };
  }

  // Get video IDs from page using multiple methods
  function getVideoIds() {
    const ids = new Set();
    
    // Method 1: data-e2e selector
    document.querySelectorAll('[data-e2e="user-post-item"] a, [data-e2e="user-post-item"]').forEach(el => {
      const href = el.href || el.getAttribute('href');
      if (href && href.includes('/video/')) {
        const parts = href.split('/');
        const id = parts[parts.length - 1].split('?')[0];
        if (id && /^\d+$/.test(id)) ids.add(id);
      }
    });
    
    // Method 2: Any anchor with video in URL
    document.querySelectorAll('a[href*="/video/"]').forEach(el => {
      const parts = el.href.split('/');
      const id = parts[parts.length - 1].split('?')[0];
      if (id && /^\d+$/.test(id)) ids.add(id);
    });
    
    // Method 3: Look in main content area
    document.querySelectorAll('[class*="VideoContainer"], [class*="VideoFeed"], [class*="Grid"] a').forEach(el => {
      const href = el.href || el.getAttribute('href');
      if (href && href.includes('/video/')) {
        const parts = href.split('/');
        const id = parts[parts.length - 1].split('?')[0];
        if (id && /^\d+$/.test(id)) ids.add(id);
      }
    });
    
    return Array.from(ids);
  }

  // Find and click the Shared tab
  async function findAndClickSharedTab() {
    log('🔍 Buscando pestaña de Compartidos/Shared...');
    
    // Wait for tabs to load
    await new Promise(r => setTimeout(r, 2000));
    
    // Find all potential tab elements
    const allElements = document.querySelectorAll('a, button, div[role], span');
    let sharedLink = null;
    
    for (const el of allElements) {
      const text = (el.textContent || '').toLowerCase().trim();
      const ariaLabel = (el.getAttribute('aria-label') || '').toLowerCase();
      
      // Look for shared/compart variants
      if (text === 'shared' || text === 'compartidos' || 
          text.includes(' shared') || text.includes(' compart') ||
          ariaLabel.includes('shared') || ariaLabel.includes('compart')) {
        sharedLink = el;
        log(`✓ Encontrada pestaña: "${text}"`);
        break;
      }
    }
    
    if (sharedLink) {
      log('👆 Haciendo clic en Shared/Compartidos...');
      try {
        sharedLink.scrollIntoView({ behavior: 'smooth', block: 'center' });
        await new Promise(r => setTimeout(r, 500));
        sharedLink.click();
        await new Promise(r => setTimeout(r, 3000));
        log('✓ Pestaña cambiada, esperando carga...');
        return true;
      } catch(e) {
        log(`Error clicking: ${e.message}`);
      }
    }
    
    // Try URL modification
    const currentUrl = window.location.href;
    if (!currentUrl.includes('tab=shared') && !currentUrl.includes('tab=likes')) {
      const newUrl = currentUrl.includes('?') 
        ? currentUrl + '&tab=shared' 
        : currentUrl + '?tab=shared';
      
      log('🔄 Intentando cambiar URL...');
      window.location.href = newUrl;
      await new Promise(r => setTimeout(r, 5000));
      return true;
    }
    
    return false;
  }

  // Main scraping function
  async function startScraping(options) {
    if (scraping) return;
    scraping = true;
    extractedData = { profile: null, videos: [], totalComments: 0 };
    
    try {
      log('🚀 INICIANDO SCRAPER');
      
      // Wait for initial load
      await new Promise(r => setTimeout(r, 4000));
      
      // Check page URL and navigate if needed
      const url = window.location.href;
      log(`📍 URL actual: ${url}`);
      
      // If we're on main profile, try shared tab
      if (url.includes('/@') && !url.includes('tab=')) {
        log('📋 Detectando pestaña correcta...');
        await findAndClickSharedTab();
      }
      
      // Get profile
      log('📊 Extrayendo perfil...');
      extractedData.profile = getProfile();
      
      if (extractedData.profile) {
        log(`✓ Perfil: @${extractedData.profile.username}`);
        log(`   Videos: ${extractedData.profile.videos}`);
      } else {
        log('⚠️ No se pudo obtener perfil');
      }
      
      // Scroll to load videos
      log('⬇️ Cargando videos (scroll)...');
      let lastCount = 0;
      let noChangeCount = 0;
      
      for (let i = 0; i < 30 && noChangeCount < 5; i++) {
        window.scrollBy(0, 600);
        await new Promise(r => setTimeout(r, 1500));
        
        const ids = getVideoIds();
        
        if (ids.length !== lastCount) {
          log(`   Scroll ${i+1}: ${ids.length} videos`);
          lastCount = ids.length;
          noChangeCount = 0;
        } else {
          noChangeCount++;
        }
        
        updateProgress(Math.min((i/30) * 100, 95));
      }
      
      // Get final video IDs
      const videoIds = getVideoIds();
      log(`📹 Total videos encontrados: ${videoIds.length}`);
      
      // Try to get videos from JSON
      const data = getTikTokJSON();
      if (data && data['webapp.user-detail']?.awemeList) {
        const awemeList = data['webapp.user-detail'].awemeList;
        log(`✓ Obtenidos ${awemeList.length} videos del JSON`);
        
        awemeList.forEach(v => {
          const stats = v.stats || {};
          extractedData.videos.push({
            video_id: v.id,
            description: v.desc || '',
            create_time: v.createTime ? new Date(v.createTime * 1000).toISOString() : null,
            stats: {
              views: stats.playCount || 0,
              likes: stats.diggCount || 0,
              comments: stats.commentCount || 0,
              shares: stats.shareCount || 0,
              saves: stats.collectCount || 0
            },
            hashtags: (v.desc || '').match(/#[\w\u00C0-\u024F]+/g) || [],
            mentions: (v.desc || '').match(/@[\w\u00C0-\u024F]+/g) || []
          });
        });
      }
      
      // If no videos from JSON, try from page elements (limited data)
      if (extractedData.videos.length === 0 && videoIds.length > 0) {
        log('⚠️ Usando datos limitados del DOM');
        videoIds.forEach(id => {
          extractedData.videos.push({
            video_id: id,
            description: '',
            create_time: null,
            stats: { views: 0, likes: 0, comments: 0, shares: 0, saves: 0 },
            hashtags: [],
            mentions: []
          });
        });
      }
      
      log(`✅ SCRAPING COMPLETADO`);
      log(`   Videos: ${extractedData.videos.length}`);
      
      updateProgress(100);
      updateStats(extractedData.videos.length, extractedData.totalComments);
      
      // Send complete data
      const dataUrl = 'data:application/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(extractedData, null, 2));
      postMessage('scrapingComplete', {
        videos: extractedData.videos.length,
        comments: extractedData.totalComments,
        dataUrl
      });
      
    } catch(e) {
      log(`❌ ERROR: ${e.message}`);
      postMessage('error', { message: e.message });
    }
    
    scraping = false;
  }

  // Listen for messages from extension popup
  chrome.runtime?.onMessage?.addListener((msg, sender, response) => {
    if (msg.action === 'startScraping') {
      startScraping({ extractComments: msg.extractComments, scrollAll: msg.scrollAll });
    }
  });

  log('✅ TikTok Scraper cargado');
})();