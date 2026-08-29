import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));
const read = name => fs.readFileSync(path.join(root, name), 'utf8');
const story = JSON.parse(read('story.json'));
const timing = JSON.parse(read('timing.json'));
if (!Number.isFinite(timing.duration) || timing.duration < 60 || timing.duration > 240) {
  throw new Error('Expected actual synthesized audio timing for a 1–4 minute film.');
}
if (timing.scenes.length !== story.scenes.length || timing.lines.length !== 16) {
  throw new Error('Audio timing does not cover the complete story.');
}
if (!fs.existsSync(path.join(root, 'audio/dialogue.wav'))) throw new Error('Dialogue audio is missing.');

const context = {window: {}};
vm.runInNewContext(read('characters.js'), context, {timeout: 1000});
// Keep the editable SVG rigs in characters.js; compact repeated instances in the export.
const character = (kind, prefix) => context.window.TWRPCharacters.render(kind, prefix).replace(/>\s+</g, '><');
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
const icon = (kind, cls = '') => {
  const paths = {
    check: '<path d="m6 16 6 6L27 7"/>',
    document: '<path d="M8 3h12l7 7v20H8z"/><path d="M20 3v8h7M13 17h9M13 22h9"/>',
    bolt: '<path d="m18 2-13 17h10l-1 12 14-18H18z"/>',
    terminal: '<rect x="3" y="5" width="28" height="24" rx="4"/><path d="m8 12 5 5-5 5M17 22h7"/>',
    lock: '<rect x="6" y="14" width="22" height="17" rx="4"/><path d="M11 14V9a6 6 0 0 1 12 0v5M17 21v4"/>',
    speaker: '<path d="M4 13h7l9-8v24l-9-8H4zM25 11q8 6 0 12"/>',
    arrow: '<path d="M3 17h27M21 7l10 10-10 10"/>',
    tools: '<path d="m20 4 4 5 6-1a10 10 0 0 1-12 12L8 30l-5-5 10-11A10 10 0 0 1 20 4z"/>'
  };
  return `<svg class="icon ${cls}" viewBox="0 0 34 34" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[kind] || paths.document}</svg>`;
};

