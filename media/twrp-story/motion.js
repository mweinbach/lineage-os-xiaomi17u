(() => {
  const story = window.TWRP_STORY;
  const timing = window.TWRP_TIMING;
  const tl = gsap.timeline({paused:true});
  const query = selector => Array.from(document.querySelectorAll(selector));
  const sceneForTime = time => timing.scenes.find(scene => time >= scene.start - 0.001 && time < scene.end + 0.001);
  const actorFor = (sceneId, speaker) => `#${sceneId}-${speaker}`;

  // GSAP's SVG matrix uses view-box coordinates. A fill-box origin would apply
  // a second offset and send a scaled mouth/eye away from its original center.
  query('.char-mouth-open, .char-eyes').forEach(part => {
    part.style.transformBox = 'view-box';
    const box = part.getBBox();
    gsap.set(part, {svgOrigin:`${box.x + box.width / 2} ${box.y + box.height / 2}`,x:0,y:0,scaleY:part.classList.contains('char-mouth-open') ? 0.15 : 1});
  });
  tl.fromTo('#film-progress-fill', {scaleX:0}, {scaleX:1, duration:timing.duration, ease:'none'}, 0);

  story.scenes.forEach((scene, index) => {
    const clock = timing.scenes.find(item => item.id === scene.id);
    const selector = `#scene-${scene.id}`;
    const start = index === 0 ? 0.15 : clock.start - 0.26;
    const enter = index === 0 ? 0.22 : clock.start - 0.04;
    const duration = clock.end - clock.start;
    if (index > 0) {
      const old = `#scene-${story.scenes[index - 1].id}`;
      tl.set(selector, {opacity:1}, start);
      if (scene.id === 'working-image' || scene.id === 'baseline') {
        tl.fromTo(selector, {clipPath:'circle(0% at 50% 55%)'}, {clipPath:'circle(80% at 50% 55%)',duration:0.52,ease:'power2.out'}, start);
      } else {
        tl.fromTo(selector, {clipPath:'inset(0% 100% 0% 0%)'}, {clipPath:'inset(0% 0% 0% 0%)',duration:0.46,ease:'power3.inOut'}, start);
      }
      tl.set(old, {opacity:0}, start + 0.53);
      tl.set(selector, {clipPath:'none'}, start + 0.54);
    }
    tl.from(`${selector} .masthead`, {y:-8,opacity:0,duration:0.46,ease:'sine.out'}, enter);
    tl.from(`${selector} .eyebrow`, {x:-25,opacity:0,duration:0.42,ease:'power2.out'}, enter + 0.06);
    tl.from(`${selector} h1`, {y:25,opacity:0,duration:0.65,ease:'expo.out'}, enter + 0.10);
    tl.from(`${selector} .diagram-panel`, {scale:0.955,rotation:index % 2 ? 1.2 : -1.2,opacity:0,duration:0.63,ease:'back.out(1.25)'}, enter + 0.18);
    tl.from(`${selector} .diagram-top`, {y:-10,opacity:0,duration:0.45,ease:'power3.out'}, enter + 0.30);
    tl.from(`${selector} .actor-nezha`, {x:-58,rotation:-6,opacity:0,duration:0.69,ease:'back.out(1.45)'}, enter + 0.15);
    tl.from(`${selector} .actor-patch`, {x:58,rotation:5,opacity:0,duration:0.78,ease:'power4.out'}, enter + 0.22);
    tl.from(`${selector} .scene-callout`, {y:12,opacity:0,duration:0.54,ease:'sine.out'}, enter + 0.52);
    query(`${selector} .detail`).forEach((node, item) => {
      tl.from(node, {y:item % 2 ? -12 : 15,opacity:0,scale:item % 3 === 0 ? 0.94 : 1,duration:0.42 + item % 3 * 0.07,ease:['power2.out','back.out(1.3)','expo.out'][item % 3]}, enter + 0.35 + item * 0.055);
    });
    ['nezha','patch'].forEach((speaker, actorIndex) => {
      const actor = actorFor(scene.id, speaker);
      const cycles = Math.max(1, Math.floor((duration - 1.6) / 2.0));
      tl.to(`${actor} .char-body`, {y:actorIndex ? -4 : -6,duration:1.0,repeat:cycles * 2 - 1,yoyo:true,ease:'sine.inOut'}, clock.start + 0.8);
      for (let blink = clock.start + 2.5 + actorIndex * 1.3; blink < clock.end - 0.5; blink += 4.1 + actorIndex * 0.7) {
        tl.to(`${actor} .char-eyes`, {scaleY:0.09,duration:0.075,ease:'power1.in'}, blink);
        tl.to(`${actor} .char-eyes`, {scaleY:1,duration:0.13,ease:'power2.out'}, blink + 0.08);
      }
    });
    tl.to(`${selector} .hanging-lamp`, {rotation:1.3,duration:duration - 0.9,transformOrigin:'50% 0%',ease:'sine.inOut'}, clock.start + 0.5);
    tl.to(`${selector} .ambient-orbit`, {x:12,y:-9,rotation:8,duration:duration - 0.8,ease:'sine.inOut'}, clock.start + 0.4);

    if (scene.id === 'workshop') {
      tl.to(`${selector} .file-stack`, {rotation:3,duration:1.1,repeat:3,yoyo:true,ease:'sine.inOut'}, clock.start + 1.0);
      tl.from(`${selector} .workshop-dots i`, {scale:0.4,opacity:0.3,duration:0.5,stagger:0.12,ease:'back.out(2)'}, clock.start + 6.0);
    }
    if (scene.id === 'black-screen') {
      tl.from(`${selector} .question`, {scale:0.1,rotation:-25,duration:0.65,ease:'elastic.out(1,0.6)'}, clock.start + 6.0);
    }
    if (scene.id === 'working-image') {
      tl.from(`${selector} .screen-check`, {scale:0,rotation:-25,duration:0.7,ease:'back.out(2)'}, clock.start + 2.2);
    }
    if (scene.id === 'slow-touch') {
      tl.to(`${selector} .clock-hand`, {rotation:720,duration:9,ease:'none'}, clock.start + 0.8);
      tl.from(`${selector} .mode-strip`, {scaleX:0.85,duration:0.6,ease:'back.out(1.8)'}, clock.start + 7.5);
    }
    if (scene.id === 'no-buzz') {
      for (let item = 0; item < 3; item++) {
        const at = clock.start + 3.0 + item * 0.38;
        tl.fromTo(`#buzz-${item} .slider-fill`, {scaleX:0.85}, {scaleX:0,duration:0.65,ease:'power3.inOut'}, at);
        tl.fromTo(`#buzz-${item} .slider-knob`, {x:282}, {x:0,duration:0.65,ease:'back.out(1.05)'}, at);
      }
      tl.from(`${selector} .user-quote`, {scale:0.94,rotation:-1,duration:0.6,ease:'back.out(1.5)'}, clock.start + 8.4);
    }
    if (scene.id === 'two-files') {
      tl.from(`${selector} .preserved-core .icon`, {scale:0.3,rotation:-18,duration:0.65,ease:'back.out(2)'}, clock.start + 6.8);
    }
    if (scene.id === 'proof') {
      query(`${selector} .proof-check`).forEach((node, item) => {
        tl.from(node.querySelector('.icon'), {scale:0,duration:0.42,ease:'back.out(2)'}, clock.start + 8 + item * 1.45);
      });
    }
    if (scene.id === 'baseline') {
      tl.from(`${selector} .test-count strong`, {scale:0.78,rotation:-3,duration:0.8,ease:'elastic.out(1,0.65)'}, clock.start + 5.8);
      tl.from(`${selector} .next-chapter`, {y:8,duration:0.6,ease:'power2.out'}, clock.start + 10.5);
    }
  });

  timing.lines.forEach((line, index) => {
    const actor = actorFor(line.sceneId, line.speaker);
    const other = actorFor(line.sceneId, line.speaker === 'nezha' ? 'patch' : 'nezha');
    const span = line.end - line.start;
    const gesture = `${actor} .char-arm-${index % 2 ? 'right' : 'left'}`;
    tl.to(gesture, {rotation:index % 2 ? -18 : 15,duration:0.35,ease:'power2.out'}, line.start + 0.1);
    tl.to(gesture, {rotation:0,duration:0.4,ease:'sine.inOut'}, line.start + Math.min(2.1, span - 0.6));
    tl.to(`${other} .char-head`, {rotation:index % 2 ? -2 : 2,duration:0.4,ease:'sine.inOut'}, line.start + 0.15);
    tl.to(`${other} .char-head`, {rotation:0,duration:0.4,ease:'sine.inOut'}, Math.max(line.start + 0.7, line.end - 0.5));
    tl.set(`${actor} .char-mouth-open`, {opacity:0,scaleY:0.12}, line.end);
    tl.set(`${actor} .char-mouth-closed`, {opacity:1}, line.end);
  });

  timing.mouth.forEach(sample => {
    const scene = sceneForTime(sample.time);
    if (!scene) return;
    const actor = actorFor(scene.id, sample.speaker);
    const value = Math.max(0, Math.min(1, sample.value));
    const speaking = value > 0.07;
    tl.to(`${actor} .char-mouth-open`, {opacity:speaking ? 1 : 0,scaleY:0.15 + value * 0.93,duration:0.045,ease:'none'}, sample.time);
    tl.set(`${actor} .char-mouth-closed`, {opacity:speaking ? 0 : 1}, sample.time);
  });

  timing.captions.forEach((caption, index) => {
    const selector = `#caption-${index}`;
    tl.fromTo(selector, {opacity:0,y:8}, {opacity:1,y:0,duration:0.12,ease:'power2.out'}, caption.start);
    tl.to(selector, {opacity:0,duration:0.09,ease:'power1.in'}, caption.end - 0.09);
    tl.set(selector, {opacity:0}, caption.end);
  });

  window.__timelines = window.__timelines || {};
  window.__timelines['twrp-story'] = tl;
  window.TWRP_RENDER_METADATA = {duration:timing.duration,sceneCount:timing.scenes.length,captionCount:timing.captions.length,characterCount:2,animatedSpeech:true};
})();
