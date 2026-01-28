/**
 * oauth2.js - OAuth2 API Client Module
 * Handles all OAuth2 API interactions with me.bot platform
 */

const OAuth2 = {
    /**
     * Check if the API is local (labs_apps_backend)
     * @param {string} apiBaseUrl - API base URL
     * @returns {boolean} True if local API
     */
    isLocalApi(apiBaseUrl) {
        return apiBaseUrl.includes('127.0.0.1') || apiBaseUrl.includes('localhost:8000');
    },

    /**
     * Exchange authorization code for tokens
     * @param {string} authCode - Authorization code
     * @param {Object} config - Configuration object
     * @returns {Promise<Object>} Token set object
     */
    async exchangeToken(authCode, config) {
        const isLocal = this.isLocalApi(config.apiBaseUrl);
        let response;

        console.log(`Exchanging authorization code for tokens (${isLocal ? 'local' : 'remote'} API)...`);

        try {
            if (isLocal) {
                // Local API: POST with form data
                const url = new URL('/api/oauth/token/code', config.apiBaseUrl);
                const formData = new URLSearchParams();
                formData.append('grant_type', 'authorization_code');
                formData.append('code', authCode);
                formData.append('redirect_uri', config.redirectUri);
                formData.append('client_id', config.appKey);
                formData.append('client_secret', config.appSecret);

                response = await fetch(url.toString(), {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    body: formData
                });
            } else {
                // Remote API (labs via gateway): POST with form data
                const url = new URL('/gate/lab/api/oauth/token/code', config.apiBaseUrl);
                const formData = new URLSearchParams();
                formData.append('grant_type', 'authorization_code');
                formData.append('code', authCode);
                formData.append('redirect_uri', config.redirectUri);
                formData.append('client_id', config.appKey);
                formData.append('client_secret', config.appSecret);

                response = await fetch(url.toString(), {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    body: formData
                });
            }

            const responseBody = await response.json();

            if (!response.ok || responseBody.code !== 0) {
                throw {
                    statusCode: response.status,
                    responseBody: responseBody,
                    requestParams: {
                        grantType: 'authorization_code',
                        code: authCode.substring(0, 8) + '...',  // Partial for security
                        appKey: config.appKey
                    }
                };
            }

            console.log('Token exchange successful');
            // Extract data field from response (backend returns {code, message, data})
            const data = responseBody.data || responseBody;

            // Normalize field names for local API (uses camelCase in response)
            return {
                accessToken: data.accessToken || data.access_token,
                refreshToken: data.refreshToken || data.refresh_token,
                openId: data.openId || data.open_id || 'local-user',  // Local API doesn't return openId
                expiresIn: data.expiresIn || data.expires_in || 7200,
                tokenType: data.tokenType || data.token_type || 'Bearer',
                scope: data.scope || []
            };

        } catch (error) {
            if (error.statusCode) {
                // API error
                throw error;
            } else {
                // Network error
                throw {
                    statusCode: null,
                    responseBody: { error: 'network_error', error_description: error.message },
                    requestParams: {
                        grantType: 'authorization_code',
                        appKey: config.appKey
                    }
                };
            }
        }
    },

    /**
     * Refresh access token using refresh token
     * @param {string} refreshToken - Refresh token
     * @param {Object} config - Configuration object
     * @returns {Promise<Object>} New token set object
     */
    async refreshToken(refreshToken, config) {
        const isLocal = this.isLocalApi(config.apiBaseUrl);
        let response;

        console.log(`Refreshing access token (${isLocal ? 'local' : 'remote'} API)...`);

        try {
            if (isLocal) {
                // Local API: POST with form data
                const url = new URL('/api/oauth/token/refresh', config.apiBaseUrl);
                const formData = new URLSearchParams();
                formData.append('grant_type', 'refresh_token');
                formData.append('refresh_token', refreshToken);
                formData.append('client_id', config.appKey);
                formData.append('client_secret', config.appSecret);

                response = await fetch(url.toString(), {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    body: formData
                });
            } else {
                // Remote API (labs via gateway): POST with form data
                const url = new URL('/gate/lab/api/oauth/token/refresh', config.apiBaseUrl);
                const formData = new URLSearchParams();
                formData.append('grant_type', 'refresh_token');
                formData.append('refresh_token', refreshToken);
                formData.append('client_id', config.appKey);
                formData.append('client_secret', config.appSecret);

                response = await fetch(url.toString(), {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    body: formData
                });
            }

            const responseBody = await response.json();

            if (!response.ok || responseBody.code !== 0) {
                throw {
                    statusCode: response.status,
                    responseBody: responseBody,
                    requestParams: {
                        grantType: 'refresh_token',
                        refreshToken: refreshToken.substring(0, 8) + '...',
                        appKey: config.appKey
                    }
                };
            }

            console.log('Token refresh successful');
            // Extract data field from response (backend returns {code, message, data})
            const data = responseBody.data || responseBody;

            // Normalize field names for local API (uses camelCase in response)
            return {
                accessToken: data.accessToken || data.access_token,
                refreshToken: data.refreshToken || data.refresh_token,
                openId: data.openId || data.open_id || 'local-user',  // Local API doesn't return openId
                expiresIn: data.expiresIn || data.expires_in || 7200,
                tokenType: data.tokenType || data.token_type || 'Bearer',
                scope: data.scope || []
            };

        } catch (error) {
            if (error.statusCode) {
                throw error;
            } else {
                throw {
                    statusCode: null,
                    responseBody: { error: 'network_error', error_description: error.message },
                    requestParams: {
                        grantType: 'refresh_token',
                        appKey: config.appKey
                    }
                };
            }
        }
    },

    /**
     * Get user information using access token
     * @param {string} accessToken - Access token
     * @param {string} openId - User open ID
     * @param {Object} config - Configuration object
     * @returns {Promise<Object>} User information object
     */
    async getUserInfo(accessToken, openId, config) {
        const isLocal = this.isLocalApi(config.apiBaseUrl);
        let response;

        console.log(`Calling user info API (${isLocal ? 'local' : 'remote'})...`);

        const startTime = Date.now();

        try {
            if (isLocal) {
                // Local API: GET with Bearer token
                const url = new URL('/api/secondme/user/info', config.apiBaseUrl);
                response = await fetch(url.toString(), {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${accessToken}`,
                        'Content-Type': 'application/json'
                    }
                });
            } else {
                // Remote API (labs via gateway): GET with Bearer token
                const url = new URL('/gate/lab/api/secondme/user/info', config.apiBaseUrl);
                response = await fetch(url.toString(), {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${accessToken}`,
                        'Content-Type': 'application/json'
                    }
                });
            }

            const responseBody = await response.json();
            const endTime = Date.now();
            const duration = endTime - startTime;

            if (!response.ok || (responseBody.code !== undefined && responseBody.code !== 0)) {
                throw {
                    statusCode: response.status,
                    responseBody: responseBody,
                    duration: duration
                };
            }

            console.log('User info API call successful');
            return {
                statusCode: response.status,
                responseBody: responseBody.data || responseBody,
                duration: duration,
                success: true
            };

        } catch (error) {
            const endTime = Date.now();
            const duration = endTime - startTime;

            if (error.statusCode) {
                throw { ...error, duration: duration };
            } else {
                throw {
                    statusCode: null,
                    responseBody: { error: 'network_error', error_description: error.message },
                    duration: duration
                };
            }
        }
    },

    /**
     * Build OAuth authorization URL (OAuth 2.0 standard)
     * @param {Object} config - Configuration object
     * @returns {string} Authorization URL
     */
    buildAuthorizationUrl(config) {
        // Local API doesn't have web-based OAuth - return null
        if (this.isLocalApi(config.apiBaseUrl)) {
            console.log('Local API detected - no web-based authorization available');
            return null;
        }

        // Use configured authorization URL with OAuth 2.0 standard parameters
        const url = new URL(config.authorizationUrl);
        url.searchParams.append('client_id', config.appKey);
        url.searchParams.append('redirect_uri', config.redirectUri);
        url.searchParams.append('response_type', 'code');

        // Generate and add state for CSRF protection
        const state = this.generateState();
        url.searchParams.append('state', state);

        // Store state in sessionStorage for verification on callback
        sessionStorage.setItem('oauth2_state', state);

        return url.toString();
    },

    /**
     * Generate random state string for CSRF protection
     * @returns {string} Random state string
     */
    generateState() {
        const array = new Uint8Array(16);
        crypto.getRandomValues(array);
        return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
    },

    /**
     * Verify state parameter from callback
     * @param {string} returnedState - State from callback
     * @returns {boolean} Whether state is valid
     */
    verifyState(returnedState) {
        const storedState = sessionStorage.getItem('oauth2_state');
        if (!storedState || storedState !== returnedState) {
            return false;
        }
        // Clear state after verification
        sessionStorage.removeItem('oauth2_state');
        return true;
    },

    /**
     * Build OAuth authorization deep link for app
     * @param {Object} config - Configuration object
     * @returns {string} Deep link URL
     */
    buildAuthorizationDeepLink(config) {
        // Generate and store state for CSRF protection
        const state = this.generateState();
        sessionStorage.setItem('oauth2_state', state);

        // Build deep link: mebot://open?route=/oauth/authorize&client_id=xxx&redirect_uri=xxx&state=xxx
        let schemeUrl = 'mebot://open?route=/oauth/authorize';
        schemeUrl += '&client_id=' + encodeURIComponent(config.appKey);
        schemeUrl += '&redirect_uri=' + encodeURIComponent(config.redirectUri);
        schemeUrl += '&response_type=code';
        schemeUrl += '&state=' + encodeURIComponent(state);

        return schemeUrl;
    }
};

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.OAuth2 = OAuth2;
}
