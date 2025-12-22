# API Configuration

The API base URL is now centralized in `src/utils/config.js`.

## Configuration

The API URL can be configured in two ways:

1. **Environment Variable** (Recommended for production):
   Create a `.env` file in the `wug-ui` directory:

   ```
   REACT_APP_API_URL=http://your-api-server:8000
   ```

2. **Default**: If no environment variable is set, it defaults to `http://localhost:8000`

## Usage

All API calls should use the `apiCall` helper from `utils/api.js`:

```javascript
import { apiCall } from "./utils/api";

// Instead of: fetch("http://localhost:8000/endpoint")
// Use: apiCall("endpoint")
const res = await apiCall("auth/login", {
  method: "POST",
  body: formData,
});
```

The `apiCall` function automatically:

- Prepends the base URL
- Adds authentication headers
- Handles 401 errors (auto-logout)

## Changing the API URL

To change the API URL for different environments:

1. **Development**: Use `.env` file:

   ```
   REACT_APP_API_URL=http://localhost:8000
   ```

2. **Production**: Set the environment variable when building:

   ```bash
   REACT_APP_API_URL=https://api.yourdomain.com npm run build
   ```

3. **Docker/Container**: Set as environment variable in your container configuration
