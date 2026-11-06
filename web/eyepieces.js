/* Product facts and calculations are separate from native framing screenshots. */
(() => {
  'use strict';
  const data=window.ATLAS_DATA, planner=data.eyepiece_planner;
  if(!planner)return;
  const $=id=>document.getElementById(id), products=planner.eyepieces;
  const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const n=x=>Number(x).toLocaleString('en-GB',{maximumFractionDigits:2});
  const focal={power70:700,mak102:1300,mak127:1500,explorer130:650,startravel102:500,heritage130:650,heritage150:750};
  const metrics=(p,f=1300,d=102)=>{const power=f/p.focal_mm;return {power,pupil:d/power,field:p.field_stop_mm?p.field_stop_mm/f*57.3:p.afov_deg/power};};
  $('eyepiece-prices').innerHTML=products.map(p=>{const m=metrics(p);return `<tr><th><a href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.name)} ↗</a><span class="price">${esc(p.price)}</span><small>${esc(p.availability)}</small></th><td>${n(m.power)}×</td><td>${n(m.pupil)} mm</td><td>${n(m.field)}°<small>${p.field_stop_mm?'Published field stop':'Approx. AFOV / power'}</small></td><td>${n((p.focal_mm/10)**2*100)}%</td><td><strong>${esc(p.verdict)}</strong><small>${esc(p.priority)}${p.eye_relief_mm?' Eye relief: '+p.eye_relief_mm+' mm.':' Exact eye relief not verified.'}</small></td></tr>`;}).join('');
  $('eyepiece-price-note').textContent=`Prices checked ${planner.checked_at}. ${planner.price_note} The two 8 mm products are alternatives, not a recommended pair.`;
  $('compat-eyepiece').innerHTML=products.map(p=>`<option value="${p.id}" ${p.id==='swa8'?'selected':''}>${esc(p.name)}</option>`).join('');
  function compatibility(){const p=products.find(x=>x.id===$('compat-eyepiece').value);$('eyepiece-compatibility').innerHTML=data.instruments.filter(i=>focal[i.id]).map(i=>{const m=metrics(p,focal[i.id],i.aperture);let note=m.power>2*i.aperture?'Above nominal 2× aperture guideline':m.pupil<.6?'Demanding power / small exit pupil':'Nominal geometry; conditions still matter';if(i.id==='startravel102')note+=' · short achromat color fringing';return `<tr><th>${esc(i.name)}</th><td>${n(m.power)}×</td><td>${n(m.pupil)} mm</td><td>${n(m.field)}°</td><td>${esc(note)}</td></tr>`;}).join('');}
  $('compat-eyepiece').addEventListener('change',compatibility);compatibility();
  function render(){const state=document.documentElement.dataset,object=state.object,bortle=Number(state.bortle);$('eyepiece-section').hidden=state.filter==='owned';$('eyepiece-jump').hidden=state.filter==='owned';
    $('eyepiece-targets').innerHTML=planner.capture_objects.map(id=>{const o=data.objects.find(x=>x.id===id);return `<button data-planner-target="${id}" aria-pressed="${object===id}">${esc(o.name)}</button>`;}).join('');
    document.querySelectorAll('[data-planner-target]').forEach(b=>b.addEventListener('click',()=>{window.ATLAS_VIEWER.selectObject(b.dataset.plannerTarget);$('eyepiece-section').scrollIntoView({block:'start'});}));
    const available=planner.capture_objects.includes(object);
    $('eyepiece-capture-note').textContent=available?`MAK 102 · same ${data.objects.find(o=>o.id===object).name} scene · Bortle ${bortle}. No Barlow or reducer. Click a frame to inspect the original and move between eyepieces.`:'Native optional-eyepiece captures are available for the four targets above. Select one to view them; the purchase table and compatibility calculator remain usable.';
    const cards=available?products.map(p=>{const c=data.captures.find(x=>x.object===object&&x.bortle===bortle&&x.instrument==='mak102'&&x.cohort==='upgrade_'+p.id);const m=metrics(p);return `<article class="card"><div class="card-top"><h4>${esc(p.name)}</h4><span class="tag candidate">OPTIONAL · ${esc(p.price)}</span></div>${c?`<button class="frame" data-upgrade="${p.id}" aria-label="Inspect ${esc(p.name)} on MAK 102"><img src="${esc(c.image)}" alt="${esc(object)} at ${n(m.power)} times through MAK 102 with ${esc(p.name)}" loading="lazy" width="${c.width}" height="${c.height}"></button>`:'<div class="frame pending">Capture unavailable</div>'}<div class="card-bottom"><div class="measurement"><span class="power">${n(m.power)}×</span><span class="fov">${n(m.field)}° FIELD</span></div><div class="eyepiece">Exit pupil ${n(m.pupil)} mm · ${p.afov_deg}° apparent field</div><div class="caution">${esc(p.verdict)} · framing only</div></div></article>`;}).join(''):'';
    const baseline=available?data.captures.find(c=>c.object===object&&c.bortle===bortle&&c.instrument==='mak102'&&c.cohort==='second'):null;
    $('eyepiece-images').innerHTML=(baseline?`<article class="card"><div class="card-top"><h4>Included Super 10 mm</h4><span class="tag">STOCK REFERENCE · NO EXTRA COST</span></div><button class="frame" id="stock-planet-reference" aria-label="Inspect stock 10 mm reference"><img src="${esc(baseline.image)}" alt="Stock 10 mm reference on MAK 102 at 130 times" loading="lazy" width="${baseline.width}" height="${baseline.height}"></button><div class="card-bottom"><div class="measurement"><span class="power">130×</span><span class="fov">${n(baseline.field_of_view_deg)}° FIELD</span></div><div class="eyepiece">Exit pupil 0.78 mm · 100% brightness reference</div></div></article>`:'')+cards;
    if(baseline)$('stock-planet-reference').addEventListener('click',()=>window.ATLAS_VIEWER.open('mak102','second'));
    document.querySelectorAll('[data-upgrade]').forEach(b=>b.addEventListener('click',()=>window.ATLAS_VIEWER.open('mak102','upgrade_'+b.dataset.upgrade)));
  }
  window.addEventListener('atlas:render',render);render();
})();
