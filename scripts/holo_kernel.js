// SPDX-License-Identifier: Apache-2.0
// SZL monochrome holographic proof-kernel (design system v1).
// A fibonacci-sphere point cloud drawn on <canvas id="holo">: depth-brightened
// white dots, faint white lattice links, one warm-white core glow. Monochrome
// only. No network access, no data binding, no claim: it is a decorative
// scientific-scan motif and never renders a measured value.
(function () {
  "use strict";

  var cv = document.getElementById("holo");
  if (!cv || typeof cv.getContext !== "function") return;
  var ctx = cv.getContext("2d");
  if (!ctx) return;

  var DPR = Math.min(window.devicePixelRatio || 1, 2);
  var W = 0, H = 0, CX = 0, CY = 0, S = 0;

  function resize() {
    W = cv.width = Math.max(1, cv.clientWidth * DPR);
    H = cv.height = Math.max(1, (cv.clientHeight || 600) * DPR);
    CX = W * 0.5;
    CY = H * 0.5;
    S = Math.min(W, H) * 0.32;
  }
  resize();
  window.addEventListener("resize", resize);

  var reduceQuery = window.matchMedia
    ? window.matchMedia("(prefers-reduced-motion: reduce)")
    : null;
  var reduce = !!(reduceQuery && reduceQuery.matches);

  var N = reduce ? 420 : 900;
  var pts = [];
  for (var i = 0; i < N; i++) {
    var y = 1 - (i / (N - 1)) * 2;
    var rr = Math.sqrt(Math.max(0, 1 - y * y));
    var th = i * 2.399963;
    pts.push([Math.cos(th) * rr, y, Math.sin(th) * rr]);
  }

  var t = 0;
  function frame() {
    ctx.clearRect(0, 0, W, H);
    if (!reduce) t += 0.0032;
    var cy = Math.cos(t), sy = Math.sin(t);
    var cx = Math.cos(t * 0.5), sx = Math.sin(t * 0.5);
    var proj = [];
    for (var i = 0; i < pts.length; i++) {
      var x = pts[i][0], y = pts[i][1], z = pts[i][2];
      var x1 = x * cy - z * sy, z1 = x * sy + z * cy;
      var y2 = y * cx - z1 * sx, z2 = y * sx + z1 * cx;
      var d = 2.6 / (2.6 + z2);
      proj.push([CX + x1 * S * d, CY + y2 * S * d, z2, d]);
    }
    // faint lattice links between nearby points
    ctx.lineWidth = 0.6 * DPR;
    var reach = 46 * DPR;
    for (var a = 0; a < proj.length; a += 7) {
      var p = proj[a];
      for (var b = a + 1; b < Math.min(a + 9, proj.length); b++) {
        var q = proj[b];
        var dx = p[0] - q[0], dy = p[1] - q[1];
        if (dx * dx + dy * dy < reach * reach) {
          ctx.strokeStyle = "rgba(255,255,255," + (0.05 * p[3]).toFixed(3) + ")";
          ctx.beginPath();
          ctx.moveTo(p[0], p[1]);
          ctx.lineTo(q[0], q[1]);
          ctx.stroke();
        }
      }
    }
    // points — brightness by depth (holographic volume)
    for (var k = 0; k < proj.length; k++) {
      var px = proj[k][0], py = proj[k][1], pz = proj[k][2], pd = proj[k][3];
      var bright = 0.28 + 0.72 * ((pz + 1) / 2);
      var r = (0.7 + 1.3 * pd) * DPR;
      ctx.fillStyle = "rgba(255,255,255," + (0.15 + 0.6 * bright).toFixed(3) + ")";
      ctx.beginPath();
      ctx.arc(px, py, r, 0, 7);
      ctx.fill();
    }
    // single warm-white core glow (very subtle)
    var g = ctx.createRadialGradient(CX, CY, 0, CX, CY, S * 1.4);
    g.addColorStop(0, "rgba(240,238,230,0.06)");
    g.addColorStop(1, "rgba(240,238,230,0)");
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(CX, CY, S * 1.4, 0, 7);
    ctx.fill();
    if (!reduce) window.requestAnimationFrame(frame);
  }
  frame();

  if (reduceQuery && typeof reduceQuery.addEventListener === "function") {
    reduceQuery.addEventListener("change", function (event) {
      reduce = !!event.matches;
      if (!reduce) window.requestAnimationFrame(frame);
      else frame();
    });
  }
}());
