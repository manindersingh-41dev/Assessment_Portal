import { loadEnv } from 'vite';

const productionEnv = loadEnv('production', process.cwd(), 'VITE_');
const apiBaseUrl = process.env.VITE_API_URL || productionEnv.VITE_API_URL;

if (!apiBaseUrl) {
  throw new Error('Set VITE_API_URL to the deployed HTTPS API in .env.production or the build environment before packaging.');
}

let parsedApiUrl;
try {
  parsedApiUrl = new URL(apiBaseUrl);
} catch {
  throw new Error('VITE_API_URL must be an absolute HTTPS URL, for example https://api.example.edu/api.');
}

if (parsedApiUrl.protocol !== 'https:' || parsedApiUrl.username || parsedApiUrl.password
  || parsedApiUrl.search || parsedApiUrl.hash) {
  throw new Error('Desktop release builds require an HTTPS VITE_API_URL without embedded credentials.');
}

console.log(`Desktop release API: ${parsedApiUrl.origin}`);
