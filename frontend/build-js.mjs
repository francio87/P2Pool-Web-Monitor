import { cp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const sourceDir = path.join(projectRoot, 'frontend');
const outputDir = path.join(projectRoot, 'src', 'templates');
const cssFiles = ['components.css', 'base.css', 'themes/classic.css', 'dashboard.css', 'themes/market-dark.css', 'p2pool-monitor.css'];

await mkdir(outputDir, { recursive: true });
await cp(path.join(sourceDir, 'p2pool_web_monitor.html'), path.join(outputDir, 'p2pool_web_monitor.html'));
await cp(path.join(sourceDir, 'p2pool-monitor.js'), path.join(outputDir, 'p2pool-monitor.js'));
await rm(path.join(outputDir, 'js'), { recursive: true, force: true });
await cp(path.join(sourceDir, 'js'), path.join(outputDir, 'js'), { recursive: true });
await writeFile(path.join(outputDir, 'p2pool-monitor.css'), (await Promise.all(cssFiles.map((file) => readFile(path.join(sourceDir, file), 'utf8')))).join('\n'));
