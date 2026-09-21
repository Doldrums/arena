import { readFileSync } from 'node:fs';

// DOM fixtures evaluate the same modules together after installing their widget stubs.
// Browser execution continues to use native ES modules and their explicit imports.
const modules = [
  'dashboard-state.js',
  'dashboard-controller.js',
  'dashboard-stream.js',
  'dashboard-metrics.js',
  'dashboard-summary.js',
  'dashboard-runtime.js',
  'dashboard-benchmark.js',
  'dashboard-architecture.js',
  'dashboard-activity.js',
  'dashboard-chart.js',
  'dashboard-tabs.js',
  'dashboard-records.js',
  'dashboard-population.js',
  'dashboard-source.js',
];
const defaultAssets = new URL('../../../web/', import.meta.url);

export function withoutModuleSyntax(source) {
  return source.replace(/^import\s[\s\S]*?;\s*/gm, '').replace(/^export /gm, '');
}

export function dashboardSource({ assets = defaultAssets, bootstrap = true } = {}) {
  const read = name => readFileSync(
    assets instanceof URL ? new URL(name, assets) : assets + name, 'utf8',
  );
  const names = bootstrap ? [...modules, 'app.js'] : modules;
  return names.map(name => withoutModuleSyntax(read(name))).join('\n\n');
}

export function dashboardFunction(name, module) {
  const source = withoutModuleSyntax(readFileSync(new URL(module, defaultAssets), 'utf8'));
  const start = source.indexOf(`function ${name}(`);
  const next = source.indexOf('\nfunction ', start + 1);
  if (start < 0) throw new Error(`Missing dashboard function: ${name}`);
  return source.slice(start, next < 0 ? source.length : next);
}
