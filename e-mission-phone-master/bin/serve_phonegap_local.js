#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

const binName = process.platform === 'win32' ? 'phonegap.cmd' : 'phonegap';
const binPath = path.join(__dirname, '..', 'node_modules', '.bin', binName);
const projectRoot = path.join(__dirname, '..');

const child = spawn(`"${binPath}" --verbose serve`, {
  cwd: projectRoot,
  env: {
    ...process.env,
    CI: 'true',
    LOCALAPPDATA: path.join(projectRoot, '.localappdata'),
    XDG_CONFIG_HOME: path.join(projectRoot, '.config'),
  },
  stdio: 'inherit',
  shell: true,
});

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
  }
  process.exit(code ?? 0);
});
