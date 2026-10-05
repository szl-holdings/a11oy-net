
const cv = document.getElementById("holo"), ctx = cv.getContext("2d");
let rot = 0.15;
function resize(){ cv.width = innerWidth*devicePixelRatio; cv.height = innerHeight*devicePixelRatio; }
addEventListener("resize", resize); resize();
function knot(t,R,r,p,q){ return [(R+r*Math.cos(q*t))*Math.cos(p*t), r*Math.sin(q*t)*0.85, (R+r*Math.cos(q*t))*Math.sin(p*t)]; }
function proj(x,y,z,w,h){ const c=Math.cos(rot), s=Math.sin(rot); const x2=x*c-z*s, z2=x*s+z*c; const f=2.6/(4.2+z2); return [w*0.72+x2*f*w*0.16, h*0.42+y*f*h*0.22]; }
function frame(){
  const w=cv.width,h=cv.height; ctx.fillStyle="#03060c"; ctx.fillRect(0,0,w,h);
  const g=ctx.createRadialGradient(w*0.72,h*0.42,10,w*0.7,h*0.44,Math.max(w,h)*0.5);
  g.addColorStop(0,"rgba(58,244,200,.09)"); g.addColorStop(1,"rgba(3,6,12,0)");
  ctx.fillStyle=g; ctx.fillRect(0,0,w,h);
  rot += 0.003; ctx.save(); ctx.globalCompositeOperation="lighter";
  ctx.strokeStyle="rgba(58,244,200,.55)"; ctx.lineWidth=2*devicePixelRatio; ctx.beginPath();
  for(let i=0;i<=280;i++){ const k=knot(i/280*Math.PI*2,0.78,0.26,3,2); const q=proj(k[0],k[1],k[2],w,h); i?ctx.lineTo(q[0],q[1]):ctx.moveTo(q[0],q[1]); }
  ctx.stroke();
  ctx.strokeStyle="rgba(232,192,116,.35)"; ctx.lineWidth=1.2*devicePixelRatio; ctx.beginPath();
  for(let i=0;i<=180;i++){ const k=knot(i/180*Math.PI*2,0.42,0.16,2,3); const q=proj(k[0],k[1],k[2],w,h); i?ctx.lineTo(q[0],q[1]):ctx.moveTo(q[0],q[1]); }
  ctx.stroke();
  ctx.restore(); requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
