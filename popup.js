// Popup script for Semantic Search Extension

// DOM Elements
const searchInput = document.getElementById('search-input');
const searchButton = document.getElementById('search-button');
const searchResults = document.getElementById('search-results');
const searchStats = document.getElementById('search-stats');
const confidentialSites = document.getElementById('confidential-sites');
const saveSettingsButton = document.getElementById('save-settings');
const downloadIndexButton = document.getElementById('download-index');
const exportStats = document.getElementById('export-stats');
const tabs = document.querySelectorAll('.tab');
const tabContents = document.querySelectorAll('.tab-content');
const backendStatus = document.getElementById('backend-status');
const notificationArea = document.getElementById('notification-area');

console.log('Popup script loaded');

// Constants
const NOTIFICATION_DURATION = 3000; // 3 seconds in milliseconds
const MAX_VISIBLE_NOTIFICATIONS = 3; // Maximum number of visible notifications
const NOTIFICATION_RULES = {
    // Messages to completely suppress
    suppress: [
        'Extension initialized successfully',
        'Extension initialized'
    ],
    // Success messages - auto-hide quickly
    quickSuccess: {
        duration: 2000, // 2 seconds
        keywords: ['successfully', 'saved', 'Settings saved', 'Successfully indexed']
    },
    // Info messages - auto-hide after medium time
    info: {
        duration: 3000, // 3 seconds
        keywords: ['started', 'indexing', 'Loading']
    },
    // Errors/warnings - keep for longer
    persistent: {
        duration: 10000, // 10 seconds
        keywords: ['error', 'failed', 'Error']
    },
    // Routine success - suppress after very short time
    routine: {
        duration: 1000, // 1 second
        keywords: ['Skipped', 'skipped', 'already indexed']
    }
};

// Tab switching functionality
tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    // Remove active class from all tabs and contents
    tabs.forEach(t => t.classList.remove('active'));
    tabContents.forEach(c => c.classList.remove('active'));
    
    // Add active class to clicked tab and corresponding content
    tab.classList.add('active');
    const tabId = tab.getAttribute('data-tab');
    document.getElementById(`${tabId}-tab`).classList.add('active');
    
    // Load tab-specific data
    if (tabId === 'preferences') {
      console.log('Loading preferences tab');
      loadUserPreferences();
    } else if (tabId === 'favorites') {
      console.log('Loading favorites tab');
      loadFavorites();
    } else if (tabId === 'settings') {
      console.log('Loading settings tab');
      loadConfidentialSites();
    } else if (tabId === 'export') {
      console.log('Loading export tab');
      getIndexStats();
    }
  });
});

// Search functionality
searchButton.addEventListener('click', performSearch);
searchInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') {
    performSearch();
  }
});

// Settings functionality
saveSettingsButton.addEventListener('click', saveConfidentialSites);

// Export functionality
downloadIndexButton.addEventListener('click', downloadIndex);

