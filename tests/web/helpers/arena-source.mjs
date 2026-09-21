import { readFileSync } from 'node:fs';
import { withoutModuleSyntax } from './dashboard-source.mjs';

const modules = [
  'arena-model.js',
  'arena-elements.js',
  'arena-navigation.js',
  'arena-task-detail.js',
  'arena-participant-detail.js',
  'arena-lists.js',
  'arena-render.js',
  'arena-loader.js',
  'arena.js',
];
export function arenaSource() {
  return modules.map(name => {
    const source = readFileSync(new URL('../../../web/' + name, import.meta.url), 'utf8');
    return withoutModuleSyntax(source.replace(/^export \{[^}]*\} from [^;]+;\s*/gm, ''));
  }).join('\n\n');
}
