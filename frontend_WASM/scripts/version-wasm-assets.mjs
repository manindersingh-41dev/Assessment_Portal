import { createHash } from 'node:crypto';
import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync } from 'node:fs';
import { join, relative, resolve, sep } from 'node:path';

const sourceDirectory = resolve('.wasm-assets');
const publicDirectory = resolve('public/clang');
const manifestPath = join(sourceDirectory, 'runtime-manifest.v1.json');

if (!existsSync(manifestPath)) {
  throw new Error('Clang runtime manifest was not generated in .wasm-assets.');
}

const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
if (manifest.manifestVersion !== 1 || typeof manifest.version !== 'string') {
  throw new Error('Generated Clang runtime manifest has an unsupported format.');
}

const hash = createHash('sha256');
const addDirectoryToHash = (directory) => {
  for (const name of readdirSync(directory).sort()) {
    const absolutePath = join(directory, name);
    const relativePath = relative(sourceDirectory, absolutePath).split(sep).join('/');
    if (statSync(absolutePath).isDirectory()) {
      hash.update(`directory\0${relativePath}\0`);
      addDirectoryToHash(absolutePath);
    } else {
      hash.update(`file\0${relativePath}\0`);
      hash.update(readFileSync(absolutePath));
      hash.update('\0');
    }
  }
};

addDirectoryToHash(sourceDirectory);
const version = `runtime-${hash.digest('hex').slice(0, 20)}`;

try {
  rmSync(publicDirectory, { recursive: true, force: true });
  mkdirSync(publicDirectory, { recursive: true });
  cpSync(sourceDirectory, join(publicDirectory, version), { recursive: true });
  console.log(`Copied Clang runtime assets to public/clang/${version}/`);
} finally {
  rmSync(sourceDirectory, { recursive: true, force: true });
}