// Initialize popup
document.addEventListener('DOMContentLoaded', function() {
    // Clear all data functionality - must be inside DOMContentLoaded
    document.getElementById('clear-all-data').addEventListener('click', clearAllData);
    
    // Save preferences functionality
    document.getElementById('save-preferences').addEventListener('click', saveUserPreferences);
    
    // Initialize category checkboxes
    initializeCategoryCheckboxes();
    
    // Load preferences
    loadUserPreferences();
    
    console.log('Popup DOM loaded');
    
    // Initialize notification area
    const notificationArea = document.getElementById('notification-area');
    if (!notificationArea) {
        console.error('Notification area not found in DOM');
    } else {
        console.log('Notification area initialized');
    }

    // Load settings when opening the popup
    loadConfidentialSites();
    
    // Load favorites
    loadFavorites();

    // Initialize the extension
    chrome.runtime.sendMessage({ action: 'init' }, response => {
        if (response && response.success) {
            console.log('Extension initialized successfully');
            // Don't show notification as it's a routine message
        } else {
            console.error('Failed to initialize extension:', response?.error || 'Unknown error');
            addNotification('Failed to initialize extension', 'error');
        }
    });

    // Connect to background script
    const port = chrome.runtime.connect({ name: 'popup' });
    
    // Listen for messages from background script
    port.onMessage.addListener((message) => {
        console.log('Popup received port message:', message);
        handleIndexingStatus(message);
    });
    
    // Handle disconnection
    port.onDisconnect.addListener(() => {
        console.log('Disconnected from background script');
    });

    // Also listen for direct messages
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
        console.log('Popup received direct message:', message);
        if (message.type === 'indexing_status') {
            handleIndexingStatus(message);
        }
        sendResponse({ received: true });
        return true; // Keep the message channel open for async response
    });

    // Function to handle indexing status messages
    function handleIndexingStatus(message) {
        console.log('Processing indexing status message:', message);
        // Update the status display
        updateStatus(message.status, message.url, message.error);
        
        // Add notification only for important statuses
        let notificationType = 'info';
        let notificationMessage = '';
        let shouldNotify = false;
        
        switch (message.status) {
            case 'skipped':
                if (message.error && message.error === 'Page already indexed') {
                    // Don't notify about already indexed pages - too routine
                    shouldNotify = false;
                } else {
                    notificationMessage = `Skipped confidential page: ${message.url}`;
                    notificationType = 'info';
                    shouldNotify = true;
                }
                // Ensure the error message is displayed
                if (message.error) {
                    const errorElement = document.getElementById('error-message');
                    if (errorElement) {
                        errorElement.textContent = message.error;
                        errorElement.style.display = 'block';
                        console.log('Displayed error message for skipped page:', message.error);
                    } else {
                        console.error('Error element not found in DOM');
                    }
                }
                break;
            case 'started':
                // Don't notify about started - just show in status indicator
                shouldNotify = false;
                break;
            case 'completed':
                notificationMessage = `Successfully indexed: ${message.url}`;
                notificationType = 'success';
                shouldNotify = true;
                break;
            case 'error':
                notificationMessage = `Error indexing ${message.url}: ${message.error || 'Unknown error'}`;
                notificationType = 'error';
                shouldNotify = true;
                break;
            default:
                notificationMessage = `Unknown status for ${message.url}: ${message.status}`;
                notificationType = 'info';
                shouldNotify = true;
        }
        
        // Add notification only if needed
        if (shouldNotify) {
            console.log('Adding notification:', notificationMessage, 'Type:', notificationType);
            addNotification(notificationMessage, notificationType);
        }
    }

    // Add test button to settings tab
    const settingsTab = document.getElementById('settings-tab');
    const testButton = document.createElement('button');
    testButton.textContent = 'Test Confidential Site Detection';
    testButton.onclick = async () => {
        const testUrl = 'https://mail.google.com';
        console.log('Testing confidential site detection for:', testUrl);
        try {
            const response = await chrome.runtime.sendMessage({
                action: 'testConfidentialSite',
                url: testUrl
            });
            console.log('Test response:', response);
            if (response.isConfidential) {
                addNotification(`Test successful: ${testUrl} is confidential (matched: ${response.matchedPattern})`, 'success');
            } else {
                addNotification(`Test failed: ${testUrl} was not detected as confidential`, 'error');
            }
        } catch (error) {
            console.error('Test error:', error);
            addNotification(`Test error: ${error.message}`, 'error');
        }
    };
    settingsTab.insertBefore(testButton, settingsTab.firstChild);
});

