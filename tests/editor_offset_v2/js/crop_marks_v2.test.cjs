const test = require('node:test');
const assert = require('node:assert/strict');
const {cropMarkDimensions} = require('../../../static/js/editor_offset_v2/geometry_view.js');
const cases = require('../../fixtures/editor_offset_v2/crop_mark_dimensions.json');
test('canvas crop marks use the same physical dimensions as native PDF', () => {
  for (const item of cases) {
    const actual = cropMarkDimensions(item.bleed);
    if (!item.dimensions) { assert.equal(actual, null); continue; }
    for (const key of ['start','end','width']) assert.ok(Math.abs(actual[key]-item.dimensions[key]) < 1e-9);
    assert.ok(actual.start > actual.width/2);
    assert.ok(actual.end + actual.width/2 <= item.bleed + 1e-9);
  }
});
