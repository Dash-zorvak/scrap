// Popup.js - UI Logic
let scraping = false;
let startTime = null;

const statusEl = document.getElementById('status');
const progressEl = document.getElementById('progress');
const logEl = document.getElementById('log');
const statsEl = document.getElementById('stats');
const videoCountEl = document.getElementById('videoCount');
const commentCountEl = document.getElementById('commentCount');
const timeSpentEl = document.getElementById('timeSpent');
const downloadLinkEl = document.getElementById('downloadLink');

function log(msg, type = 'info') {
  const entry = document.createElement('div');
  entry.className = `log-entry ${type}`;
  entry.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
  logEl.appendChild(entry);
  logEl.scrollTop = logEl.scrollHeight;
}

function setStatus(text, type = 'idle') {
  statusEl.textContent = text;
  statusEl.className = `status ${type}`;
}

function updateProgress(percent) {
  progressEl.style.width = `${percent}%`;
}

function updateStats(videos, comments, time) {
  statsEl.style.display = 'block';
  videoCountEl.textContent = videos;
  commentCountEl.textContent = comments;
  timeSpentEl.textContent = `${time}s`;
}

document.getElementById('scrapeBtn').addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  
  if (!tab.url.includes('tiktok.com')) {
    setStatus('❌ Abre una página de TikTok primero', 'error');
    return;
  }
  
  scraping = true;
  startTime = Date.now();
  document.getElementById('scrapeBtn').disabled = true;
  document.getElementById('stopBtn').disabled = false;
  downloadLinkEl.style.display = 'none';
  logEl.innerHTML = '';
  
  const extractComments = document.getElementById('extractComments').checked;
  const scrollAll = document.getElementById('scrollAll').checked;
  
  setStatus('🚀 Iniciando scraping...', 'running');
  log('Iniciando extracción de datos...', 'info');
  
  // Send message to content script
  chrome.tabs.sendMessage(tab.id, {
    action: 'startScraping',
    extractComments,
    scrollAll
  });
  
  // Start progress updater
  const progressInterval = setInterval(() => {
    if (!scraping) {
      clearInterval(progressInterval);
      return;
    }
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    chrome.tabs.sendMessage(tab.id, { action: 'getProgress' });
  }, 1000);
});

document.getElementById('stopBtn').addEventListener('click', async () => {
  scraping = false;
  document.getElementById('scrapeBtn').disabled = false;
  document.getElementById('stopBtn').disabled = true;
  setStatus('⏹ Scraping detenido', 'error');
  
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  chrome.tabs.sendMessage(tab.id, { action: 'stopScraping' });
});

// Listen for messages from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('Popup received:', message.action, message);
  
  if (message.action === 'log') {
    log(message.message, message.type || 'info');
  }
  else if (message.action === 'progress') {
    updateProgress(message.percent);
  }
  else if (message.action === 'stats') {
    const elapsed = startTime ? Math.floor((Date.now() - startTime) / 1000) : 0;
    updateStats(message.videos, message.comments, elapsed);
  }
  else if (message.action === 'scrapingComplete') {
    scraping = false;
    document.getElementById('scrapeBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;
    
    setStatus('✅ Scraping completado!', 'done');
    log(`Completado! Videos: ${message.videos}, Comentarios: ${message.comments}`, 'success');
    
    // Show download link
    downloadLinkEl.style.display = 'block';
    document.getElementById('downloadBtn').href = message.dataUrl;
    document.getElementById('downloadBtn').download = `tiktok-data-${Date.now()}.json`;
    
    // Show preview
    if (message.videos > 0) {
      document.getElementById('preview').style.display = 'block';
      const previewText = JSON.stringify({
        videos: message.videos,
        comments: message.comments,
        sample: "Data extracted successfully. Download JSON to see full content."
      }, null, 2);
      document.getElementById('previewData').textContent = previewText;
    }
  }
  else if (message.action === 'error') {
    scraping = false;
    setStatus('❌ Error: ' + message.message, 'error');
    log(message.message, 'error');
    document.getElementById('scrapeBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;
  }
});