// Function to add a notification with smart duration
function addNotification(message, type = 'info') {
    console.log('Adding notification:', message, 'Type:', type);
    
    // Check if message should be suppressed
    if (NOTIFICATION_RULES.suppress.some(pattern => message.includes(pattern))) {
        console.log('Suppressed notification:', message);
        return;
    }
    
    const notificationArea = document.getElementById('notification-area');
    if (!notificationArea) {
        console.error('Notification area not found');
        return;
    }

    // Determine auto-hide duration based on message content
    let autoHideDuration = NOTIFICATION_DURATION;
    
    // Check for persistent messages (errors)
    if (NOTIFICATION_RULES.persistent.keywords.some(keyword => message.toLowerCase().includes(keyword.toLowerCase()))) {
        autoHideDuration = NOTIFICATION_RULES.persistent.duration;
    }
    // Check for routine messages
    else if (NOTIFICATION_RULES.routine.keywords.some(keyword => message.includes(keyword))) {
        autoHideDuration = NOTIFICATION_RULES.routine.duration;
    }
    // Check for success messages
    else if (NOTIFICATION_RULES.quickSuccess.keywords.some(keyword => message.toLowerCase().includes(keyword.toLowerCase()))) {
        autoHideDuration = NOTIFICATION_RULES.quickSuccess.duration;
    }
    // Check for info messages
    else if (NOTIFICATION_RULES.info.keywords.some(keyword => message.toLowerCase().includes(keyword.toLowerCase()))) {
        autoHideDuration = NOTIFICATION_RULES.info.duration;
    }

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    const content = document.createElement('div');
    content.className = 'content';
    content.textContent = message;
    
    const timestamp = document.createElement('span');
    timestamp.className = 'timestamp';
    timestamp.textContent = new Date().toLocaleTimeString();
    
    const close = document.createElement('span');
    close.className = 'close';
    close.textContent = '×';
    close.onclick = () => notification.remove();
    
    notification.appendChild(content);
    notification.appendChild(timestamp);
    notification.appendChild(close);
    
    // Limit number of visible notifications
    const existingNotifications = notificationArea.querySelectorAll('.notification');
    if (existingNotifications.length >= MAX_VISIBLE_NOTIFICATIONS) {
        // Remove oldest notification
        const oldest = existingNotifications[existingNotifications.length - 1];
        if (oldest) {
            oldest.remove();
        }
    }
    
    // Add to the top of the notification area
    notificationArea.insertBefore(notification, notificationArea.firstChild);
    console.log('Notification added to DOM with auto-hide duration:', autoHideDuration);
    
    // Auto-remove after duration (but not for persistent errors unless they're old)
    if (autoHideDuration < 10000) {
        setTimeout(() => {
            if (notification.parentNode === notificationArea) {
                notification.remove();
                console.log('Notification auto-removed after', autoHideDuration, 'ms');
            }
        }, autoHideDuration);
    }
}

// Function to check backend status
async function checkBackendStatus() {
  try {
    const response = await fetch('http://localhost:5000/api/health');
    if (response.ok) {
      backendStatus.textContent = 'LLM Service: ON';
      backendStatus.classList.remove('status-off');
      backendStatus.classList.add('status-on');
      return true;
    } else {
      throw new Error('Backend not healthy');
    }
  } catch (error) {
    console.error('Backend status check failed:', error);
    backendStatus.textContent = 'LLM Service: OFF';
    backendStatus.classList.remove('status-on');
    backendStatus.classList.add('status-off');
    return false;
  }
}

// Check backend status periodically
setInterval(checkBackendStatus, 5000); // Check every 5 seconds

// Initial backend status check
checkBackendStatus();

