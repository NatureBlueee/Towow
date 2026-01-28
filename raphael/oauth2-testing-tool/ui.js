/**
 * ui.js - UI State Management Module
 * Handles all UI updates, loading states, error displays, and user feedback
 */

const UI = {
    /**
     * Show loading state on a button
     * @param {string} buttonId - Button element ID
     */
    showLoading(buttonId) {
        const button = document.getElementById(buttonId);
        if (button) {
            button.disabled = true;
            button.classList.add('loading');
        }
    },

    /**
     * Hide loading state on a button
     * @param {string} buttonId - Button element ID
     */
    hideLoading(buttonId) {
        const button = document.getElementById(buttonId);
        if (button) {
            button.disabled = false;
            button.classList.remove('loading');
        }
    },

    /**
     * Show error panel with details
     * @param {string} panelId - Error panel element ID
     * @param {string} summary - User-friendly error summary
     * @param {Object} details - Detailed error information
     */
    showError(panelId, summary, details = {}) {
        const panel = document.getElementById(panelId);
        if (!panel) return;

        // Show panel
        panel.style.display = 'block';

        // Set summary
        const summaryEl = panel.querySelector('.error-summary');
        if (summaryEl) {
            summaryEl.textContent = summary;
        }

        // Set details
        const detailsEl = panel.querySelector('.error-details');
        if (detailsEl && details) {
            let detailsHtml = '';

            if (details.statusCode) {
                detailsHtml += `Status Code: ${details.statusCode}\n\n`;
            }

            if (details.responseBody) {
                detailsHtml += `Response Body:\n${JSON.stringify(details.responseBody, null, 2)}\n\n`;
            }

            if (details.requestParams) {
                detailsHtml += `Request Parameters:\n${JSON.stringify(details.requestParams, null, 2)}`;
            }

            // Use textContent to prevent XSS
            detailsEl.textContent = detailsHtml;
        }

        // Setup toggle button
        const toggleBtn = panel.querySelector('.error-toggle');
        if (toggleBtn && detailsEl) {
            toggleBtn.onclick = () => this.toggleErrorDetails(panelId);
        }
    },

    /**
     * Hide error panel
     * @param {string} panelId - Error panel element ID
     */
    hideError(panelId) {
        const panel = document.getElementById(panelId);
        if (panel) {
            panel.style.display = 'none';
            // Reset details to collapsed state
            const detailsEl = panel.querySelector('.error-details');
            if (detailsEl) {
                detailsEl.style.display = 'none';
            }
        }
    },

    /**
     * Toggle error details visibility
     * @param {string} panelId - Error panel element ID
     */
    toggleErrorDetails(panelId) {
        const panel = document.getElementById(panelId);
        if (!panel) return;

        const detailsEl = panel.querySelector('.error-details');
        const toggleBtn = panel.querySelector('.error-toggle');

        if (detailsEl && toggleBtn) {
            if (detailsEl.style.display === 'none' || detailsEl.style.display === '') {
                detailsEl.style.display = 'block';
                toggleBtn.textContent = 'Hide Details';
            } else {
                detailsEl.style.display = 'none';
                toggleBtn.textContent = 'Show Details';
            }
        }
    },

    /**
     * Show status message
     * @param {string} elementId - Status message element ID
     * @param {string} message - Message text
     * @param {string} type - Message type: 'success', 'error', or default
     */
    showStatus(elementId, message, type = '') {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = message;
            element.className = 'status-message' + (type ? ` ${type}` : '');
        }
    },

    /**
     * Clear status message
     * @param {string} elementId - Status message element ID
     */
    clearStatus(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = '';
            element.className = 'status-message';
        }
    },

    /**
     * Display token set in UI
     * @param {Object} tokenSet - Token set object
     */
    displayTokens(tokenSet) {
        if (!tokenSet) return;

        // Show token panel
        const tokenPanel = document.getElementById('token-panel');
        if (tokenPanel) {
            tokenPanel.style.display = 'block';
        }

        // Show API testing panel
        const apiPanel = document.getElementById('api-panel');
        if (apiPanel) {
            apiPanel.style.display = 'block';
        }

        // Display access token
        this.setElementText('access-token-value', tokenSet.accessToken);

        // Display refresh token
        this.setElementText('refresh-token-value', tokenSet.refreshToken);

        // Display open ID
        this.setElementText('openid-value', tokenSet.openId);

        // Display expires in
        const expiresInText = `${tokenSet.expiresIn} seconds (${Math.floor(tokenSet.expiresIn / 60)} minutes)`;
        this.setElementText('expires-in-value', expiresInText);

        // Display expiration time
        const expiryEl = document.getElementById('access-token-expiry');
        if (expiryEl) {
            const expiryText = Config.formatExpirationTime(tokenSet);
            expiryEl.textContent = expiryText;
            expiryEl.className = 'token-meta' + (Config.isTokenExpired(tokenSet) ? ' expired' : '');
        }
    },

    /**
     * Display authorization code
     * @param {string} authCode - Authorization code
     */
    displayAuthCode(authCode) {
        const display = document.getElementById('authcode-display');
        const valueEl = document.getElementById('authcode-value');
        const exchangeControls = document.getElementById('exchange-controls');

        if (display) display.style.display = 'block';
        if (valueEl) valueEl.textContent = authCode;
        if (exchangeControls) exchangeControls.style.display = 'block';
    },

    /**
     * Display API response
     * @param {Object} response - API response object
     */
    displayApiResponse(response) {
        const apiResponse = document.getElementById('api-response');
        if (!apiResponse) return;

        apiResponse.style.display = 'block';

        // Display status
        const statusEl = document.getElementById('response-status');
        if (statusEl) {
            statusEl.textContent = `Status: ${response.statusCode}`;
        }

        // Display response time
        const timeEl = document.getElementById('response-time');
        if (timeEl && response.duration) {
            timeEl.textContent = `Time: ${response.duration}ms`;
        }

        // Display response body
        const bodyEl = document.getElementById('response-body');
        if (bodyEl && response.responseBody) {
            // Use textContent to prevent XSS
            bodyEl.textContent = JSON.stringify(response.responseBody, null, 2);
        }

        // Show API panel
        const apiPanel = document.getElementById('api-panel');
        if (apiPanel) {
            apiPanel.style.display = 'block';
        }
    },

    /**
     * Set text content of an element (XSS-safe)
     * @param {string} elementId - Element ID
     * @param {string} text - Text content
     */
    setElementText(elementId, text) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = text || '';
        }
    },

    /**
     * Show/hide element
     * @param {string} elementId - Element ID
     * @param {boolean} show - Show (true) or hide (false)
     */
    toggleElement(elementId, show) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.display = show ? 'block' : 'none';
        }
    },

    /**
     * Enable/disable button
     * @param {string} buttonId - Button element ID
     * @param {boolean} enabled - Enable (true) or disable (false)
     */
    setButtonEnabled(buttonId, enabled) {
        const button = document.getElementById(buttonId);
        if (button) {
            button.disabled = !enabled;
        }
    },

    /**
     * Initialize copy-to-clipboard functionality
     */
    initCopyButtons() {
        document.querySelectorAll('.btn-copy').forEach(button => {
            button.addEventListener('click', (e) => {
                const targetId = e.target.getAttribute('data-copy-target');
                if (targetId) {
                    const targetEl = document.getElementById(targetId);
                    if (targetEl) {
                        const text = targetEl.textContent;
                        navigator.clipboard.writeText(text).then(() => {
                            // Visual feedback
                            const originalText = e.target.textContent;
                            e.target.textContent = '✓ Copied!';
                            setTimeout(() => {
                                e.target.textContent = originalText;
                            }, 2000);
                        }).catch(err => {
                            console.error('Failed to copy:', err);
                            alert('Failed to copy to clipboard');
                        });
                    }
                }
            });
        });
    },

    /**
     * Initialize error panel toggle handlers
     */
    initErrorToggles() {
        document.querySelectorAll('.error-toggle').forEach(button => {
            button.addEventListener('click', (e) => {
                const panel = e.target.closest('.error-panel');
                if (panel) {
                    const details = panel.querySelector('.error-details');
                    if (details) {
                        if (details.style.display === 'none' || details.style.display === '') {
                            details.style.display = 'block';
                            e.target.textContent = 'Hide Details';
                        } else {
                            details.style.display = 'none';
                            e.target.textContent = 'Show Details';
                        }
                    }
                }
            });
        });
    }
};

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.UI = UI;
}
