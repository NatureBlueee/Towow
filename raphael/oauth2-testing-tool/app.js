/**
 * app.js - Main Application Logic
 * Orchestrates OAuth2 flow, configuration management, and user interactions
 */

// Application state
const AppState = {
    flowState: 'idle', // idle, authorizing, code_received, exchanging, completed, error
    authCode: null,
    config: null,
    tokenSet: null
};

// Deep link timeout for app detection
const OPEN_TIMEOUT = 2500;

/**
 * Try to open app with scheme URL
 * @param {string} schemeUrl - Deep link scheme URL
 * @param {Function} onFail - Callback when app is not installed
 */
function tryOpenAppWithScheme(schemeUrl, onFail) {
    let hidden = false;

    const onVisibilityChange = () => {
        if (document.hidden || document.visibilityState === 'hidden') {
            hidden = true;
        }
    };
    document.addEventListener('visibilitychange', onVisibilityChange);

    const timer = setTimeout(() => {
        document.removeEventListener('visibilitychange', onVisibilityChange);
        if (!hidden) {
            onFail();
        }
    }, OPEN_TIMEOUT);

    const iframe = document.createElement('iframe');
    iframe.style.cssText = 'display:none;width:0;height:0;';
    iframe.src = schemeUrl;
    document.body.appendChild(iframe);

    setTimeout(() => {
        try {
            document.body.removeChild(iframe);
        } catch(e) {}
    }, 500);
}

/**
 * Initialize application on page load
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('OAuth2 Testing Frontend initialized');

    // Load configuration from localStorage
    loadConfiguration();

    // Initialize UI components
    UI.initCopyButtons();
    UI.initErrorToggles();

    // Setup event handlers
    setupEventHandlers();

    // Check for OAuth callback
    handleOAuthCallback();

    // Load existing tokens if present
    loadExistingTokens();
});

/**
 * Load configuration from localStorage and populate form
 */
function loadConfiguration() {
    const config = Config.loadConfig();
    if (config) {
        AppState.config = config;

        // Populate form fields
        document.getElementById('app-key').value = config.appKey || '';
        document.getElementById('app-secret').value = config.appSecret || '';
        document.getElementById('redirect-uri').value = config.redirectUri || '';
        document.getElementById('api-base-url').value = config.apiBaseUrl || '';
        document.getElementById('authorization-url').value = config.authorizationUrl || 'https://mindos-devusk8s.mindverse.ai/oauth';

        console.log('Configuration loaded from localStorage');

        // Update UI based on local/remote API
        updateAuthFlowUI(config);
    }
}

/**
 * Check if API is local (labs_apps_backend)
 */
function isLocalApi(apiBaseUrl) {
    return apiBaseUrl && (apiBaseUrl.includes('127.0.0.1') || apiBaseUrl.includes('localhost:8000'));
}

/**
 * Update authorization flow UI based on local or remote API
 */
function updateAuthFlowUI(config) {
    const isLocal = isLocalApi(config.apiBaseUrl);
    const oauthRedirectFlow = document.getElementById('oauth-redirect-flow');
    const manualCodeFlow = document.getElementById('manual-code-flow');

    if (isLocal) {
        // Show manual code entry for local API
        if (oauthRedirectFlow) oauthRedirectFlow.style.display = 'none';
        if (manualCodeFlow) {
            manualCodeFlow.style.display = 'block';
            // Generate curl command
            updateCurlCommand(config);
        }
        console.log('Local API detected - showing manual code entry');
    } else {
        // Show standard OAuth redirect flow
        if (oauthRedirectFlow) oauthRedirectFlow.style.display = 'block';
        if (manualCodeFlow) manualCodeFlow.style.display = 'none';
        console.log('Remote API detected - showing standard OAuth flow');
    }
}

/**
 * Generate and display curl command for local API authorization
 */
function updateCurlCommand(config) {
    const curlDisplay = document.getElementById('curl-command-display');
    if (!curlDisplay || !config.appKey) return;

    const curlCommand = `curl -X POST 'http://${getApiHost(config.apiBaseUrl)}/api/oauth/authorize/external' \\
  -H 'Content-Type: application/json' \\
  -H 'Authorization: Bearer <YOUR_AUTH_TOKEN>' \\
  -d '{
    "client_id": "${config.appKey}",
    "redirect_uri": "${config.redirectUri || 'http://localhost:8080'}",
    "scope": ["user.info.name", "chat"],
    "response_type": "code"
  }'`;

    curlDisplay.textContent = curlCommand;
}

/**
 * Extract host from API base URL
 */
