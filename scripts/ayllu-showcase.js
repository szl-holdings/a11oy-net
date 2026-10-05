
const ROSTER = [
  ["Amaru","serpent / vision"],["Ruwaq","maker"],["Yupaq","one who counts"],
  ["Qhaway","one who sees"],["Maskaq","seeker"],["Hampiq","healer"],
  ["Yanapaq","helper"],["Chaka","bridge"],["Kamachiq","organizer"],
  ["Qhatuq","trader"],["Willakuq","chronicler"]
];
const COLORS = ["#e8c074","#ff9a4a","#3af4c8","#b38bff","#7ad7ff","#7dffb0","#6ea8ff","#e8c074","#eef3f6","#ff7a9c","#c9d6e2"];
document.getElementById("seats").innerHTML = ROSTER.map((s,i)=>
  `<div class="seat"><b style="color:${COLORS[i]}">${s[0]}</b><span>${s[1]}</span></div>`
).join("");
const cv = document.getElementById("holo"), ctx = cv.getContext("2d");
let rot = 0.2;
function resize(){ cv.width = innerWidth*devicePixelRatio; cv.height = innerHeight*devicePixelRatio; }
addEventListener("resize", resize); resize();
function knot(t,R,r,p,q){ return [(R+r*Math.cos(q*t))*Math.cos(p*t), r*Math.sin(q*t)*0.85, (R+r*Math.cos(q*t))*Math.sin(p*t)]; }
function proj(x,y,z,w,h){ const c=Math.cos(rot), s=Math.sin(rot); const x2=x*c-z*s, z2=x*s+z*c; const f=2.6/(4.2+z2); return [w*0.72+x2*f*w*0.16, h*0.38+y*f*h*0.22]; }
function frame(){
  const w=cv.width,h=cv.height; ctx.fillStyle="#03060c"; ctx.fillRect(0,0,w,h);
  const g=ctx.createRadialGradient(w*0.72,h*0.38,10,w*0.7,h*0.4,Math.max(w,h)*0.5);
  g.addColorStop(0,"rgba(58,244,200,.09)"); g.addColorStop(1,"rgba(3,6,12,0)");
  ctx.fillStyle=g; ctx.fillRect(0,0,w,h);
  rot += 0.003; ctx.save(); ctx.globalCompositeOperation="lighter";
  ctx.strokeStyle="rgba(232,192,116,.5)"; ctx.lineWidth=2*devicePixelRatio; ctx.beginPath();
  for(let i=0;i<=240;i++){ const k=knot(i/240*Math.PI*2,0.72,0.28,3,2); const q=proj(k[0],k[1],k[2],w,h); i?ctx.lineTo(q[0],q[1]):ctx.moveTo(q[0],q[1]); }
  ctx.stroke();
  ROSTER.forEach((s,i)=>{ const a=(i/11)*Math.PI*2-Math.PI/2; const q=proj(Math.cos(a+rot*0.15)*1.85,0.05,Math.sin(a+rot*0.15)*1.85,w,h);
    ctx.fillStyle=COLORS[i]; ctx.beginPath(); ctx.arc(q[0],q[1],7*devicePixelRatio,0,Math.PI*2); ctx.fill(); });
  ctx.restore(); requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
