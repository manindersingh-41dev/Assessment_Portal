const EXTENSION_SIGNATURES = [
  {
    name: 'Grammarly',
    selectors: [
      '[data-gr-ext-installed]',
      '[data-new-gr-c-s-check-loaded]',
      '[data-grammarly-shadow-root]',
      'grammarly-desktop-integration',
      '[id*="grammarly" i]',
      '[class*="grammarly" i]',
    ],
  },
  {
    name: 'LanguageTool',
    selectors: [
      '[data-lt-installed]',
      'lt-toolbar',
      'lt-div',
      '[id*="languagetool" i]',
      '[class*="languagetool" i]',
    ],
  },
  {
    name: 'QuillBot',
    selectors: [
      '[id*="quillbot" i]',
      '[class*="quillbot" i]',
      '[data-quillbot]',
      '[id*="qb-inline" i]',
      '[class*="qb-inline" i]',
    ],
  },
  ...[
    ['Wordtune', 'wordtune'],
    ['Sider', 'sider'],
    ['Monica', 'monica'],
    ['Merlin', 'merlin'],
    ['HARPA AI', 'harpa'],
    ['MaxAI', 'maxai'],
    ['AI Blaze', 'aiblaze'],
    ['Copilot', 'copilot'],
    ['ChatGPT assistant', 'chatgpt'],
    ['Gemini assistant', 'gemini'],
    ['Claude assistant', 'claude'],
    ['Perplexity assistant', 'perplexity'],
  ].map(([name, marker]) => ({
    name,
    selectors: [
      `[id*="${marker}" i]`,
      `[class*="${marker}" i]`,
      `[data-${marker}]`,
    ],
  })),
];

export const EXTENSION_MARKER_ATTRIBUTES = [
  'id',
  'class',
  'src',
  'href',
  'type',
  'data-gr-ext-installed',
  'data-new-gr-c-s-check-loaded',
  'data-grammarly-shadow-root',
  'data-lt-installed',
  'data-quillbot',
  'data-wordtune',
  'data-sider',
  'data-monica',
  'data-merlin',
  'data-harpa',
  'data-maxai',
  'data-aiblaze',
  'data-copilot',
  'data-chatgpt',
  'data-gemini',
  'data-claude',
  'data-perplexity',
];

const BROWSER_EXTENSION_SCRIPT_PROTOCOLS = new Set([
  'chrome-extension:',
  'moz-extension:',
  'safari-web-extension:',
  'ms-browser-extension:',
  'edge-extension:',
]);

const hasBrowserExtensionScript = (root) => (
  Array.from(root.querySelectorAll('script[src]')).some((script) => {
    const source = script.getAttribute('src');
    try {
      const scriptUrl = new URL(source, root.location?.href || window.location.href);
      return BROWSER_EXTENSION_SCRIPT_PROTOCOLS.has(scriptUrl.protocol);
    } catch {
      return false;
    }
  })
);

export const detectKnownBrowserExtensions = (root = document) => {
  const detected = EXTENSION_SIGNATURES
    .filter(({ selectors }) => selectors.some((selector) => root.querySelector(selector)))
    .map(({ name }) => name);

  if (hasBrowserExtensionScript(root)) detected.push('Browser extension script');
  return detected;
};