function getApiHost(apiBaseUrl) {
    try {
        const url = new URL(apiBaseUrl);
        return url.host;
    } catch {
        return '127.0.0.1:8000';
    }
}

/**
 * Load existing tokens from localStorage
 */
function loadExistingTokens() {
    const tokenSet = Config.loadTokenSet();
    if (tokenSet) {
        AppState.tokenSet = tokenSet;
        UI.displayTokens(tokenSet);
        console.log('Existing tokens loaded from localStorage');
    }
}

/**
 * Setup all event handlers
 */
function setupEventHandlers() {
    // Configuration form submission
    const configForm = document.getElementById('config-form');
    if (configForm) {
        configForm.addEventListener('submit', handleConfigSubmit);
    }

    // Authorization flow buttons (standard OAuth redirect)
    const startAuthBtn = document.getElementById('start-auth-btn');
    if (startAuthBtn) {
        startAuthBtn.addEventListener('click', handleStartAuthorization);
    }

    const resetFlowBtn = document.getElementById('reset-flow-btn');
    if (resetFlowBtn) {
        resetFlowBtn.addEventListener('click', handleResetFlow);
    }

    // Manual code entry buttons (local API)
    const submitManualCodeBtn = document.getElementById('submit-manual-code-btn');
    if (submitManualCodeBtn) {
        submitManualCodeBtn.addEventListener('click', handleSubmitManualCode);
    }

    const resetFlowBtnManual = document.getElementById('reset-flow-btn-manual');
    if (resetFlowBtnManual) {
        resetFlowBtnManual.addEventListener('click', handleResetFlow);
    }

    const exchangeTokenBtn = document.getElementById('exchange-token-btn');
    if (exchangeTokenBtn) {
        exchangeTokenBtn.addEventListener('click', handleExchangeToken);
    }

    // Token refresh button
    const refreshTokenBtn = document.getElementById('refresh-token-btn');
    if (refreshTokenBtn) {
        refreshTokenBtn.addEventListener('click', handleRefreshToken);
    }

    // API testing button
    const testUserinfoBtn = document.getElementById('test-userinfo-btn');
    if (testUserinfoBtn) {
        testUserinfoBtn.addEventListener('click', handleTestUserInfo);
    }
}

/**
 * Handle configuration form submission
 */
function handleConfigSubmit(event) {
    event.preventDefault();

    // Clear previous errors
    UI.hideError('config-error');
    UI.clearStatus('config-status');

    // Get form data
    const formData = new FormData(event.target);
    const config = {
        appKey: formData.get('appKey'),
        appSecret: formData.get('appSecret'),
        redirectUri: formData.get('redirectUri'),
        apiBaseUrl: formData.get('apiBaseUrl'),
        authorizationUrl: formData.get('authorizationUrl')
    };

    // Validate configuration
    const validation = Config.validateConfig(config);
    if (!validation.valid) {
        UI.showError('config-error', 'Configuration validation failed', {
            responseBody: { errors: validation.errors }
        });
        return;
    }

    // Save configuration
    const saved = Config.saveConfig(config);
    if (saved) {
        AppState.config = config;
        UI.showStatus('config-status', '✓ Configuration saved successfully', 'success');

        // Update auth flow UI based on local/remote API
        updateAuthFlowUI(config);

        // Clear success message after 3 seconds
        setTimeout(() => {
            UI.clearStatus('config-status');
        }, 3000);

        console.log('Configuration saved successfully');
    } else {
        UI.showError('config-error', 'Failed to save configuration', {
            responseBody: { error: 'localStorage save failed' }
        });
    }
}

/**
 * Handle OAuth callback (check for code in URL - OAuth 2.0 standard)
 */
function handleOAuthCallback() {
    const urlParams = new URLSearchParams(window.location.search);

    // Check for error response first
    const error = urlParams.get('error');
    if (error) {
        const errorDescription = urlParams.get('error_description') || 'Authorization denied';
        console.log('OAuth callback received with error:', error);

        AppState.flowState = 'error';
        UI.showError('auth-error', `Authorization failed: ${errorDescription}`, {
            responseBody: { error, error_description: errorDescription }
        });

        // Clean URL
        window.history.replaceState({}, document.title, window.location.pathname);
        return;
    }

    // Check for authorization code (OAuth 2.0 uses 'code' parameter)
    const authCode = urlParams.get('code');
    const returnedState = urlParams.get('state');

    if (authCode) {
        console.log('OAuth callback received with code');

        // Verify state parameter for CSRF protection
        if (returnedState && !OAuth2.verifyState(returnedState)) {
            console.error('State mismatch - possible CSRF attack');
            UI.showError('auth-error', 'Security error: State mismatch', {
                responseBody: { error: 'state_mismatch', error_description: 'The state parameter does not match' }
            });
            window.history.replaceState({}, document.title, window.location.pathname);
            return;
        }

        AppState.authCode = authCode;
        AppState.flowState = 'code_received';

        // Display auth code
        UI.displayAuthCode(authCode);

        // Update flow status
        UI.showStatus('flow-status', 'Authorization code received', 'success');

        // Clean URL (remove query parameters)
        window.history.replaceState({}, document.title, window.location.pathname);
    }
}

