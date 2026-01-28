/**
 * config.js - Configuration Management Module
 * Handles localStorage operations for OAuth2 configuration and token storage
 */

const Config = {
    // localStorage keys
    STORAGE_KEYS: {
        CONFIG: 'oauth2Config',
        TOKENS: 'oauth2TokenSet'
    },

    /**
     * Load configuration from localStorage
     * @returns {Object|null} Configuration object or null if not found
     */
    loadConfig() {
        try {
            const configStr = localStorage.getItem(this.STORAGE_KEYS.CONFIG);
            if (!configStr) {
                return null;
            }
            return JSON.parse(configStr);
        } catch (error) {
            console.error('Error loading config from localStorage:', error);
            return null;
        }
    },

    /**
     * Save configuration to localStorage
     * @param {Object} config - Configuration object to save
     * @returns {boolean} Success status
     */
    saveConfig(config) {
        try {
            // Validate required fields
            if (!this.validateConfig(config)) {
                return false;
            }

            // Trim all string values
            const cleanConfig = {
                appKey: config.appKey.trim(),
                appSecret: config.appSecret.trim(),
                redirectUri: config.redirectUri.trim(),
                apiBaseUrl: config.apiBaseUrl.trim(),
                authorizationUrl: config.authorizationUrl ? config.authorizationUrl.trim() : 'https://app.me.bot/oauth'
            };

            localStorage.setItem(this.STORAGE_KEYS.CONFIG, JSON.stringify(cleanConfig));
            return true;
        } catch (error) {
            console.error('Error saving config to localStorage:', error);
            return false;
        }
    },

    /**
     * Clear configuration from localStorage
     */
    clearConfig() {
        localStorage.removeItem(this.STORAGE_KEYS.CONFIG);
    },

    /**
     * Validate configuration object
     * @param {Object} config - Configuration to validate
     * @returns {Object} Validation result {valid: boolean, errors: Array}
     */
    validateConfig(config) {
        const errors = [];

        // Required fields
        if (!config.appKey || config.appKey.trim() === '') {
            errors.push('APP_KEY is required');
        }
        if (!config.appSecret || config.appSecret.trim() === '') {
            errors.push('APP_SECRET is required');
        }
        if (!config.redirectUri || config.redirectUri.trim() === '') {
            errors.push('REDIRECT_URI is required');
        }
        if (!config.apiBaseUrl || config.apiBaseUrl.trim() === '') {
            errors.push('API Base URL is required');
        }
        if (!config.authorizationUrl || config.authorizationUrl.trim() === '') {
            errors.push('Authorization URL is required');
        }

        // URL format validation
        if (config.redirectUri && !this.isValidUrl(config.redirectUri)) {
            errors.push('REDIRECT_URI must be a valid URL');
        }
        if (config.apiBaseUrl && !this.isValidUrl(config.apiBaseUrl)) {
            errors.push('API Base URL must be a valid URL');
        }
        if (config.authorizationUrl && !this.isValidUrl(config.authorizationUrl)) {
            errors.push('Authorization URL must be a valid URL');
        }

        return {
            valid: errors.length === 0,
            errors: errors
        };
    },

    /**
     * Validate URL format
     * @param {string} url - URL to validate
     * @returns {boolean} Valid status
     */
    isValidUrl(url) {
        try {
            new URL(url);
            return true;
        } catch {
            return false;
        }
    },

    /**
     * Load token set from localStorage
     * @returns {Object|null} Token set object or null if not found
     */
    loadTokenSet() {
        try {
            const tokenStr = localStorage.getItem(this.STORAGE_KEYS.TOKENS);
            if (!tokenStr) {
                return null;
            }
            return JSON.parse(tokenStr);
        } catch (error) {
            console.error('Error loading tokens from localStorage:', error);
            return null;
        }
    },

    /**
     * Save token set to localStorage
     * @param {Object} tokenSet - Token set object to save
     */
    saveTokenSet(tokenSet) {
        try {
            // Calculate expiration timestamp
            const now = Date.now();
            const expiresAt = now + (tokenSet.expiresIn * 1000);

            const completeTokenSet = {
                accessToken: tokenSet.accessToken,
                refreshToken: tokenSet.refreshToken,
                openId: tokenSet.openId,
                expiresIn: tokenSet.expiresIn,
                tokenObtainedAt: now,
                expiresAt: expiresAt
            };

            localStorage.setItem(this.STORAGE_KEYS.TOKENS, JSON.stringify(completeTokenSet));
        } catch (error) {
            console.error('Error saving tokens to localStorage:', error);
        }
    },

    /**
     * Clear token set from localStorage
     */
    clearTokenSet() {
        localStorage.removeItem(this.STORAGE_KEYS.TOKENS);
    },

    /**
     * Check if access token is expired
     * @param {Object} tokenSet - Token set object
     * @returns {boolean} True if expired
     */
    isTokenExpired(tokenSet) {
        if (!tokenSet || !tokenSet.expiresAt) {
            return true;
        }
        return Date.now() >= tokenSet.expiresAt;
    },

    /**
     * Format expiration time for display
     * @param {Object} tokenSet - Token set object
     * @returns {string} Formatted expiration message
     */
    formatExpirationTime(tokenSet) {
        if (!tokenSet || !tokenSet.expiresAt) {
            return 'Unknown';
        }

        const now = Date.now();
        const expiresAt = tokenSet.expiresAt;

        if (now >= expiresAt) {
            return 'Expired';
        }

        const secondsRemaining = Math.floor((expiresAt - now) / 1000);
        const minutesRemaining = Math.floor(secondsRemaining / 60);
        const hoursRemaining = Math.floor(minutesRemaining / 60);

        if (hoursRemaining > 0) {
            return `Expires in ${hoursRemaining}h ${minutesRemaining % 60}m`;
        } else if (minutesRemaining > 0) {
            return `Expires in ${minutesRemaining}m ${secondsRemaining % 60}s`;
        } else {
            return `Expires in ${secondsRemaining}s`;
        }
    },

    /**
     * Clear all data from localStorage
     */
    clearAll() {
        this.clearConfig();
        this.clearTokenSet();
    }
};

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.Config = Config;
}