// Function to perform a search
async function performSearch() {
  const query = searchInput.value.trim();
  const shouldHighlight = document.getElementById('highlight-checkbox').checked;
  
  if (!query) {
    searchResults.innerHTML = '<p>Please enter a search query.</p>';
    return;
  }

  // Check LLM service status before proceeding
  const isServiceRunning = await checkBackendStatus();
  if (!isServiceRunning) {
    alert('LLM Service is down. Please start the service first before searching.');
    return;
  }
  
  console.log('Searching for:', query);
  searchResults.innerHTML = '<p>Searching...</p>';
  
  try {
    // Get user preferences for context
    let userContext = {};
    try {
      const prefsResponse = await fetch('http://localhost:5000/api/preferences');
      
      if (!prefsResponse.ok) {
        console.log(`Preferences endpoint returned HTTP ${prefsResponse.status} - backend may not have new routes yet`);
        userContext = {};
      } else {
        const prefsResult = await prefsResponse.json();
        if (prefsResult.success) {
          userContext = prefsResult.preferences;
        }
      }
    } catch (error) {
      console.log('Preferences not available yet (normal if backend not restarted):', error.message);
      userContext = {};
    }
    
    const response = await chrome.runtime.sendMessage({ 
      action: 'search', 
      query: query,
      user_context: userContext
    });
    
    if (response && response.results) {
      // Remove duplicates based on URL
      const uniqueResults = response.results.reduce((acc, current) => {
        // Check if we already have this URL
        const existingResult = acc.find(item => item.url === current.url);
        if (!existingResult) {
          // If no existing result with this URL, add it
          acc.push(current);
        } else {
          // If we have a result with this URL, keep the one with higher score
          if (current.score > existingResult.score) {
            const index = acc.indexOf(existingResult);
            acc[index] = current;
          }
        }
        return acc;
      }, []);

      // Sort results by score in descending order
      uniqueResults.sort((a, b) => (b.score || 0) - (a.score || 0));
      
      searchStats.textContent = `Found ${uniqueResults.length} unique results`;
      searchResults.innerHTML = '';
      
      uniqueResults.forEach(result => {
        const resultItem = document.createElement('div');
        resultItem.className = 'result-item';
        
        // Create title element if title exists
        let resultTitle = null;
        if (result.title) {
          resultTitle = document.createElement('div');
          resultTitle.className = 'result-title';
          resultTitle.textContent = result.title;
          resultItem.appendChild(resultTitle);
        }
        
        const resultText = document.createElement('div');
        resultText.className = 'result-text';
        resultText.textContent = result.content;
        
        const resultUrl = document.createElement('a');
        resultUrl.className = 'result-url';
        resultUrl.href = result.url;
        resultUrl.textContent = result.url;
        
        // Add click handler for highlighting
        resultItem.addEventListener('click', async () => {
          try {
            // Get the active tab
            const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
            
            // If we're on the same page
            if (activeTab.url === result.url) {
              if (shouldHighlight) {
                // Inject content script first
                try {
                  await chrome.scripting.executeScript({
                    target: { tabId: activeTab.id },
                    files: ['content.js']
                  });
                  
                  // Send highlight message after content script is injected
                  chrome.tabs.sendMessage(activeTab.id, {
                    action: 'highlightText',
                    text: query
                  }, (response) => {
                    if (chrome.runtime.lastError) {
                      console.error('Error highlighting:', chrome.runtime.lastError);
                    } else if (response && response.matches) {
                      console.log(`Highlighted ${response.matches} matches`);
                    }
                  });
                } catch (err) {
                  console.log('Content script already injected or injection failed:', err);
                }
              }
            } else {
              // Navigate to the page
              const tab = await chrome.tabs.create({ url: result.url, active: true });
              
              if (shouldHighlight) {
                // Store the search query for highlighting after page load
                chrome.storage.local.set({ pendingHighlight: { text: query } });
                
                // Wait for the page to load before highlighting
                chrome.tabs.onUpdated.addListener(function listener(tabId, info) {
                  if (tabId === tab.id && info.status === 'complete') {
                    // Remove the listener
                    chrome.tabs.onUpdated.removeListener(listener);
                    
                    // Inject content script and highlight
                    chrome.scripting.executeScript({
                      target: { tabId: tab.id },
                      files: ['content.js']
                    }).then(() => {
                      // Add a small delay to ensure content script is initialized
                      setTimeout(() => {
                        chrome.tabs.sendMessage(tab.id, {
                          action: 'highlightText',
                          text: query
                        }, (response) => {
                          if (chrome.runtime.lastError) {
                            console.error('Error highlighting:', chrome.runtime.lastError);
                            // Retry highlighting after a longer delay if it fails
                            setTimeout(() => {
                              chrome.tabs.sendMessage(tab.id, {
                                action: 'highlightText',
                                text: query
                              }, (retryResponse) => {
                                if (chrome.runtime.lastError) {
                                  console.error('Error highlighting on retry:', chrome.runtime.lastError);
                                } else if (retryResponse && retryResponse.matches) {
                                  console.log(`Highlighted ${retryResponse.matches} matches on retry`);
                                }
                              });
                            }, 1000);
                          } else if (response && response.matches) {
                            console.log(`Highlighted ${response.matches} matches`);
                          }
                        });
                      }, 500);
                    }).catch(err => {
                      console.error('Error injecting content script:', err);
                      // Retry content script injection after a delay
                      setTimeout(() => {
                        chrome.scripting.executeScript({
                          target: { tabId: tab.id },
                          files: ['content.js']
                        }).then(() => {
                          // Try highlighting again after content script is injected
                          setTimeout(() => {
                            chrome.tabs.sendMessage(tab.id, {
                              action: 'highlightText',
                              text: query
                            });
                          }, 500);
                        }).catch(retryErr => console.error('Error injecting content script on retry:', retryErr));
                      }, 1000);
                    });
                  }
                });
              }
            }
          } catch (error) {
            console.error('Error handling result click:', error);
          }
        });
        
        // Add "Add to Favorites" button
        const favoriteBtn = document.createElement('button');
        favoriteBtn.textContent = 'Add to Favorites';
        favoriteBtn.style.background = '#4caf50';
        favoriteBtn.style.marginTop = '5px';
        favoriteBtn.onclick = () => addFavorite(result.url, result.title || '', result.content || '');
        resultItem.appendChild(favoriteBtn);
        
        // Add category tag if available
        if (result.category && resultTitle) {
          const categoryTag = document.createElement('span');
          categoryTag.className = 'category-tag';
          categoryTag.textContent = result.category;
          categoryTag.style.cssText = `
            background-color: #e3f2fd;
            color: #1565c0;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
            margin-left: 5px;
            display: inline-block;
          `;
          
          // Insert category tag after title
          resultTitle.appendChild(categoryTag);
        }
        
        resultItem.appendChild(resultText);
        resultItem.appendChild(resultUrl);
        searchResults.appendChild(resultItem);
      });
    } else {
      searchStats.textContent = 'No results found';
    }
  } catch (error) {
    console.error('Error during search:', error);
    searchStats.textContent = 'Error: ' + error.message;
  }
}

