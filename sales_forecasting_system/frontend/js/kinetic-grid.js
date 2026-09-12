/* ═══════════════════════════════════════════════════════════════════════════
   KineticGrid — vanilla JS port
   Animated warped grid background that reacts to cursor + click ripples.
   Theme: black canvas + emerald green accents
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  // ─── Config ──────────────────────────────────────────────────────────────
  const CELL_SIZE = 55;
  const INFLUENCE_RADIUS = 260;
  const MAX_WARP = 24;
  const DOT_SPACING = 28;
  const LERP_SPEED = 0.08;

  const LINE_BASE = { r: 255, g: 255, b: 255, a: 0.06 };
  const NODE_BASE_RADIUS = 1.8;
  const NODE_ACTIVE_RADIUS = 3.2;

  // Theme
  const THEME = {
    bg: "#0a0a0a",
    lineActive: { r: 0, g: 255, b: 136, a: 0.85 },
    nodeActive: { r: 0, g: 255, b: 136, a: 1.0 },
    glow: "0,255,136",
    ripple: "0,255,136",
  };

  // ─── Helpers ─────────────────────────────────────────────────────────────
  function lerpN(a, b, t) {
    return a + (b - a) * t;
  }

  function lerpColor(base, active, t) {
    const r = Math.round(lerpN(base.r, active.r, t));
    const g = Math.round(lerpN(base.g, active.g, t));
    const b = Math.round(lerpN(base.b, active.b, t));
    const a = lerpN(base.a, active.a, t);
    return `rgba(${r},${g},${b},${a.toFixed(3)})`;
  }

  // ─── State ───────────────────────────────────────────────────────────────
  const canvas = document.getElementById("kinetic-grid-canvas");
  if (!canvas) {
    console.warn("KineticGrid: canvas#kinetic-grid-canvas not found");
    return;
  }
  const ctx = canvas.getContext("2d");

  let W = 0,
    H = 0;
  const mouse = { x: -9999, y: -9999 };
  const targetMouse = { x: -9999, y: -9999 };
  const ripples = [];
  let rafId = 0;
  let isPaused = false;

  // Respect reduced motion
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ─── Warp ────────────────────────────────────────────────────────────────
  function getWarpedPoint(gx, gy, col, row, mousePt, rips, cols, rows) {
    const edgeMargin = 1.5;
    const colPin = Math.min(col / edgeMargin, (cols - 1 - col) / edgeMargin, 1);
    const rowPin = Math.min(row / edgeMargin, (rows - 1 - row) / edgeMargin, 1);
    const pinFactor = colPin * colPin * rowPin * rowPin;

    const dx = gx - mousePt.x;
    const dy = gy - mousePt.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const proximity = Math.max(0, 1 - dist / INFLUENCE_RADIUS) * pinFactor;

    // Ripple displacement
    let rx = 0,
      ry = 0;
    for (let i = 0; i < rips.length; i++) {
      const r = rips[i];
      const rdx = gx - r.x;
      const rdy = gy - r.y;
      const rdist = Math.sqrt(rdx * rdx + rdy * rdy);
      const waveWidth = 55;
      const diff = rdist - r.radius;
      if (Math.abs(diff) < waveWidth) {
        const strength = (1 - Math.abs(diff) / waveWidth) * r.opacity * 18 * pinFactor;
        const angle = Math.atan2(rdy, rdx);
        const sign = diff < 0 ? -1 : 1;
        rx += Math.cos(angle) * strength * sign * -1;
        ry += Math.sin(angle) * strength * sign * -1;
      }
    }

    if (dist < INFLUENCE_RADIUS && dist > 0 && pinFactor > 0) {
      const t = dist / INFLUENCE_RADIUS;
      const eased = t < 0.01 ? 0 : (1 - t) * (1 - t) * Math.min(1, dist / 60);
      const warpAmt = eased * MAX_WARP * pinFactor;
      const angle = Math.atan2(dy, dx);
      return {
        pt: {
          x: gx - Math.cos(angle) * warpAmt + rx,
          y: gy - Math.sin(angle) * warpAmt + ry,
        },
        proximity,
      };
    }

    return { pt: { x: gx + rx, y: gy + ry }, proximity };
  }

  // ─── Draw ────────────────────────────────────────────────────────────────
  function draw(now) {
    ctx.clearRect(0, 0, W, H);

    // Background
    ctx.fillStyle = THEME.bg;
    ctx.fillRect(0, 0, W, H);

    // Static dot texture
    ctx.fillStyle = "rgba(255,255,255,0.035)";
    for (let x = DOT_SPACING / 2; x < W; x += DOT_SPACING) {
      for (let y = DOT_SPACING / 2; y < H; y += DOT_SPACING) {
        ctx.beginPath();
        ctx.arc(x, y, 0.7, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // Age ripples
    for (let i = ripples.length - 1; i >= 0; i--) {
      const r = ripples[i];
      const age = (now - r.born) / 1000;
      r.radius = Math.max(0, age * 400);
      r.opacity = Math.max(0, 1 - age * 1.2);
      if (r.opacity <= 0) ripples.splice(i, 1);
    }

    const cols = Math.max(2, Math.ceil(W / CELL_SIZE)) + 1;
    const rows = Math.max(2, Math.ceil(H / CELL_SIZE)) + 1;
    const cellW = W / (cols - 1);
    const cellH = H / (rows - 1);

    const pts = [];
    const prox = [];

    for (let row = 0; row < rows; row++) {
      pts[row] = [];
      prox[row] = [];
      for (let col = 0; col < cols; col++) {
        const res = getWarpedPoint(
          col * cellW,
          row * cellH,
          col,
          row,
          mouse,
          ripples,
          cols,
          rows,
        );
        pts[row][col] = res.pt;
        prox[row][col] = res.proximity;
      }
    }

    // Draw segments
    function drawSeg(p1, p2, pr1, pr2) {
      const avg = (pr1 + pr2) / 2;
      const t = avg * avg * (3 - 2 * avg);
      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.strokeStyle = lerpColor(LINE_BASE, THEME.lineActive, t);
      ctx.lineWidth = lerpN(0.7, 1.5, t);
      ctx.stroke();
    }

    ctx.lineCap = "butt";

    for (let row = 0; row < rows; row++)
      for (let col = 0; col < cols - 1; col++)
        drawSeg(pts[row][col], pts[row][col + 1], prox[row][col], prox[row][col + 1]);

    for (let col = 0; col < cols; col++)
      for (let row = 0; row < rows - 1; row++)
        drawSeg(pts[row][col], pts[row + 1][col], prox[row][col], prox[row + 1][col]);

    // Intersection nodes
    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        const p = pts[row][col];
        const pr = prox[row][col];
        const t = pr * pr * (3 - 2 * pr);
        const r = lerpN(NODE_BASE_RADIUS, NODE_ACTIVE_RADIUS, t);

        if (t > 0.3) {
          const glowR = r + lerpN(0, 6, (t - 0.3) / 0.7);
          const grd = ctx.createRadialGradient(p.x, p.y, r * 0.5, p.x, p.y, glowR);
          grd.addColorStop(0, `rgba(${THEME.glow},${(t * 0.35).toFixed(3)})`);
          grd.addColorStop(1, `rgba(${THEME.glow},0)`);
          ctx.beginPath();
          ctx.arc(p.x, p.y, glowR, 0, Math.PI * 2);
          ctx.fillStyle = grd;
          ctx.fill();
        }

        ctx.beginPath();
        ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        ctx.fillStyle = lerpColor({ r: 255, g: 255, b: 255, a: 0.15 }, THEME.nodeActive, t);
        ctx.fill();
      }
    }

    // Ripple rings
    for (let i = 0; i < ripples.length; i++) {
      const r = ripples[i];
      const safeR = Math.max(0, r.radius);
      ctx.beginPath();
      ctx.arc(r.x, r.y, safeR, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(${THEME.ripple},${(r.opacity * 0.35).toFixed(3)})`;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
  }

  // ─── Animation loop ──────────────────────────────────────────────────────
  function animate(now) {
    if (!isPaused) {
      mouse.x = lerpN(mouse.x, targetMouse.x, LERP_SPEED);
      mouse.y = lerpN(mouse.y, targetMouse.y, LERP_SPEED);
      draw(now);
    }
    rafId = requestAnimationFrame(animate);
  }

  // ─── Setup ───────────────────────────────────────────────────────────────
  function setSize() {
    W = window.innerWidth;
    H = window.innerHeight;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width = W + "px";
    canvas.style.height = H + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function onMouseMove(e) {
    targetMouse.x = e.clientX;
    targetMouse.y = e.clientY;
  }

  function onMouseLeave() {
    targetMouse.x = -9999;
    targetMouse.y = -9999;
  }

  function onClick(e) {
    // Don't create ripples when clicking interactive UI elements
    const t = e.target;
    if (t && t.closest && t.closest("button, a, input, select, textarea, .no-ripple")) {
      return;
    }
    ripples.push({
      x: e.clientX,
      y: e.clientY,
      radius: 0,
      opacity: 1,
      born: performance.now(),
    });
  }

  function onVisibility() {
    isPaused = document.hidden;
  }

  // Init
  setSize();
  window.addEventListener("resize", setSize);
  window.addEventListener("mousemove", onMouseMove, { passive: true });
  window.addEventListener("mouseleave", onMouseLeave);
  window.addEventListener("click", onClick);
  document.addEventListener("visibilitychange", onVisibility);

  if (reduceMotion) {
    // Draw one static frame, no animation
    draw(performance.now());
  } else {
    rafId = requestAnimationFrame(animate);
  }

  // Expose a tiny API for debugging
  window.KineticGrid = {
    addRipple: function (x, y) {
      ripples.push({ x, y, radius: 0, opacity: 1, born: performance.now() });
    },
    pause: function () {
      isPaused = true;
    },
    resume: function () {
      isPaused = false;
    },
  };
})();