/**
 * Handle start authorization button click
 */
function handleStartAuthorization() {
    // Clear previous errors
    UI.hideError('auth-error');
    UI.clearStatus('flow-status');

    // Validate configuration
    if (!AppState.config) {
        UI.showError('auth-error', 'Configuration not found - Please save configuration first', {});
        return;
    }

    const validation = Config.validateConfig(AppState.config);
    if (!validation.valid) {
        UI.showError('auth-error', 'Invalid configuration - Please check your settings', {
            responseBody: { errors: validation.errors }
        });
        return;
    }

    // Update flow state
    AppState.flowState = 'authorizing';

    // Disable start button and show status
    UI.setButtonEnabled('start-auth-btn', false);
    UI.showStatus('flow-status', 'Trying to open app...', '');

    // Build deep link for app authorization
    const deepLinkUrl = OAuth2.buildAuthorizationDeepLink(AppState.config);
    console.log('Trying to open app with deep link:', deepLinkUrl);

    // Try to open app with deep link
    tryOpenAppWithScheme(deepLinkUrl, () => {
        // App not installed, fallback to web authorization
        console.log('App not detected, falling back to web authorization');
        UI.showStatus('flow-status', 'App not installed, redirecting to web authorization...', '');

        // Build web authorization URL
        const authUrl = OAuth2.buildAuthorizationUrl(AppState.config);
        if (authUrl) {
            console.log('Redirecting to authorization URL:', authUrl);
            window.location.href = authUrl;
        } else {
            // Local API doesn't support web authorization
            UI.showStatus('flow-status', 'App not installed and web authorization not available', 'error');
            UI.setButtonEnabled('start-auth-btn', true);
        }
    });
}

/**
 * Handle reset flow button click
 */
function handleResetFlow() {
    // Reset flow state
    AppState.flowState = 'idle';
    AppState.authCode = null;

    // Hide displays
    UI.toggleElement('authcode-display', false);
    UI.toggleElement('exchange-controls', false);

    // Clear status and errors
    UI.clearStatus('flow-status');
    UI.clearStatus('flow-status-manual');
    UI.hideError('auth-error');

    // Enable start authorization button
    UI.setButtonEnabled('start-auth-btn', true);

    // Clear manual code input
    const manualCodeInput = document.getElementById('manual-auth-code');
    if (manualCodeInput) manualCodeInput.value = '';

    console.log('Flow reset to idle state');
}

/**
 * Handle manual code submission (for local API testing)
 */
function handleSubmitManualCode() {
    // Clear previous errors
    UI.hideError('auth-error');
    UI.clearStatus('flow-status-manual');

    // Get manual code input
    const manualCodeInput = document.getElementById('manual-auth-code');
    const authCode = manualCodeInput ? manualCodeInput.value.trim() : '';

    if (!authCode) {
        UI.showStatus('flow-status-manual', 'Please enter authorization code', 'error');
        return;
    }

    // Validate configuration
    if (!AppState.config) {
        UI.showError('auth-error', 'Configuration not found - Please save configuration first', {});
        return;
    }

    // Set state
    AppState.authCode = authCode;
    AppState.flowState = 'code_received';

    // Display auth code
    UI.displayAuthCode(authCode);

    // Update flow status
    UI.showStatus('flow-status-manual', 'Authorization code received', 'success');

    console.log('Manual authorization code submitted');
}

/**
 * Handle exchange token button click
 */
