// ═══════════════════════════════════════════════════════════════
// OCEAN JOURNEY — Pirate Ship Canvas Animation for Notak Music Hub
// States: ANCHORED → DEPARTING → SAILING → ARRIVING → ANCHORED
// ═══════════════════════════════════════════════════════════════
const OceanScene = (() => {
  const S = { ANCHORED: 0, DEPARTING: 1, SAILING: 2, ARRIVING: 3 };
  let cv, ctx, raf, t = 0, state = S.ANCHORED, tp = 0;
  let worldX = 0;
  let sh = { bobY: 0, bobPh: 0, roll: 0, sailAmt: 0, anchorAmt: 1, spd: 0, targetSpd: 0, startStopSpd: 0 };
  let sea = { waveH: 0.4, choppy: 0, wind: 0.3 };
  let gustT = 0, gustDur = 6, waveT = 0, waveDur = 9;
  let clouds = [], birds = [], islands = [];
  const islandTypes = ['tropical', 'pine', 'jungle', 'barren', 'atoll', 'village_hill', 'village_coast'];

  function genIslandFeats(type) {
    let f = [];
    const rnd = () => Math.random();
    if (type === 'tropical') {
      let n = 2 + Math.floor(rnd()*3);
      for(let i=0; i<n; i++) f.push({ x: (rnd()-0.5)*0.6, type: 'palm' });
    } else if (type === 'pine') {
      let n = 4 + Math.floor(rnd()*5);
      for(let i=0; i<n; i++) f.push({ x: (rnd()-0.5)*0.7, type: 'pine' });
    } else if (type === 'jungle') {
      let n = 5 + Math.floor(rnd()*5);
      for(let i=0; i<n; i++) f.push({ x: (rnd()-0.5)*0.8, type: 'jungle' });
    } else if (type === 'atoll') {
      if (rnd() > 0.3) f.push({ x: (rnd()-0.5)*0.4, type: 'palm' });
    } else if (type === 'barren') {
      let n = 3 + Math.floor(rnd()*4);
      for(let i=0; i<n; i++) f.push({ x: (rnd()-0.5)*0.7, type: 'rock' });
    } else if (type === 'village_hill') {
      f.push({ x: 0, type: 'chief_hut' });
      f.push({ x: -0.25, type: 'hut' });
      f.push({ x: 0.25, type: 'hut' });
      f.push({ x: -0.4, type: 'canoe', flip: false });
      f.push({ x: 0.4, type: 'canoe', flip: true });
      f.push({ x: -0.15, type: 'palm' });
    } else if (type === 'village_coast') {
      f.push({ x: -0.1, type: 'chief_hut' });
      f.push({ x: 0.2, type: 'hut' });
      f.push({ x: -0.3, type: 'hut' });
      f.push({ x: -0.45, type: 'canoe', flip: false });
      f.push({ x: 0.35, type: 'canoe', flip: true });
      f.push({ x: 0.45, type: 'canoe', flip: true });
      f.push({ x: -0.2, type: 'palm' });
      f.push({ x: 0.3, type: 'palm' });
    }
    return f.sort((a,b) => Math.abs(b.x) - Math.abs(a.x)); 
  }

  function init() {
    cv = document.getElementById('ocean-canvas');
    if (!cv) return;
    ctx = cv.getContext('2d');
    resize();
    clouds = Array.from({ length: 7 }, () => mkCloud(Math.random() * cv.width));
    islands = [
      { wx: 900,  sc: 1.0, type: 'tropical', feats: genIslandFeats('tropical') },
      { wx: 2400, sc: 0.8, type: 'village_coast', feats: genIslandFeats('village_coast') },
      { wx: 4200, sc: 1.1, type: 'pine', feats: genIslandFeats('pine') },
      { wx: 5800, sc: 0.9, type: 'village_hill', feats: genIslandFeats('village_hill') },
    ];
    sh = { bobY: 0, bobPh: 0, roll: 0, sailAmt: 0, anchorAmt: 1, spd: 0, targetSpd: 0, startStopSpd: 0 };
    state = S.ANCHORED; tp = 0;
    if (raf) cancelAnimationFrame(raf);
    loop();

    // Hook audio element events
    const au = document.getElementById('audio-el');
    if (au) {
      au.addEventListener('play',  () => { if (state === S.ANCHORED || state === S.ARRIVING) { state = S.DEPARTING; tp = 0; } });
      au.addEventListener('pause', () => { if (state === S.SAILING  || state === S.DEPARTING) { state = S.ARRIVING; tp = 0; sh.startStopSpd = sh.spd; } });
      au.addEventListener('ended', () => { if (state === S.SAILING  || state === S.DEPARTING) { state = S.ARRIVING; tp = 0; sh.startStopSpd = sh.spd; } });
    }
  }

  function resize() {
    if (!cv) return;
    const p = cv.parentElement;
    cv.width  = (p ? p.clientWidth  : 600) || 600;
    cv.height = (p ? p.clientHeight : 190) || 190;
  }

  function mkCloud(x) {
    return { x, y: 10 + Math.random() * 42, spd: 0.12 + Math.random() * 0.22,
             w: 55 + Math.random() * 75, h: 17 + Math.random() * 20,
             op: 0.32 + Math.random() * 0.38 };
  }

  function mkBird(x) {
    return { x, y: 14 + Math.random() * 54, spd: 0.9 + Math.random() * 1.7,
             ph: Math.random() * Math.PI * 2, sz: 3 + Math.random() * 3.5 };
  }

  function wave(x, off, amp, freq, parallax) {
    // Wave moves forward based on absolute time (t), parallax shifts it with camera (worldX)
    const phase1 = x + worldX * parallax + t * 40;
    const phase2 = x + worldX * parallax * 0.62 + t * 55;
    return Math.sin((phase1 + off) * freq) * amp
         + Math.sin((phase2 + off * 1.37) * freq * 1.73) * amp * 0.32;
  }

  // ── Update logic ────────────────────────────────────────────
  function update() {
    t += 0.016;

    if (state === S.DEPARTING) {
      tp = Math.min(1, tp + 0.0025); // Takes about 6.5 seconds (slow, gradual start)
      sh.sailAmt   = Math.min(1, tp * 2.2); // Sails unfurl slightly faster
      sh.anchorAmt = Math.max(0, 1 - tp * 4); // Anchor drops fast
      
      // Smoothstep for gradual speed curve up to initial moving speed
      let smoothTp = tp * tp * (3 - 2 * tp);
      sh.targetSpd = smoothTp * 3.0; // Gradually gets up to 3.0 while unfurling
      
      sea.waveH = 0.4 + smoothTp * 0.8;
      
      if (tp >= 1) { state = S.SAILING; sea.choppy = 0.22; sea.wind = 0.5; }
    } else if (state === S.SAILING) {
      gustT += 0.016; waveT += 0.016;
      if (gustT > gustDur) { gustT = 0; gustDur = 4 + Math.random() * 14; sea.wind = 0.15 + Math.random() * 0.9; }
      if (waveT > waveDur) { waveT = 0; waveDur = 5 + Math.random() * 20; sea.choppy = Math.random() * 0.95; sea.waveH = 0.35 + Math.random() * 1.8; }
      
      // Highway speed! Shifts up to a much faster, dynamic speed based on random wind gusts
      sh.targetSpd = 4.0 + sea.wind * 6.5; 
    } else if (state === S.ARRIVING) {
      tp = Math.min(1, tp + 0.0028); // Takes about 6 seconds (gradual brake)
      sh.sailAmt   = Math.max(0, 1 - tp * 2.2);
      sh.anchorAmt = Math.min(1, tp * 2.2);
      
      // Smoothstep ramp down from whatever highway speed we were at when paused
      let smoothTp = tp * tp * (3 - 2 * tp);
      sh.targetSpd = sh.startStopSpd * (1 - smoothTp);
      
      sea.choppy = Math.max(0, sea.choppy - 0.005);
      sea.waveH  = Math.max(0.4, sea.waveH - 0.004);
      
      if (tp >= 1) { 
        state = S.ANCHORED; 
        sh.spd = 0; 
        sh.targetSpd = 0; 
        sh.sailAmt = 0; 
        sh.anchorAmt = 1; 
        sea.waveH = 0.4; 
        sea.choppy = 0; 
      }
    } else if (state === S.ANCHORED) {
      sh.targetSpd = 0;
    }

    // Smooth speed interpolation
    // Once sails are down (SAILING), we accelerate faster onto the "highway"
    let accel = 0.015;
    if (state === S.SAILING) accel = 0.02;   // Accelerating dynamically on the highway
    if (state === S.ARRIVING) accel = 0.035; // Firm braking
    
    sh.spd += (sh.targetSpd - sh.spd) * accel;
    if (sh.spd < 0.001) sh.spd = 0; // complete stop

    worldX += sh.spd * 0.44;

    // Bobbing
    const bobF = 0.33 + sea.choppy * 0.52;
    const bobA = 2.2 + sea.waveH * 6.5;
    sh.bobPh += bobF * 0.05;
    sh.bobY  = Math.sin(sh.bobPh) * bobA + Math.sin(sh.bobPh * 1.82 + 0.55) * bobA * 0.33;
    sh.roll  = Math.sin(sh.bobPh * 0.78) * sea.choppy * 0.072 + Math.sin(sh.bobPh * 1.43) * 0.016;

    // Clouds
    const cSpd = 0.22 + sea.wind * 0.38;
    clouds.forEach(c => { c.x -= c.spd * cSpd; if (c.x < -c.w - 40) { c.x = cv.width + 50; c.y = 10 + Math.random() * 42; } });

    // Birds
    if (Math.random() < 0.004 && birds.length < 6 && state === S.SAILING) birds.push(mkBird(cv.width + 20));
    birds.forEach(b => { b.x -= b.spd; b.ph += 0.1; });
    birds = birds.filter(b => b.x > -40);

    // Extend island list as world grows
    const last = islands[islands.length - 1];
    if (worldX * 0.26 + cv.width > last.wx - 700) {
      let tpe = islandTypes[Math.floor(Math.random() * islandTypes.length)];
      islands.push({ 
        wx: last.wx + 1200 + Math.random() * 1200, 
        sc: 0.7 + Math.random() * 0.6,
        type: tpe,
        feats: genIslandFeats(tpe)
      });
    }
  }

  // ── Draw sky ────────────────────────────────────────────────
  function drawSky() {
    const W = cv.width, H = cv.height, wy = H * 0.52;
    const sg = ctx.createLinearGradient(0, 0, 0, wy);
    sg.addColorStop(0, '#04020f'); sg.addColorStop(0.45, '#0c051e'); sg.addColorStop(1, '#160838');
    ctx.fillStyle = sg; ctx.fillRect(0, 0, W, wy);
    const hg = ctx.createLinearGradient(0, wy - 30, 0, wy);
    hg.addColorStop(0, 'transparent'); hg.addColorStop(1, 'rgba(100,30,180,0.16)');
    ctx.fillStyle = hg; ctx.fillRect(0, wy - 30, W, 30);
    // Stars
    const star = [[.07,.06],[.17,.13],[.29,.04],[.44,.09],[.58,.03],[.72,.12],[.86,.06],
                  [.11,.21],[.40,.18],[.65,.20],[.80,.08],[.93,.15],[.24,.27],[.53,.25]];
    star.forEach(([sx, sy]) => {
      ctx.globalAlpha = (0.38 + 0.62 * Math.sin(t * 1.9 + sx * 9.2)) * 0.82;
      ctx.fillStyle = '#fff'; ctx.beginPath();
      ctx.arc(sx * W, sy * wy, 0.85, 0, Math.PI * 2); ctx.fill();
    });
    ctx.globalAlpha = 1;
    // Moon
    const mx = W * 0.84, my = wy * 0.21;
    const mg = ctx.createRadialGradient(mx, my, 0, mx, my, 28);
    mg.addColorStop(0, 'rgba(230,210,255,0.17)'); mg.addColorStop(1, 'transparent');
    ctx.fillStyle = mg; ctx.fillRect(mx - 28, my - 28, 56, 56);
    ctx.fillStyle = '#ede8ff'; ctx.beginPath(); ctx.arc(mx, my, 10.5, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#0c051e';  ctx.beginPath(); ctx.arc(mx + 4, my - 1, 8.5, 0, Math.PI * 2); ctx.fill();
    // Moon reflection trail on water
    for (let i = 0; i < 4; i++) {
      ctx.fillStyle = `rgba(190,165,255,${0.055 - i * 0.01})`;
      ctx.fillRect(mx - (13 - i * 3), wy + 7 + i * 8, 26 - i * 6, 3);
    }
  }

  // ── Draw clouds ─────────────────────────────────────────────
  function drawClouds() {
    clouds.forEach(c => {
      ctx.save(); ctx.globalAlpha = c.op * 0.62;
      ctx.fillStyle = 'rgba(172,148,235,1)';
      ctx.beginPath();
      ctx.ellipse(c.x,             c.y,            c.w * 0.52, c.h * 0.56, 0, 0, Math.PI * 2);
      ctx.ellipse(c.x - c.w * 0.3, c.y + c.h * 0.12, c.w * 0.33, c.h * 0.5, 0, 0, Math.PI * 2);
      ctx.ellipse(c.x + c.w * 0.3, c.y + c.h * 0.1,  c.w * 0.29, c.h * 0.46, 0, 0, Math.PI * 2);
      ctx.fill(); ctx.restore();
    });
  }

  // ── Draw birds ──────────────────────────────────────────────
  function drawBirds() {
    birds.forEach(b => {
      const flap = Math.sin(b.ph) * b.sz * 0.65;
      ctx.strokeStyle = 'rgba(195,170,255,0.68)'; ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(b.x - b.sz, b.y - flap);
      ctx.quadraticCurveTo(b.x, b.y, b.x + b.sz, b.y - flap);
      ctx.stroke();
    });
  }

  // ── Island drawing helpers ──────────────────────────────────
  function drawPalm(tx, ty, sc) {
    ctx.strokeStyle = '#4a2e0e'; ctx.lineWidth = 2.5 * sc; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(tx, ty + 4*sc);
    ctx.bezierCurveTo(tx + 5*sc, ty - 10*sc, tx - 3*sc, ty - 22*sc, tx - 1, ty - 30*sc); ctx.stroke();
    ctx.strokeStyle = '#2a5a18'; ctx.lineWidth = 1.8 * sc;
    for (let i = 0; i < 5; i++) {
      const ang = -Math.PI * 0.22 + i * 0.32 + Math.sin(t * 0.7 + tx) * 0.1;
      ctx.beginPath(); ctx.moveTo(tx - 1, ty - 30*sc);
      ctx.lineTo(tx - 1 + Math.cos(ang) * 18 * sc, ty - 30 * sc + Math.sin(ang) * 10 * sc); ctx.stroke();
    }
  }

  function drawPine(tx, ty, sc) {
    ctx.fillStyle = '#113311';
    ctx.beginPath(); ctx.moveTo(tx, ty - 26*sc);
    ctx.lineTo(tx - 9*sc, ty); ctx.lineTo(tx + 9*sc, ty); ctx.fill();
    ctx.fillStyle = '#0a220a';
    ctx.beginPath(); ctx.moveTo(tx, ty - 26*sc);
    ctx.lineTo(tx, ty); ctx.lineTo(tx + 9*sc, ty); ctx.fill();
  }

  function drawJungleTree(tx, ty, sc) {
    ctx.strokeStyle = '#3a200a'; ctx.lineWidth = 3 * sc; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(tx, ty + 2*sc); ctx.lineTo(tx, ty - 14*sc); ctx.stroke();
    ctx.fillStyle = '#184a18';
    ctx.beginPath(); ctx.arc(tx, ty - 18*sc, 12*sc, 0, Math.PI*2); ctx.fill();
    ctx.fillStyle = '#113811';
    ctx.beginPath(); ctx.arc(tx - 3*sc, ty - 21*sc, 9*sc, 0, Math.PI*2); ctx.fill();
  }

  function drawHut(hx, hy, sc, isChief) {
    let w = (isChief ? 22 : 14) * sc;
    let h = (isChief ? 16 : 10) * sc;
    ctx.fillStyle = '#c8a87a'; 
    ctx.fillRect(hx - w/2, hy - h, w, h);
    ctx.fillStyle = '#3a200a'; 
    ctx.fillRect(hx - w/8, hy - h + h/2, w/4, h/2);
    ctx.fillStyle = '#8b6508'; 
    ctx.beginPath();
    ctx.moveTo(hx - w*0.6, hy - h);
    ctx.lineTo(hx, hy - h - (isChief ? 16 : 10)*sc);
    ctx.lineTo(hx + w*0.6, hy - h);
    ctx.closePath(); ctx.fill();
  }

  function drawCanoe(cx, cy, sc, flip) {
    ctx.fillStyle = '#5c3a21';
    ctx.beginPath();
    let dir = flip ? -1 : 1;
    ctx.moveTo(cx - 12*sc*dir, cy - 1*sc);
    ctx.lineTo(cx + 12*sc*dir, cy - 1*sc);
    ctx.quadraticCurveTo(cx + 6*sc*dir, cy + 4*sc, cx - 10*sc*dir, cy + 3*sc);
    ctx.fill();
  }

  // ── Draw island ─────────────────────────────────────────────
  function drawIsland(isl) {
    const W = cv.width, H = cv.height, wy = H * 0.52;
    const sx = isl.wx - worldX * 0.26;
    if (sx < -250 || sx > W + 250) return;
    
    let iW = 110 * isl.sc;
    let iH = 46 * isl.sc;
    if (isl.type.startsWith('village')) { iW *= 1.5; iH *= 1.3; } 
    if (isl.type === 'atoll' || isl.type === 'barren') { iH *= 0.4; }
    if (isl.type === 'rocky') { iH *= 1.15; }

    const ig = ctx.createLinearGradient(sx, wy - iH, sx, wy + 8);
    if (isl.type === 'rocky' || isl.type === 'barren') {
      ig.addColorStop(0, '#1c1c28'); ig.addColorStop(0.75, '#12121c'); ig.addColorStop(1, '#0a0a12');
    } else {
      ig.addColorStop(0, '#183618'); ig.addColorStop(0.75, '#0c220c'); ig.addColorStop(1, '#07100a');
    }
    ctx.fillStyle = ig;
    ctx.beginPath();
    ctx.moveTo(sx - iW * 0.5, wy + 6);
    
    if (isl.type === 'rocky') {
       ctx.lineTo(sx - iW*0.25, wy - iH*0.7);
       ctx.lineTo(sx - iW*0.1, wy - iH*1.1);
       ctx.lineTo(sx + iW*0.15, wy - iH*0.8);
       ctx.lineTo(sx + iW*0.35, wy - iH*0.4);
       ctx.lineTo(sx + iW*0.5, wy + 6);
    } else if (isl.type === 'village_hill') {
       ctx.bezierCurveTo(sx - iW*0.4, wy, sx - iW*0.2, wy - iH*1.1, sx, wy - iH*1.1);
       ctx.bezierCurveTo(sx + iW*0.2, wy - iH*1.1, sx + iW*0.4, wy, sx + iW*0.5, wy + 6);
    } else {
       ctx.bezierCurveTo(sx - iW * 0.38, wy - iH * 0.28, sx - iW * 0.06, wy - iH, sx, wy - iH * 1.05);
       ctx.bezierCurveTo(sx + iW * 0.11,  wy - iH * 1.16, sx + iW * 0.36, wy - iH * 0.42, sx + iW * 0.5, wy + 6);
    }
    ctx.closePath(); ctx.fill();

    // Sandy beach
    if (isl.type !== 'rocky') {
      ctx.fillStyle = 'rgba(155,120,55,0.32)';
      ctx.beginPath(); ctx.ellipse(sx, wy + 4, iW * 0.42, 5.5, 0, 0, Math.PI * 2); ctx.fill();
    }

    // Draw features
    if (isl.feats) {
      isl.feats.forEach(feat => {
        let fx = sx + feat.x * iW;
        let hr = Math.cos(feat.x * Math.PI); 
        if (hr < 0) hr = 0;
        let fy = wy + 4 - (iH * hr * 0.95);
        if (isl.type === 'village_hill') fy = wy + 4 - (iH * Math.pow(hr, 1.5) * 1.0);
        else if (isl.type === 'rocky') fy = wy + 4 - (iH * hr * 1.1);
        
        if (feat.type === 'canoe') fy = wy + 6; // snap to water level
        
        let sc = isl.sc;
        if (feat.type === 'palm') drawPalm(fx, fy, sc);
        else if (feat.type === 'pine') drawPine(fx, fy, sc);
        else if (feat.type === 'jungle') drawJungleTree(fx, fy, sc);
        else if (feat.type === 'hut') drawHut(fx, fy, sc, false);
        else if (feat.type === 'chief_hut') drawHut(fx, fy, sc, true);
        else if (feat.type === 'canoe') drawCanoe(fx, fy, sc, feat.flip);
        else if (feat.type === 'rock') {
           ctx.fillStyle = '#1c1c28';
           ctx.beginPath(); ctx.ellipse(fx, fy, 6*sc, 4*sc, 0, 0, Math.PI*2); ctx.fill();
        }
      });
    }
  }

  // ── Draw ocean ──────────────────────────────────────────────
  function drawOcean() {
    const W = cv.width, H = cv.height, wy = H * 0.52;
    const wg = ctx.createLinearGradient(0, wy, 0, H);
    wg.addColorStop(0, '#0a042a'); wg.addColorStop(0.38, '#06041a'); wg.addColorStop(1, '#030210');
    ctx.fillStyle = wg; ctx.fillRect(0, wy, W, H - wy);
    // Wave layers (far → near)
    const layers = [
      { off: 0,   amp: 2.0 * sea.waveH, freq: 0.013, parallax: 0.22, fill: 'rgba(16,6,50,0.62)' },
      { off: 260, amp: 3.8 * sea.waveH, freq: 0.019, parallax: 0.42, fill: 'rgba(10,4,38,0.70)' },
      { off: 530, amp: 5.2 * sea.waveH, freq: 0.025, parallax: 0.64, fill: 'rgba(24,8,62,0.50)' },
    ];
    layers.forEach(l => {
      ctx.beginPath(); ctx.moveTo(0, wy);
      for (let x = 0; x <= W; x += 2) ctx.lineTo(x, wy + wave(x, l.off, l.amp, l.freq, l.parallax));
      ctx.lineTo(W, H); ctx.lineTo(0, H); ctx.closePath();
      ctx.fillStyle = l.fill; ctx.fill();
    });
    // Wave crests / foam
    ctx.strokeStyle = 'rgba(130,88,240,0.11)'; ctx.lineWidth = 1;
    for (let li = 0; li < 3; li++) {
      ctx.beginPath();
      for (let x = 0; x <= W; x += 4) {
        const y = wy + 4 + li * 9 + wave(x, li * 175, 3.2 * sea.waveH, 0.02 + li * 0.004, 0.4);
        x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.stroke();
    }
  }

  // ── Draw ship ───────────────────────────────────────────────
  function drawShip() {
    const W = cv.width, H = cv.height, wy = H * 0.52;
    const sx = W * 0.32, sy = wy + sh.bobY;
    ctx.save();
    ctx.translate(sx, sy);
    ctx.rotate(sh.roll);

    // Anchor & chain
    if (sh.anchorAmt > 0.04) {
      const adrop = sh.anchorAmt * 26;
      const aOp = sh.anchorAmt * 0.72;
      ctx.strokeStyle = `rgba(155,130,210,${aOp})`; ctx.lineWidth = 1.4;
      ctx.setLineDash([3, 3]);
      ctx.beginPath(); ctx.moveTo(0, 9); ctx.lineTo(0, 9 + adrop); ctx.stroke();
      ctx.setLineDash([]);
      const ay = 9 + adrop;
      ctx.strokeStyle = `rgba(175,145,225,${aOp})`; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.arc(0, ay, 4.5, 0, Math.PI * 2); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, ay + 4.5); ctx.lineTo(0, ay + 11); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(-5, ay + 10); ctx.lineTo(5, ay + 10); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(-5, ay + 10); ctx.quadraticCurveTo(-8, ay + 14, -5.5, ay + 17); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(5,  ay + 10); ctx.quadraticCurveTo(8,  ay + 14, 5.5,  ay + 17); ctx.stroke();
    }

    // Masts & Bowsprit
    ctx.strokeStyle = '#634320'; ctx.lineWidth = 2; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(-18, -12); ctx.lineTo(-18, -55); ctx.stroke(); // Mizzen mast
    ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(-32, -42); ctx.lineTo(-4, -42); ctx.stroke(); // Mizzen yard
    
    ctx.strokeStyle = '#7a5828'; ctx.lineWidth = 2.4;
    ctx.beginPath(); ctx.moveTo(6, -10); ctx.lineTo(6, -75); ctx.stroke(); // Main mast
    ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(-14, -58); ctx.lineTo(26, -58); ctx.stroke(); // Main yard
    
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(35, -12); ctx.lineTo(55, -22); ctx.stroke(); // Bowsprit

    // Rigging lines
    ctx.strokeStyle = 'rgba(255,255,255,0.15)'; ctx.lineWidth = 0.5;
    ctx.beginPath(); ctx.moveTo(6, -75); ctx.lineTo(55, -22); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(6, -75); ctx.lineTo(-18, -55); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(-18, -55); ctx.lineTo(-40, -18); ctx.stroke();

    // Sails
    if (sh.sailAmt > 0.01) {
      const sailH_main = sh.sailAmt * 38;
      const sailH_miz = sh.sailAmt * 24;
      const billow = Math.sin(t * (1.4 + sea.wind)) * (3.5 + sea.wind * 6.5) * sh.sailAmt;
      
      const sailG = ctx.createLinearGradient(0, -60, 0, -20);
      sailG.addColorStop(0, `rgba(180,150,255,${0.85 * sh.sailAmt})`);
      sailG.addColorStop(1, `rgba(100,60,190,${0.65 * sh.sailAmt})`);
      ctx.fillStyle = sailG;
      ctx.strokeStyle = `rgba(120,80,200,${0.4 * sh.sailAmt})`;
      ctx.lineWidth = 0.5;

      // Mizzen sail
      ctx.beginPath();
      ctx.moveTo(-30, -42);
      ctx.quadraticCurveTo(-30 + billow*0.4, -42 + sailH_miz*0.5, -26, -42 + sailH_miz);
      ctx.lineTo(-10, -42 + sailH_miz);
      ctx.quadraticCurveTo(-6 + billow*0.4, -42 + sailH_miz*0.5, -6, -42);
      ctx.fill(); ctx.stroke();

      // Main sail
      ctx.beginPath();
      ctx.moveTo(-12, -58);
      ctx.quadraticCurveTo(-12 + billow*0.5, -58 + sailH_main*0.5, -8, -58 + sailH_main);
      ctx.lineTo(20, -58 + sailH_main);
      ctx.quadraticCurveTo(24 + billow*0.8, -58 + sailH_main*0.5, 24, -58);
      ctx.fill(); ctx.stroke();
      
      // Jib (front triangle sail)
      ctx.beginPath();
      ctx.moveTo(8, -55);
      ctx.quadraticCurveTo(25 + billow*0.4, -35, 48, -18);
      ctx.lineTo(28, -8);
      ctx.quadraticCurveTo(18 + billow*0.2, -30, 8, -55);
      ctx.fill();
    }
    
    // Bundled sails when furled
    if (sh.sailAmt < 0.99) {
      ctx.fillStyle = `rgba(90,60,145,${(1 - sh.sailAmt) * 0.5})`;
      ctx.beginPath(); ctx.rect(-30, -44, 24, 4); ctx.fill();
      ctx.beginPath(); ctx.rect(-12, -60, 36, 5); ctx.fill();
    }

    // Pirate flag (Jolly Roger)
    const flagWave = Math.sin(t * 2.8 + sh.roll * 4) * 4 * (0.15 + sea.wind * 0.85);
    ctx.fillStyle = 'rgba(200,30,50,0.85)';
    ctx.beginPath();
    ctx.moveTo(6, -74);
    ctx.lineTo(19, -70 + flagWave * 0.5);
    ctx.lineTo(6, -66 + flagWave);
    ctx.closePath(); ctx.fill();
    ctx.fillStyle = 'rgba(255,255,255,0.8)';
    ctx.beginPath(); ctx.arc(10, -70 + flagWave * 0.38, 1.5, 0, Math.PI * 2); ctx.fill();

    // Hull body - Galleon shape
    const hg = ctx.createLinearGradient(-40, -18, -40, 16);
    hg.addColorStop(0, '#2b1b47'); hg.addColorStop(1, '#130a24');
    ctx.fillStyle = hg;
    ctx.beginPath();
    ctx.moveTo(-40, -18); // Stern top
    ctx.lineTo(-38, 8); // Stern bottom
    ctx.quadraticCurveTo(-20, 16, 5, 16); // Bottom curve
    ctx.quadraticCurveTo(28, 16, 40, -2);
    ctx.lineTo(44, -10); // Bow
    ctx.quadraticCurveTo(20, -6, -20, -10); // Deck curve
    ctx.lineTo(-40, -18);
    ctx.closePath(); ctx.fill();
    ctx.strokeStyle = 'rgba(90,50,150,0.5)'; ctx.lineWidth = 1; ctx.stroke();

    // Wood panel lines
    ctx.strokeStyle = 'rgba(150,100,240,0.15)'; ctx.lineWidth = 0.5;
    ctx.beginPath(); ctx.moveTo(-38, -6); ctx.quadraticCurveTo(-10, -2, 38, -6); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(-38, 2); ctx.quadraticCurveTo(-10, 6, 32, 2); ctx.stroke();

    // Stern gallery windows (warm glow)
    ctx.fillStyle = 'rgba(240,200,100,0.6)';
    for (let i = 0; i < 3; i++) {
      ctx.fillRect(-37, -15 + i*4.5, 3.5, 3);
    }
    
    // Gold trim
    ctx.strokeStyle = 'rgba(200,150,50,0.6)'; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(-40, -18); ctx.lineTo(-20, -10); ctx.stroke();

    // Cannons
    for (let i = 0; i < 4; i++) {
      let cx = -20 + i * 14;
      let cy = 0;
      ctx.fillStyle = 'rgba(0,0,0,0.7)';
      ctx.fillRect(cx - 3, cy - 3, 6, 6); // Gunport
      ctx.fillStyle = '#333';
      ctx.fillRect(cx - 1, cy - 1, 7, 2); // Barrel
    }
    
    // Bow figurehead
    ctx.fillStyle = 'rgba(200,150,50,0.8)';
    ctx.beginPath(); ctx.arc(43, -9, 2, 0, Math.PI*2); ctx.fill();

    ctx.restore();
  }

  // ── Render loop ─────────────────────────────────────────────
  function loop() {
    if (!cv) return;
    update();
    ctx.clearRect(0, 0, cv.width, cv.height);
    drawSky();
    drawClouds();
    islands.forEach(drawIsland);
    drawOcean();
    drawBirds();
    drawShip();
    raf = requestAnimationFrame(loop);
  }

  window.addEventListener('resize', resize);

  return { init };
})();
