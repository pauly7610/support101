// Injects sidebar React root into Zendesk/Intercom DOM
(function injectSidebar() {
  if (document.getElementById('support-copilot-sidebar')) return;
  const sidebar = document.createElement('div');
  sidebar.id = 'support-copilot-sidebar';
  document.body.appendChild(sidebar);
  // Load React app into this div
  const script = document.createElement('script');
  script.src = /* global chrome */ chrome.runtime.getURL('sidebar.js');
  document.body.appendChild(script);
})();