async function handleExchangeToken() {
    // Clear previous errors
    UI.hideError('auth-error');
    UI.hideError('token-error');

    // Validate state
    if (!AppState.authCode) {
        UI.showError('auth-error', 'No authorization code available', {});
        return;
    }

    if (!AppState.config) {
        UI.showError('auth-error', 'Configuration not found', {});
        return;
    }

    // Update state
    AppState.flowState = 'exchanging';

    // Show loading
    UI.showLoading('exchange-token-btn');
    UI.showStatus('flow-status', 'Exchanging code for tokens...', '');

    try {
        // Exchange authCode for tokens
        const tokenSet = await OAuth2.exchangeToken(AppState.authCode, AppState.config);

        // Save tokens and load back to get expiresAt
        Config.saveTokenSet(tokenSet);
        AppState.tokenSet = Config.loadTokenSet();

        // Update state
        AppState.flowState = 'completed';

        // Hide loading
        UI.hideLoading('exchange-token-btn');

        // Display tokens (use AppState.tokenSet which has expiresAt)
        UI.displayTokens(AppState.tokenSet);

        // Show success status
        UI.showStatus('flow-status', '✓ Token exchange successful', 'success');

        // Re-enable start authorization for new flow
        UI.setButtonEnabled('start-auth-btn', true);

        console.log('Token exchange completed successfully');

    } catch (error) {
        console.error('Token exchange failed:', error);

        // Update state
        AppState.flowState = 'error';

        // Hide loading
        UI.hideLoading('exchange-token-btn');

        // Determine error message
        let errorSummary = 'Token exchange failed';
        if (error.statusCode === 400) {
            errorSummary = 'Token exchange failed - Invalid authorization code';
        } else if (error.statusCode === 401 || error.statusCode === 403) {
            errorSummary = 'Token exchange failed - Invalid APP_KEY or APP_SECRET';
        } else if (!error.statusCode) {
            errorSummary = 'Token exchange failed - Network error';
        }

        // Show error
        UI.showError('auth-error', errorSummary, error);

        // Update status
        UI.showStatus('flow-status', errorSummary, 'error');
    }
}

/**
 * Handle refresh token button click
 */
async function handleRefreshToken() {
    // Clear previous errors
    UI.hideError('token-error');

    // Validate state
    if (!AppState.tokenSet || !AppState.tokenSet.refreshToken) {
        UI.showError('token-error', 'No refresh token available', {});
        return;
    }

    if (!AppState.config) {
        UI.showError('token-error', 'Configuration not found', {});
        return;
    }

    // Show loading
    UI.showLoading('refresh-token-btn');

    try {
        // Refresh token
        const newTokenSet = await OAuth2.refreshToken(AppState.tokenSet.refreshToken, AppState.config);

        // Save new tokens and load back to get expiresAt
        Config.saveTokenSet(newTokenSet);
        AppState.tokenSet = Config.loadTokenSet();

        // Hide loading
        UI.hideLoading('refresh-token-btn');

        // Update token display
        UI.displayTokens(AppState.tokenSet);

        console.log('Token refresh completed successfully');

    } catch (error) {
        console.error('Token refresh failed:', error);

        // Hide loading
        UI.hideLoading('refresh-token-btn');

        // Determine error message
        let errorSummary = 'Token refresh failed';
        if (error.statusCode === 400) {
            errorSummary = 'Token refresh failed - Refresh token expired or invalid';
        } else if (error.statusCode === 401 || error.statusCode === 403) {
            errorSummary = 'Token refresh failed - Invalid APP_KEY or APP_SECRET';
        } else if (!error.statusCode) {
            errorSummary = 'Token refresh failed - Network error';
        }

        // Show error
        UI.showError('token-error', errorSummary, error);
    }
}

/**
 * Handle test user info button click
 */
async function handleTestUserInfo() {
    // Clear previous errors
    UI.hideError('api-error');

    // Validate state
    if (!AppState.tokenSet || !AppState.tokenSet.accessToken) {
        UI.showError('api-error', 'No access token available - Complete authorization first', {});
        return;
    }

    if (!AppState.config) {
        UI.showError('api-error', 'Configuration not found', {});
        return;
    }

    // Check if token is expired
    if (Config.isTokenExpired(AppState.tokenSet)) {
        UI.showError('api-error', 'Access token expired - Please refresh token first', {});
        return;
    }

    // Show loading
    UI.showLoading('test-userinfo-btn');

    try {
        // Call user info API
        const response = await OAuth2.getUserInfo(
            AppState.tokenSet.accessToken,
            AppState.tokenSet.openId,
            AppState.config
        );

        // Hide loading
        UI.hideLoading('test-userinfo-btn');

        // Display response
        UI.displayApiResponse(response);

        console.log('User info API call completed successfully');

    } catch (error) {
        console.error('User info API call failed:', error);

        // Hide loading
        UI.hideLoading('test-userinfo-btn');

        // Determine error message
        let errorSummary = 'API call failed';
        if (error.statusCode === 401) {
            errorSummary = 'API call failed - Access token expired or invalid';
        } else if (!error.statusCode) {
            errorSummary = 'API call failed - Network error';
        }

        // Show error
        UI.showError('api-error', errorSummary, error);
    }
}
