import { cpSync, existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { delimiter, dirname, isAbsolute, join, relative, resolve, sep } from 'node:path';
import { tmpdir } from 'node:os';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const configuredSource = process.env.GEETA_GCC_BUNDLE_SOURCE?.trim();
const defaultSource = process.platform === 'win32' ? 'C:\\msys64\\ucrt64' : '';
const sourceRoot = configuredSource ? resolve(configuredSource) : defaultSource;

if (!sourceRoot) {
  throw new Error(
    'Set GEETA_GCC_BUNDLE_SOURCE to a Windows MSYS2 UCRT64 prefix. '
      + 'On Windows, the default is C:\\msys64\\ucrt64.',
  );
}

const requiredPaths = [
  'bin/gcc.exe',
  'bin/as.exe',
  'bin/ld.exe',
  'include',
  'lib',
  'lib/gcc',
];
const missingPaths = requiredPaths.filter((path) => !existsSync(join(sourceRoot, path)));
if (missingPaths.length) {
  throw new Error(
    `The GCC source at ${sourceRoot} is incomplete. Missing: ${missingPaths.join(', ')}. `
      + 'Install the MSYS2 UCRT64 GCC and binutils packages, or set GEETA_GCC_BUNDLE_SOURCE to that prefix.',
  );
}

const bundleRoot = join(projectRoot, 'resources', 'gcc', 'ucrt64');
const normalizedSource = resolve(sourceRoot).toLowerCase();
const normalizedBundle = resolve(bundleRoot).toLowerCase();
const isWithin = (parent, candidate) => {
  const relativePath = relative(parent, candidate);
  return relativePath === ''
    || (relativePath !== '..' && !relativePath.startsWith(`..${sep}`) && !isAbsolute(relativePath));
};
if (isWithin(resolve(sourceRoot), resolve(bundleRoot)) || isWithin(resolve(bundleRoot), resolve(sourceRoot))) {
  throw new Error('GEETA_GCC_BUNDLE_SOURCE cannot overlap the GCC bundle output directory.');
}

mkdirSync(dirname(bundleRoot), { recursive: true });
rmSync(bundleRoot, { recursive: true, force: true });
cpSync(sourceRoot, bundleRoot, {
  recursive: true,
  force: true,
  dereference: true,
  preserveTimestamps: true,
});

const stagedGcc = join(bundleRoot, 'bin', 'gcc.exe');
if (!existsSync(stagedGcc)) {
  throw new Error(`GCC staging did not produce ${stagedGcc}.`);
}

if (process.platform === 'win32') {
  const systemRoot = process.env.SystemRoot || 'C:\\Windows';
  const environment = {
    ...process.env,
    PATH: [join(bundleRoot, 'bin'), join(systemRoot, 'System32'), systemRoot].join(delimiter),
  };
  const versionCheck = spawnSync(stagedGcc, ['--version'], {
    encoding: 'utf8',
    env: environment,
    timeout: 30_000,
  });
  if (versionCheck.error || versionCheck.status !== 0) {
    throw new Error(
      `The staged GCC could not start: ${versionCheck.error?.message || versionCheck.stderr || 'unknown error'}`,
    );
  }

  for (const [argument, description] of [
    ['-print-file-name=include', 'compiler headers'],
    ['-print-file-name=libgcc.a', 'GCC runtime library'],
    ['-print-prog-name=cc1', 'GCC C frontend'],
  ]) {
    const probe = spawnSync(stagedGcc, [argument], {
      encoding: 'utf8',
      env: environment,
      timeout: 30_000,
    });
    const reportedPath = probe.stdout?.trim();
    if (probe.error || probe.status !== 0 || !reportedPath) {
      throw new Error(`Could not locate bundled ${description} with the staged GCC.`);
    }
    if (isAbsolute(reportedPath)) {
      const normalizedReportedPath = resolve(reportedPath).toLowerCase();
      if (!normalizedReportedPath.startsWith(`${normalizedBundle}${sep.toLowerCase()}`)) {
        throw new Error(`The staged GCC resolves ${description} outside its bundle: ${reportedPath}`);
      }
    }
  }

  const smokeDirectory = mkdtempSync(join(tmpdir(), 'geeta-gcc-bundle-check-'));
  try {
    const sourceFile = join(smokeDirectory, 'bundle-check.c');
    const executableFile = join(smokeDirectory, 'bundle-check.exe');
    writeFileSync(sourceFile, '#include <stdio.h>\nint main(void) { puts("bundled-gcc-ok"); return 0; }\n');
    const compileCheck = spawnSync(stagedGcc, [
      '-std=c11', sourceFile, '-o', executableFile,
    ], { encoding: 'utf8', env: environment, timeout: 60_000 });
    if (compileCheck.error || compileCheck.status !== 0) {
      throw new Error(
        `The staged GCC could not compile a C smoke test: ${compileCheck.error?.message || compileCheck.stderr || 'unknown error'}`,
      );
    }

    const runCheck = spawnSync(executableFile, [], {
      encoding: 'utf8',
      env: environment,
      timeout: 10_000,
    });
    if (runCheck.error || runCheck.status !== 0 || !runCheck.stdout.includes('bundled-gcc-ok')) {
      throw new Error(
        `The staged compiler output could not run with its bundled runtime: ${runCheck.error?.message || runCheck.stderr || 'unexpected output'}`,
      );
    }
  } finally {
    rmSync(smokeDirectory, { recursive: true, force: true });
  }
}

console.log(`Staged Windows GCC from ${sourceRoot} into resources/gcc/ucrt64.`);
