const test=require('node:test'),assert=require('node:assert/strict');
const {number,escapeHTML,gate}=require('../web/app.js');
test('zero speed remains numeric; unavailable is never zero',()=>{assert.equal(number(0),'0.00');for(const v of [null,undefined,NaN,Infinity,'0'])assert.equal(number(v),'Unavailable');});
test('source names and report values cannot inject HTML',()=>{assert.equal(escapeHTML('<img src=x onerror="oops">'), '&lt;img src=x onerror=&quot;oops&quot;&gt;');});
test('later requests invalidate earlier responses and errors',()=>{const g=gate(),old=g.next(),current=g.next();assert.equal(g.current(old),false);assert.equal(g.current(current),true);g.next();assert.equal(g.current(current),false);});
