# OAuth2 Testing Frontend

A web-based testing tool for developers to test and validate OAuth2 authorization code flow integration with the me.bot platform.

## Features

- 🔐 Complete OAuth2 authorization code flow testing
- 🔄 Token refresh mechanism validation
- 📡 Authenticated API testing with userinfo endpoint
- 💾 Configuration persistence via localStorage
- ⚠️ Comprehensive error handling with detailed debugging
- 🚫 Concurrent flow prevention
- 🔒 Security warnings for credential storage

## Quick Setup

### Prerequisites

- Modern web browser (Chrome or Safari)
- OAuth2 credentials from me.bot platform:
  - APP_KEY
  - APP_SECRET
  - REDIRECT_URI (configured in platform)
  - User Token (for Dev environment)

### Installation

**Option 1: Python HTTP Server (Recommended)**
```bash
cd oauth2-testing-tool
python3 -m http.server 8080
# Open http://localhost:8080 in browser
```

**Option 2: Node.js HTTP Server**
```bash
npm install -g http-server
cd oauth2-testing-tool
http-server -p 8080
# Open http://localhost:8080 in browser
```

**Option 3: Direct File Open**
```bash
# Open index.html directly in browser
open index.html  # macOS
# Note: May have issues with OAuth redirects
```

## Usage

1. **Configure Credentials**
   - Enter APP_KEY, APP_SECRET, REDIRECT_URI
   - Enter User Token (for Dev environment)
   - Set API Base URL (Dev: https://mindos-devusk8s.mindverse.ai)
   - Click "Save Configuration"

2. **Test Authorization Flow**
   - Click "Start Authorization"
   - Authorize on me.bot platform
   - Return with authCode
   - Click "Exchange for Token"
   - View accessToken and refreshToken

3. **Test Token Refresh**
   - Click "Refresh Token"
   - View new accessToken

4. **Test Authenticated API**
   - Click "Test User Info API"
   - View user profile information

## Security Warning

⚠️ **This tool stores credentials in plaintext browser localStorage**

- **DO NOT** use production credentials
- **DO NOT** use on shared devices
- Use test/development credentials only
- Clear localStorage after testing

## Project Structure

```
oauth2-testing-tool/
├── index.html      # Main HTML structure
├── styles.css      # Styling and layout
├── app.js          # Main application logic
├── config.js       # Configuration management
├── oauth2.js       # OAuth2 API client
├── ui.js           # UI state management
└── README.md       # This file
```

## Documentation

- [Feature Specification](../specs/001-oauth2-test-frontend/spec.md)
- [Implementation Plan](../specs/001-oauth2-test-frontend/plan.md)
- [API Contracts](../specs/001-oauth2-test-frontend/contracts/oauth2-api.md)
- [Quickstart Guide](../specs/001-oauth2-test-frontend/quickstart.md)

## Support

For issues or questions:
- Check [quickstart.md](../specs/001-oauth2-test-frontend/quickstart.md) troubleshooting section
- Contact me.bot platform team for API-related questions

## License

Development/Testing tool - not for production use
