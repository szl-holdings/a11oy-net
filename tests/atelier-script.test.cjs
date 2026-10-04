/* SPDX-License-Identifier: Apache-2.0 */
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const filename = path.join(__dirname, '../atelier/app.js');
const source = fs.readFileSync(filename, 'utf8');

function loadRenderer() {
  // Keep this unit test offline: define functions without starting browser boot.
  const entrypoint = /\nboot\(\);\s*$/;
  assert.match(source, entrypoint, 'Review the test harness if the boot entrypoint changes');
  const context = vm.createContext(Object.create(null));
  new vm.Script(source.replace(entrypoint, '\n'), { filename })
    .runInContext(context, { timeout: 1000 });
  assert.equal(typeof context.pythonOf, 'function');
  return context.pythonOf;
}

test('the complete shipped Atelier script parses as JavaScript', () => {
  assert.doesNotThrow(() => new vm.Script(source, { filename }));
});

test('full weights and adapters retain the configured base model', () => {
  const render = loadRenderer();
  for (const weights of ['full', 'adapter']) {
    const result = render({ weights, base: 'example/exact-base' });
    assert.ok(result.includes('# base = example/exact-base'));
    assert.equal(result.includes('# base = Qwen/Qwen2.5-1.5B-Instruct'), false);
  }
});

test('full weights and adapters use the fallback for absent or empty bases', () => {
  const render = loadRenderer();
  for (const weights of ['full', 'adapter']) {
    for (const base of [undefined, null, '']) {
      const result = render({ weights, base });
      assert.ok(result.includes('# base = Qwen/Qwen2.5-1.5B-Instruct'));
    }
  }
});
