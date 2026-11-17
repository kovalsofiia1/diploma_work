import { execFileSync } from 'node:child_process';
import { delimiter, resolve } from 'node:path';

export default function globalSetup(): void {
  const backendDirectory = resolve(__dirname, '..', '..', 'backend');
  const seedScript = resolve(backendDirectory, 'tests', 'seed_admin_e2e.py');
  execFileSync(process.env.PYTHON || 'python', [seedScript], {
    cwd: backendDirectory,
    env: {
      ...process.env,
      PYTHONPATH: [backendDirectory, process.env.PYTHONPATH].filter(Boolean).join(delimiter),
    },
    stdio: 'inherit',
  });
}
