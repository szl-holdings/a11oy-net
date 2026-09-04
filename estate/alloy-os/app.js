function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"":"&quot;","'":"&#39;"}[c]));}
async function loadJSON(url){const r=await fetch(url,{cache:"no-store"});if(!r.ok) throw new Error(url+" "+r.status);return r.json();}

async function bootAlignment(){
  const rail=$("bake-rail"), table=$("align-table");
  let live=null, estate=null, spaces=null, models=null;
  try{ live=await loadJSON("./live.json"); }catch(e){ table.innerHTML="<p class='bad'>live.json UNAVAILABLE — "+esc(e.message)+"</p>"; }
  try{ estate=await loadJSON("/estate.json"); }catch(_){}
  try{ spaces=await loadJSON("/spaces.json"); }catch(_){}
  try{ models=await loadJSON("/models.json"); }catch(_){}
  const honest=live?.product_honest?.doctrine_lock||{};
  const hf=live?.hf_unauth||{};
  const rows=[
    ["Doctrine", honest.state||"—", "v11 "+(honest.commit||"")],
    ["Locked formulas", honest.locked_formula_count??"—", (honest.locked_formula_ids||[]).join(" ")],
    ["Keep spaces", (live?.keep_spaces||[]).length, (live?.keep_spaces||[]).join(" · ")],
    ["Hub spaces listed", hf.spaces?.length??"—", "unauth list API"],
    ["Hub models / datasets", (hf.models_listed??"—")+" / "+(hf.datasets_listed??"—"), "unauth list API"],
    ["Estate contract", estate?"loaded":"bake only", estate?.captured_at||live?.estate_capture?.captured_at||"—"],
  ];
  rail.innerHTML=rows.map(([k,v,d])=>`<article><span>${esc(k)}</span><b>${esc(v)}</b><p>${esc(d)}</p></article>`).join("");
  const align=live?.alignment||[];
  table.innerHTML=`<table class="align"><thead><tr><th>Plane</th><th>Class</th><th>Bind</th></tr></thead><tbody>${
    align.map(a=>`<tr><td>${esc(a.plane)}<br><a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.url)}</a></td><td>${esc(a.class)}</td><td>${esc(a.note)}</td></tr>`).join("")
  }</tbody></table>`;
}

function $(id){return document.getElementById(id);}

function renderKernel(){
  const el=$("kernel-app");
  if(!el||typeof Alloy==="undefined") return;
  const c=window.__compose||{title:"Session note",body:"A thought sealed on this device.",adapter:Alloy.ADAPTER_CURRENT,policy:"private",msg:"",tone:""};
  window.__compose=c;
  const receipts=[...Alloy.receipts].slice(-8).reverse().map(r=>`<li>#${r.seq} <b>${esc(r.type)}</b> ${esc(r.note)} <span>${esc(Alloy.shortHex(r.digest))}</span></li>`).join("");
  const caps=[...Alloy.capsules].slice(-6).reverse().map(x=>`<li>${esc(x.title)} · ${esc(x.status)} · ${esc(Alloy.shortHex(x.digest))}</li>`).join("");
  el.innerHTML=`<div class="kbox">
    <div class="kcard">
      <p class="eyebrow">${esc(Alloy.status)} · kid ${esc(Alloy.identity?.kid||"booting")} · epoch ${Alloy.epoch}</p>
      <label for="ktitle">Title</label><input id="ktitle" value="${esc(c.title)}">
      <label for="kbody">Payload</label><textarea id="kbody">${esc(c.body)}</textarea>
      <label for="kadapter">Adapter</label>
      <select id="kadapter">
        <option value="${Alloy.ADAPTER_CURRENT}">${Alloy.ADAPTER_CURRENT} pinned</option>
        <option value="alloy-local-v0" ${c.adapter==="alloy-local-v0"?"selected":""}>alloy-local-v0 stale</option>
      </select>
      <div class="kactions">
        <button class="button primary" id="ksubmit">Submit envelope</button>
        <button class="button" id="ktamper">Tamper one byte</button>
        <button class="button" id="kheal">Run healer</button>
      </div>
      ${c.msg?`<p class="${c.tone}">${esc(c.msg)}</p>`:""}
    </div>
    <div class="kcard">
      <p class="eyebrow">Ledger ${Alloy.receipts.length} · capsules ${Alloy.capsules.length} · healed ${Alloy.health.healed} · blocked ${Alloy.health.blocked}</p>
      <p>Replayable: ${Alloy.health.ledgerReplayable?"MEASURED":"degraded"} · last verify ${esc(Alloy.health.lastVerify||"—")}</p>
      <ol class="klog">${receipts||"<li>No receipts yet.</li>"}</ol>
      <p class="eyebrow">Capsules</p>
      <ol class="klog">${caps||"<li>None.</li>"}</ol>
    </div>
  </div>`;
  $("ksubmit").onclick=async()=>{
    c.title=$("ktitle").value; c.body=$("kbody").value; c.adapter=$("kadapter").value;
    const out=await Alloy.govern({title:c.title,body:c.body,policyClass:c.policy,adapter:c.adapter});
    c.msg=out.decision+" — "+out.reason+" · receipt "+out.receipt.seq;
    c.tone=out.decision==="ALLOW"?"ok":"bad";
    renderKernel();
  };
  $("ktamper").onclick=async()=>{c.msg=await Alloy.injectFault(); c.tone="warn"; renderKernel();};
  $("kheal").onclick=async()=>{await Alloy.runWatchdog(); c.msg="Watchdog complete."; c.tone="ok"; renderKernel();};
}

Alloy.subscribe(()=>renderKernel());
void (async()=>{
  await bootAlignment();
  await Alloy.boot();
  renderKernel();
})();