const diagrams = {
  workshop: `
    <div class="diagram-top mono">THE TESTING WORKSHOP</div>
    <div class="workshop-flow">
      <div class="old-cycle detail"><div class="file-stack">${icon('document')}<span>image.img</span></div><strong>Flash. Reboot.</strong><span class="old-repeat">Again. And again.</span></div>
      <div class="flow-arrow detail">${icon('arrow')}</div>
      <div class="recovery-workshop detail"><div class="workshop-logo">TWRP</div><div class="workshop-tools"><span>${icon('tools')} Test</span><span>${icon('terminal')} Logs</span></div><div class="workshop-dots"><i></i><i></i><i></i></div></div>
    </div>
    <div class="diagram-note detail">A recovery environment we can work in.</div>`,
  'black-screen': `
    <div class="diagram-top mono">NOT EVERY ATTEMPT IS A BREAKTHROUGH</div>
    <div class="attempts">
      <div class="attempt-card detail"><span class="attempt-number mono">01</span><strong>Image rejected</strong><span class="result-x">×</span></div>
      <div class="attempt-card detail"><span class="attempt-number mono">02</span><strong>Back to Android</strong><span class="result-return">↩</span></div>
      <div class="attempt-card dark-card detail"><span class="attempt-number mono">03</span><strong>Black screen</strong><div class="sleeping-display"><i></i><i></i></div></div>
    </div>
    <div class="unknown-note detail"><span class="question">?</span> Investigated. Not every cause isolated.</div>`,
  'working-image': `
    <div class="diagram-top mono">THE USER-SUPPLIED BREAKTHROUGH</div>
    <div class="baseline-reveal">
      <div class="source-image detail">${icon('document')}<strong>touchfix18.img</strong><span>Working recovery</span></div>
      <div class="flow-arrow detail">${icon('arrow')}</div>
      <div class="mini-recovery detail"><span class="mini-camera"></span><strong>TWRP</strong><div class="mini-buttons"><span>TOOLS</span><span>LOGS</span><span>FILES</span><span>REBOOT</span></div><span class="screen-check">${icon('check')}</span></div>
    </div>
    <div class="credit detail">Built on antocorvo3000’s supplied recovery.</div>`,
  'slow-touch': `
    <div class="diagram-top mono">THE UI IS HERE. THE RESPONSE ISN’T.</div>
    <div class="lag-layout"><div class="lag-number detail"><strong>5–10</strong><span>seconds per tap</span></div><div class="clock detail"><span class="clock-hand"></span><i></i></div></div>
    <div class="mode-strip detail"><span>RECOVERY SELINUX</span><strong>Permissive</strong><span class="small-check">${icon('check')} Some improvement</span></div>
    <div class="diagram-note detail">Android unchanged · Denial logs retained</div>`,
  'no-buzz': `
    <div class="diagram-top mono">THREE VIBRATION SETTINGS</div>
    <div class="vibration-controls">${['Action', 'Button', 'Keyboard'].map((name, i) => `<div class="vibration-row detail" id="buzz-${i}"><span>${name}</span><div class="slider-track"><div class="slider-fill"></div><i class="slider-knob"></i></div><strong class="mono">0</strong></div>`).join('')}</div>
    <div class="user-quote detail"><span class="quote-mark">“</span><strong>oh yea way faster</strong><span class="quote-source mono">USER FEEDBACK</span></div>
    <div class="diagram-note detail">Faster feel confirmed. No speed multiplier claimed.</div>`,
  'two-files': `
    <div class="diagram-top mono">A SMALL PATCH TO A WORKING BASE</div>
    <div class="config-files"><div class="config-file detail">${icon('document')}<strong>init.rc</strong><span>Recovery permissive</span></div><div class="plus detail">+</div><div class="config-file detail">${icon('document')}<strong>twres/ui.xml</strong><span>Vibration defaults: 0</span></div></div>
    <div class="preserved-core detail">${icon('lock')}<div><strong>WORKING CORE PRESERVED</strong><span>Executable · Libraries · Drivers · Firmware</span></div></div>
    <div class="diagram-note detail">Adapted prebuilt · Repacked + development-signed</div>`,
  proof: `
    <div class="diagram-top mono">THE ACTUAL INSTALL + BOOT CHECKS</div>
    <div class="partition-row"><div class="backup-stack detail">${icon('document')}<strong>Original + stock</strong><span>Recovery images kept</span></div><div class="flow-arrow detail">${icon('arrow')}</div><div class="partition-target detail"><span class="mono">FLASH TARGET</span><strong>recovery_a</strong><span>No wipe</span></div></div>
    <div class="proof-checks">${['Root ADB', 'Recovery + kernel logs', 'Image hash matches', 'Defaults active at boot'].map((label, i) => `<div class="proof-check detail" id="proof-${i}">${icon('check')}<span>${label}</span></div>`).join('')}</div>`,
  baseline: `
    <div class="diagram-top mono">THE MILESTONE, WITH THE LIMITS IN VIEW</div>
    <div class="success-stamp detail">${icon('check')}<div><strong>working76</strong><span>UI · Responsive touch · Root ADB · Logs</span></div></div>
    <div class="test-count detail"><strong>2,475</strong><div><span>offline tests passed</span><small>Workspace tooling, not full hardware certification.</small></div></div>
    <div class="next-chapter detail"><span class="mono">STILL AHEAD</span><div><span>Data decryption</span><span>SELinux enforcement</span><span>Magisk</span></div></div>
    <div class="diagram-note detail">A working recovery. The ROM is still ahead.</div>`
};