// Save highlight preference
document.getElementById('highlight-checkbox').addEventListener('change', function(e) {
  chrome.storage.local.set({ 'highlightEnabled': e.target.checked });
});

// Load highlight preference
chrome.storage.local.get(['highlightEnabled'], function(result) {
  document.getElementById('highlight-checkbox').checked = result.highlightEnabled || false;
});

// Function to load confidential sites
async function loadConfidentialSites() {
    console.log('Loading confidential sites list');
    
    try {
        const response = await new Promise((resolve) => {
            chrome.runtime.sendMessage(
                { action: 'getConfidentialSites' },
                response => {
                    if (chrome.runtime.lastError) {
                        console.error('Error getting confidential sites:', chrome.runtime.lastError);
                        resolve({ sites: [] });
                    } else {
                        resolve(response);
                    }
                }
            );
        });
        
        console.log('Got confidential sites response:', response);
        
        if (response && Array.isArray(response.sites)) {
            confidentialSites.value = response.sites.join('\n');
            console.log(`Loaded ${response.sites.length} confidential sites`);
        } else {
            console.error('Invalid response format for confidential sites');
            confidentialSites.value = '';
        }
    } catch (error) {
        console.error('Error loading confidential sites:', error);
        confidentialSites.value = '';
    }
}

// Function to save confidential sites
async function saveConfidentialSites() {
    const sites = confidentialSites.value
        .split('\n')
        .map(site => site.trim())
        .filter(site => site.length > 0);
    
    console.log(`Saving ${sites.length} confidential sites`);
    
    try {
        const response = await new Promise((resolve) => {
            chrome.runtime.sendMessage(
                { action: 'updateConfidentialSites', sites: sites },
                response => {
                    if (chrome.runtime.lastError) {
                        console.error('Error saving confidential sites:', chrome.runtime.lastError);
                        resolve({ success: false, error: chrome.runtime.lastError.message });
                    } else {
                        resolve(response);
                    }
                }
            );
        });
        
        console.log('Save confidential sites response:', response);
        
        if (response && response.success) {
            console.log('Settings saved successfully');
            addNotification('Settings saved successfully', 'success');
        } else {
            const errorMsg = response?.error || 'Unknown error';
            console.error('Failed to save settings:', errorMsg);
            addNotification(`Failed to save settings: ${errorMsg}`, 'error');
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        addNotification(`Error saving settings: ${error.message}`, 'error');
    }
}

// Function to download index
async function downloadIndex() {
    console.log('Downloading index...');
    exportStats.textContent = 'Preparing download...';
    
    try {
        const response = await fetch('http://localhost:5000/api/download-index', {
            method: 'GET'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Get the filename from the Content-Disposition header if available
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'semantic_search_index.zip';
        if (contentDisposition) {
            const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(contentDisposition);
            if (matches != null && matches[1]) {
                filename = matches[1].replace(/['"]/g, '');
            }
        }
        
        // Create a blob from the response
        const blob = await response.blob();
        
        // Create a link element and trigger download
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        exportStats.textContent = 'Index downloaded successfully!';
    } catch (error) {
        console.error('Error downloading index:', error);
        exportStats.textContent = `Error downloading index: ${error.message}`;
    }
}

// Function to get index stats
async function getIndexStats() {
  console.log('Getting index stats');
  
  exportStats.textContent = 'Loading index stats...';
  
  try {
    const response = await fetch('http://localhost:5000/api/stats', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    const result = await response.json();
    console.log('Index stats response:', result);
    
    if (result.status === 'success') {
      const stats = result.stats;
      const message = `Index contains ${stats.total_documents} documents with dimension ${stats.dimension}.`;
      exportStats.textContent = message;
      
      // Show download button
      downloadIndexButton.style.display = 'inline-block';
      
      // Show or hide regenerate button based on index size
      let regenerateButton = document.getElementById('regenerate-index');
      if (!regenerateButton) {
        regenerateButton = document.createElement('button');
        regenerateButton.id = 'regenerate-index';
        regenerateButton.textContent = 'Regenerate Test Data';
        regenerateButton.addEventListener('click', regenerateTestData);
        downloadIndexButton.parentNode.insertBefore(regenerateButton, downloadIndexButton.nextSibling);
      }
      
      if (stats.total_documents === 0) {
        regenerateButton.style.display = 'inline-block';
        downloadIndexButton.style.display = 'none';
      } else {
        regenerateButton.style.display = 'none';
        downloadIndexButton.style.display = 'inline-block';
      }
    } else {
      const errorMsg = result.error || 'Unknown error getting index stats';
      exportStats.textContent = `Error: ${errorMsg}`;
      console.error('Failed to get index stats:', errorMsg);
      
      // Show regenerate button when there's an error
      let regenerateButton = document.getElementById('regenerate-index');
      if (!regenerateButton) {
        regenerateButton = document.createElement('button');
        regenerateButton.id = 'regenerate-index';
        regenerateButton.textContent = 'Regenerate Test Data';
        regenerateButton.addEventListener('click', regenerateTestData);
        downloadIndexButton.parentNode.insertBefore(regenerateButton, downloadIndexButton.nextSibling);
      }
      regenerateButton.style.display = 'inline-block';
      downloadIndexButton.style.display = 'none';
    }
  } catch (error) {
    console.error('Error getting index stats:', error);
    exportStats.textContent = `Error: ${error.message}`;
    
    // Show regenerate button on error
    let regenerateButton = document.getElementById('regenerate-index');
    if (!regenerateButton) {
      regenerateButton = document.createElement('button');
      regenerateButton.id = 'regenerate-index';
      regenerateButton.textContent = 'Regenerate Test Data';
      regenerateButton.addEventListener('click', regenerateTestData);
      downloadIndexButton.parentNode.insertBefore(regenerateButton, downloadIndexButton.nextSibling);
    }
    regenerateButton.style.display = 'inline-block';
    downloadIndexButton.style.display = 'none';
  }
}

// Function to regenerate test data
async function regenerateTestData() {
  console.log('Requesting test data regeneration');
  
  exportStats.textContent = 'Regenerating test data...';
  
  try {
    const response = await fetch('http://localhost:5000/api/regenerate-test-data', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    const result = await response.json();
    console.log('Regenerate test data response:', result);
    
    if (result.success) {
      exportStats.textContent = 'Test data regenerated successfully. Try searching for "machine learning", "web development", or "data science".';
      setTimeout(getIndexStats, 1000); // Refresh stats after a delay
    } else {
      const errorMsg = result.error || 'Unknown error regenerating test data';
      exportStats.textContent = `Error: ${errorMsg}`;
      console.error('Failed to regenerate test data:', errorMsg);
    }
  } catch (error) {
    console.error('Error regenerating test data:', error);
    exportStats.textContent = `Error: ${error.message}`;
  }
}

// Function to update status display
function updateStatus(status, url, error = null) {
    const statusElement = document.getElementById('status');
    const statusText = document.getElementById('status-text');
    const errorElement = document.getElementById('error-message');
    
    if (!statusElement || !statusText || !errorElement) {
        console.error('Status elements not found in DOM');
        return;
    }
    
    // Clear previous status
    statusElement.className = '';
    statusText.textContent = '';
    errorElement.textContent = '';
    errorElement.style.display = 'none';
    
    // Update status based on type
    switch (status) {
        case 'started':
            statusElement.classList.add('indexing');
            statusText.textContent = 'Indexing page...';
            break;
            
        case 'completed':
            statusElement.classList.add('completed');
            statusText.textContent = 'Page indexed successfully!';
            break;
            
        case 'error':
            statusElement.classList.add('error');
            statusText.textContent = 'Error indexing page';
            if (error) {
                errorElement.textContent = error;
                errorElement.style.display = 'block';
            }
            break;
            
        case 'skipped':
            statusElement.classList.add('skipped');
            statusText.textContent = 'Page skipped';
            if (error) {
                errorElement.textContent = error;
                errorElement.style.display = 'block';
            }
            // Reset status after 3 seconds
            setTimeout(() => {
                statusElement.className = 'idle';
                statusText.textContent = 'Ready to search';
                errorElement.textContent = '';
                errorElement.style.display = 'none';
            }, NOTIFICATION_DURATION);
            break;
            
        default:
            statusElement.classList.add('idle');
            statusText.textContent = 'Ready to search';
    }
    
    console.log('Updated status display:', status, 'for URL:', url);
}

async function getConfidentialSites() {
    console.log('Requesting confidential sites list...');
    try {
        const response = await chrome.runtime.sendMessage({ action: 'getConfidentialSites' });
        console.log('Got confidential sites response:', response);
        if (response && response.sites) {
            console.log('Loaded', response.sites.length, 'confidential sites');
            return response.sites;
        } else {
            console.warn('No sites in response:', response);
            return [];
        }
    } catch (error) {
        console.error('Error getting confidential sites:', error);
        return [];
    }
}

// Function to clear all indexed data
async function clearAllData() {
    // Confirm with the user
    const confirmed = confirm(
        'WARNING: This will permanently delete all indexed data!\n\n' +
        'This includes:\n' +
        '- All web pages you have visited and indexed\n' +
        '- Search history\n' +
        '- Index metadata\n\n' +
        'This action CANNOT be undone!\n\n' +
        'Do you want to continue?'
    );
    
    if (!confirmed) {
        console.log('User cancelled data clearing');
        return;
    }
    
    console.log('Clearing all indexed data...');
    
    try {
        // Call the backend API to clear the index
        const response = await fetch('http://localhost:5000/api/clear-index', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            addNotification('All indexed data cleared successfully!', 'success');
            
            // Also update the stats display if we're on the export tab
            if (document.getElementById('export-tab').classList.contains('active')) {
                setTimeout(getIndexStats, 500);
            }
        } else {
            throw new Error(result.error || 'Unknown error');
        }
    } catch (error) {
        console.error('Error clearing indexed data:', error);
        addNotification(`Error clearing data: ${error.message}`, 'error');
    }
}

// Function to initialize category checkboxes
function initializeCategoryCheckboxes() {
    const categories = ['Sports', 'Politics', 'Financial', 'Health & Medical', 'Current Affairs', 'Technology', 'Others'];
    const container = document.getElementById('category-checkboxes');
    
    categories.forEach(category => {
        const label = document.createElement('label');
        label.style.display = 'flex';
        label.style.alignItems = 'center';
        label.style.margin = '5px 0';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = category;
        checkbox.id = `category-${category.toLowerCase().replace(/\s+/g, '-')}`;
        checkbox.style.marginRight = '5px';
        
        const text = document.createTextNode(category);
        
        label.appendChild(checkbox);
        label.appendChild(text);
        container.appendChild(label);
    });
}

// Function to load user preferences
async function loadUserPreferences() {
    try {
        const response = await fetch('http://localhost:5000/api/preferences');
        
        if (!response.ok) {
            console.error(`HTTP error loading preferences: ${response.status}`);
            return;
        }
        
        const result = await response.json();
        
        if (result.success) {
            const prefs = result.preferences;
            
            document.getElementById('pref-interests').value = prefs.interests || '';
            document.getElementById('pref-location').value = prefs.location || '';
            document.getElementById('pref-topics').value = prefs.favorite_topics || '';
            document.getElementById('pref-taste').value = prefs.taste_preferences || '';
            
            document.getElementById('highlight-search-terms').checked = prefs.highlight_search_terms !== false;
            document.getElementById('categorize-results').checked = prefs.categorize_results === true;
            document.getElementById('skip-confidential').checked = prefs.skip_confidential_sites !== false;
            
            // Set category checkboxes
            if (prefs.categories && Array.isArray(prefs.categories)) {
                prefs.categories.forEach(category => {
                    const checkbox = document.getElementById(`category-${category.toLowerCase().replace(/\s+/g, '-')}`);
                    if (checkbox) {
                        checkbox.checked = true;
                    }
                });
            }
        }
    } catch (error) {
        console.error('Error loading preferences:', error);
    }
}

// Function to save user preferences
async function saveUserPreferences() {
    const interests = document.getElementById('pref-interests').value;
    const location = document.getElementById('pref-location').value;
    const topics = document.getElementById('pref-topics').value;
    const taste = document.getElementById('pref-taste').value;
    
    const highlight = document.getElementById('highlight-search-terms').checked;
    const categorize = document.getElementById('categorize-results').checked;
    const skipConf = document.getElementById('skip-confidential').checked;
    
    // Get selected categories
    const categoryCheckboxes = document.querySelectorAll('#category-checkboxes input[type="checkbox"]');
    const selectedCategories = Array.from(categoryCheckboxes)
        .filter(cb => cb.checked)
        .map(cb => cb.value);
    
    const preferences = {
        interests,
        location,
        favorite_topics: topics,
        taste_preferences: taste,
        highlight_search_terms: highlight,
        categorize_results: categorize,
        skip_confidential_sites: skipConf,
        categories: selectedCategories
    };
    
    try {
        const response = await fetch('http://localhost:5000/api/preferences', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(preferences)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            addNotification('Preferences saved successfully', 'success');
        } else {
            addNotification('Failed to save preferences', 'error');
        }
    } catch (error) {
        console.error('Error saving preferences:', error);
        addNotification(`Error saving preferences: ${error.message}. Make sure backend server is running and has been restarted.`, 'error');
    }
}

// Function to load favorites
async function loadFavorites() {
    const favoritesList = document.getElementById('favorites-list');
    
    try {
        const response = await fetch('http://localhost:5000/api/favorites');
        
        if (!response.ok) {
            console.log('Favorites endpoint not available yet');
            favoritesList.innerHTML = '<p>Favorites feature coming soon. Please restart backend server.</p>';
            return;
        }
        
        const result = await response.json();
        
        if (result.success && result.favorites && result.favorites.length > 0) {
            favoritesList.innerHTML = '';
            
            result.favorites.forEach(fav => {
                const item = document.createElement('div');
                item.className = 'result-item';
                item.style.marginBottom = '10px';
                
                if (fav.title) {
                    const title = document.createElement('div');
                    title.className = 'result-title';
                    title.textContent = fav.title;
                    item.appendChild(title);
                }
                
                const url = document.createElement('a');
                url.className = 'result-url';
                url.href = fav.url;
                url.textContent = fav.url;
                url.target = '_blank';
                item.appendChild(url);
                
                const deleteBtn = document.createElement('button');
                deleteBtn.textContent = 'Remove';
                deleteBtn.style.background = '#d32f2f';
                deleteBtn.style.marginTop = '5px';
                deleteBtn.onclick = () => removeFavorite(fav.url);
                item.appendChild(deleteBtn);
                
                favoritesList.appendChild(item);
            });
        } else {
            favoritesList.innerHTML = '<p>No favorites yet. Search results can be marked as favorites.</p>';
        }
    } catch (error) {
        console.log('Favorites not available:', error.message);
        favoritesList.innerHTML = '<p>Favorites feature not available yet. Please restart backend server with new routes.</p>';
    }
}

// Function to add item to favorites
async function addFavorite(url, title, content) {
    try {
        const response = await fetch('http://localhost:5000/api/favorites', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url,
                title,
                content
            })
        });
        
        if (!response.ok) {
            console.log('Favorites endpoint not available');
            addNotification('Favorites feature not available yet. Please restart backend.', 'error');
            return;
        }
        
        const result = await response.json();
        
        if (result.success) {
            addNotification('Added to favorites', 'success');
        }
    } catch (error) {
        console.log('Favorites not available:', error.message);
        addNotification('Favorites feature not available yet', 'error');
    }
}

// Function to remove item from favorites
async function removeFavorite(url) {
    try {
        const response = await fetch('http://localhost:5000/api/favorites', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url })
        });
        
        if (!response.ok) {
            addNotification('Favorites feature not available', 'error');
            return;
        }
        
        const result = await response.json();
        
        if (result.success) {
            loadFavorites();
            addNotification('Removed from favorites', 'success');
        }
    } catch (error) {
        console.log('Favorites not available:', error.message);
        addNotification('Favorites feature not available yet', 'error');
    }
} 