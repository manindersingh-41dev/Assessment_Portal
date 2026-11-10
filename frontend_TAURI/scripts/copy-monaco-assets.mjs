import { cpSync, existsSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

const source = resolve('node_modules/monaco-editor/min/vs');
const destination = resolve('public/vendor/monaco/vs');

if (!existsSync(resolve(source, 'loader.js'))) {
  throw new Error('Monaco assets are missing. Run npm install in the frontend directory.');
}

mkdirSync(dirname(destination), { recursive: true });
rmSync(destination, { recursive: true, force: true });
cpSync(source, destination, { recursive: true });

console.log('Copied Monaco assets for local loading.');