function makeScene(scene, index) {
  const sceneTime = timing.scenes.find(item => item.id === scene.id);
  if (!sceneTime) throw new Error(`Missing audio scene: ${scene.id}`);
  return `<section class="scene" id="scene-${scene.id}" style="z-index:${index + 1};opacity:${index ? 0 : 1}" aria-label="${esc(scene.title)}">
    <div class="workshop-decoration" data-layout-ignore="true"><div class="hanging-lamp"><i></i><b></b></div><div class="wall-lines"></div><div class="desk-line"></div><div class="ambient-orbit"></div></div>
    <div class="scene-content">
      <div class="masthead"><span class="brand mono" data-layout-allow-overlap>TWRP FIELD NOTES</span><span class="illustration-label mono" data-layout-allow-overlap>ANIMATED RECAP · XIAOMI 17 ULTRA</span></div>
      <header class="scene-heading"><div class="eyebrow mono" data-layout-allow-overlap>${esc(scene.eyebrow)}</div><h1 data-layout-allow-overlap>${esc(index === 0 ? story.title : scene.title)}</h1></header>
      <div class="stage">
        <div class="actor actor-nezha" id="${scene.id}-nezha"><div class="actor-art">${character('nezha', `${scene.id}-nezha`)}</div><div class="actor-label"><strong data-layout-allow-overlap>NEZHA</strong><span data-layout-allow-overlap>The phone</span></div></div>
        <div class="diagram-panel" id="panel-${scene.id}">${diagrams[scene.id]}</div>
        <div class="actor actor-patch" id="${scene.id}-patch"><div class="actor-art">${character('patch', `${scene.id}-patch`)}</div><div class="actor-label"><strong data-layout-allow-overlap>PATCH</strong><span data-layout-allow-overlap>The engineer</span></div></div>
      </div>
      <div class="scene-callout mono">${esc(scene.callout)}</div>
    </div>
  </section>`;
}

const scenes = story.scenes.map(makeScene).join('\n');
const captions = timing.captions.map((caption, index) => `<div class="caption-group" id="caption-${index}"><span class="caption-speaker ${esc(caption.speaker)}">${esc(story.characters[caption.speaker].name)}</span><p>${esc(caption.text)}</p></div>`).join('\n');

const fonts = [
  ['Bricolage Grotesque', 400, '@fontsource/bricolage-grotesque/files/bricolage-grotesque-latin-400-normal.woff2'],
  ['Bricolage Grotesque', 800, '@fontsource/bricolage-grotesque/files/bricolage-grotesque-latin-800-normal.woff2'],
  ['IBM Plex Mono', 400, '@fontsource/ibm-plex-mono/files/ibm-plex-mono-latin-400-normal.woff2'],
  ['IBM Plex Mono', 600, '@fontsource/ibm-plex-mono/files/ibm-plex-mono-latin-600-normal.woff2']
].map(([family, weight, filename]) => `@font-face{font-family:"${family}";font-style:normal;font-weight:${weight};font-display:block;src:url(data:font/woff2;base64,${fs.readFileSync(path.join(root, 'node_modules', filename)).toString('base64')}) format('woff2');}`).join('\n');
const jsonScript = value => JSON.stringify(value).replace(/</g, '\\u003c');
const html = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=1920, initial-scale=1"><title>${esc(story.title)}</title>
<style>${fonts}\n${read('styles.css')}</style><script src="node_modules/gsap/dist/gsap.min.js"></script></head>
<body><main id="twrp-story" data-composition-id="twrp-story" data-start="0" data-duration="${timing.duration.toFixed(4)}" data-width="1920" data-height="1080">
${scenes}
<div class="caption-rail">${captions}</div>
<div class="film-progress" data-layout-ignore="true"><div id="film-progress-fill"></div></div>
<audio id="dialogue" data-start="0" data-duration="${timing.duration.toFixed(4)}" data-track-index="1" data-volume="1" src="audio/dialogue.wav"></audio>
</main><script>window.TWRP_STORY=${jsonScript(story)};window.TWRP_TIMING=${jsonScript(timing)};</script><script>${read('motion.js')}</script></body></html>`;
const exported = html.replace(/\n\s*\n/g, '\n');
fs.writeFileSync(path.join(root, 'index.html'), exported);
console.log(JSON.stringify({output:'index.html',duration:timing.duration,scenes:story.scenes.length,lines:timing.lines.length,captions:timing.captions.length,bytes:Buffer.byteLength(exported)}, null, 2));
