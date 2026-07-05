/* Extracts the speech manifest from index.html using the app's own logic.
   Usage: node extract_manifest.js   → writes speech_manifest.json */
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
const m = html.match(/<script>([\s\S]*)<\/script>/);
if(!m) throw new Error('script not found');

/* minimal DOM/browser stubs so the app script can evaluate */
function el(){
  const e = {
    style:{}, dataset:{}, classList:{add(){},remove(){},contains(){return false;}},
    children:[], textContent:'', innerHTML:'', value:'', disabled:false,
    appendChild(c){ this.children.push(c); }, setAttribute(){}, getContext(){ return ctx(); },
    addEventListener(){}, removeEventListener(){}, focus(){}, click(){},
    querySelector(){ return el(); }, querySelectorAll(){ return []; },
    getBoundingClientRect(){ return {left:0,top:0,width:300,height:300}; },
    setPointerCapture(){},
  };
  return e;
}
function ctx(){ return {fillText(){},clearRect(){},beginPath(){},moveTo(){},lineTo(){},stroke(){},getImageData(){return {data:new Uint8ClampedArray(4)};},strokeText(){}}; }

const sandbox = {
  document: {
    getElementById(){ return el(); }, createElement(){ return el(); },
    querySelector(){ return el(); }, querySelectorAll(){ return []; },
    body: el(),
  },
  window: {}, localStorage: { getItem(){return null;}, setItem(){}, removeItem(){} },
  navigator: {}, console,
  confirm(){ return false; }, alert(){},
  setTimeout(fn){ return 0; }, clearInterval(){}, setInterval(){ return 0; },
  Audio: function(){ return {play(){return {catch(){}};},pause(){}}; },
  SpeechSynthesisUtterance: function(){},
  speechSynthesis: { getVoices(){return [];}, cancel(){}, speak(){}, onvoiceschanged:null },
  Math, JSON, Object, Array, String, Number, RegExp, Map, Set, Uint8ClampedArray,
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;

const vm = require('vm');
vm.createContext(sandbox);
const contentDir = path.join(__dirname, 'content');
if (fs.existsSync(contentDir)) {
  fs.readdirSync(contentDir).filter(f => f.endsWith('.js')).sort().forEach(f => {
    vm.runInContext(fs.readFileSync(path.join(contentDir, f), 'utf8'), sandbox);
  });
}
vm.runInContext(m[1], sandbox);

const manifest = sandbox.exportSpeechManifest();
fs.writeFileSync(path.join(__dirname, 'speech_manifest.json'), manifest, 'utf8');
const items = JSON.parse(manifest);
console.log('wrote speech_manifest.json —', items.length, 'clips,',
  items.reduce((a,x)=>a+x.text.length,0), 'chars');
