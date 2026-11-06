/* Local-only gallery: script data avoids file:// fetch restrictions. */
(() => {
  'use strict';
  const data = window.ATLAS_DATA;
  if (!data) { document.querySelector('main').textContent = 'Capture data is missing. Run capture_atlas.py first.'; return; }
  const requestedObject = new URLSearchParams(location.search).get('object');
  const initialObject = data.objects.some(o=>o.id===requestedObject) ? requestedObject : data.captures.some(c => c.object === 'pleiades' && c.bortle === 5) ? 'pleiades' : (data.captures[0]?.object || data.objects[0].id);
  const state = { object: initialObject, bortle: 5, filter: 'shortlist', viewer: null, inspection: false };
  const $ = id => document.getElementById(id);
  const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const number = value => Number(value).toLocaleString('en-GB', { maximumFractionDigits: 2 });
  const objects = data.objects;
  const instrumentList = () => data.instruments.filter(i => state.filter === 'all' || (state.filter === 'shortlist' ? i.shortlist : i.owned === (state.filter === 'owned')));
  const target = () => objects.find(o => o.id === state.object);
  const captureFor = (instrument, cohort) => data.captures.find(c => !(instrument.id === 'vortex' && cohort.startsWith('reducer')) && c.object === state.object && c.bortle === state.bortle && c.instrument === instrument.id && c.cohort === (instrument.id === 'vortex' ? 'fixed' : cohort));
  const timeLabel = at => {
    const offset = at.slice(-6), zone = offset === '+02:00' ? 'CEST' : 'CET';
    return new Intl.DateTimeFormat('en-GB', { timeZone:'Europe/Warsaw', day:'2-digit', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit', hourCycle:'h23' }).format(new Date(at)) + ` Warsaw (${zone}, UTC${offset})`;
  };
  function renderNav() {
    let group = '';
    $('targets').innerHTML = objects.map((o,index) => {
      const nextGroup = index < 6 ? 'REFERENCE & PLANETS' : 'DEEP SKY';
      const heading = nextGroup !== group ? `<p class="nav-group">${nextGroup}</p>` : ''; group = nextGroup;
      return `${heading}<button class="target" data-object="${o.id}" aria-current="${o.id === state.object}"><span class="number">${String(index+1).padStart(2,'0')}</span><span>${escape(o.name)}<span class="catalog">${escape(o.target === o.name ? o.kind : o.target + ' · ' + o.kind)}</span></span></button>`;
    }).join('');
    document.querySelectorAll('[data-object]').forEach(button => button.addEventListener('click', () => { state.object = button.dataset.object; render(); }));
  }
  const cohortLabel = cohort => ({wide:"Wide stock",second:"Second stock",reducer063:"25 mm + nominal 0.63× reducer",reducer050:"25 mm + nominal 0.5× reducer"}[cohort] || data.eyepiece_planner?.eyepieces.find(p=>"upgrade_"+p.id===cohort)?.name || cohort);
  function renderCards(cohort, instruments = instrumentList()) {
    return instruments.map(instrument => {
      const c = captureFor(instrument,cohort), fixed = instrument.id === 'vortex';
      const reduction = c?.reducer || 1;
      const lens = reduction === 1 ? 'None' : `nominal ${number(reduction)}× reducer`;
      const eyepiece = fixed ? 'Fixed optics · same 8× reference' : c ? `${number(c.eyepiece_mm)} mm stock eyepiece · Lens: ${lens}` : 'Awaiting capture';
      const caution = instrument.id === 'power70' && cohort === 'second' ? '<div class="caution">30° apparent field assumed · useful detail not guaranteed at 175×</div>' : reduction !== 1 ? '<div class="caution">Idealized field only · compatibility, vignetting and focus unverified</div>' : instrument.id === 'startravel102' ? '<div class="caution">Photo eyepiece AFOV assumed 50° · color fringing is not simulated</div>' : '';
      const baseline = captureFor(instrument,'wide');
      const fieldChange = reduction !== 1 && baseline ? `<div class="field-change">Field ${number(baseline.field_of_view_deg)}° → ${number(c.field_of_view_deg)}° · ${number(1/reduction)}× wider diameter</div>` : '';
      return `<article class="card"><div class="card-top"><h4>${escape(instrument.name)}</h4><span class="tag ${instrument.owned?'':'candidate'}">${instrument.owned?'EXISTING':'COMPARE'} · ${instrument.aperture} MM</span>${instrument.mount?`<div class="mount">${escape(instrument.mount)}</div>`:""}</div>${c ? `<button class="frame" data-instrument="${instrument.id}" data-cohort="${cohort}" aria-label="Inspect ${escape(target().name)} through ${escape(instrument.name)}, ${escape(cohortLabel(cohort))}"><img src="${escape(c.image)}" alt="${escape(target().name)} through ${escape(instrument.name)}, ${number(c.magnification)} times, Bortle ${state.bortle}" loading="lazy" width="${c.width}" height="${c.height}"></button>` : '<div class="frame"><div class="pending">This capture is not available yet.</div></div>'}<div class="card-bottom"><div class="measurement"><span class="power">${c?number(c.magnification):'—'}×</span><span class="fov">${c?number(c.field_of_view_deg):'—'}° FIELD</span></div><div class="eyepiece">${eyepiece}</div>${fieldChange}${caution}</div></article>`;
    }).join('');
  }
  function render() {
    const o=target(), scene=data.scenes[o.id];
    $('object-count').textContent=String(objects.length).padStart(2,'0'); renderNav();
    $('object-kind').textContent=o.kind + (o.target===o.name?'':' / '+o.target);
    $('object-title').textContent=o.name; $('object-note').textContent=o.note;
    $('scene-details').innerHTML=scene ? `<strong>${escape(timeLabel(scene.at))}</strong><br>Target ${number(scene.target_altitude_deg)}° above horizon · Sun ${number(scene.sun_altitude_deg)}°<br>Moon ${scene.moon_altitude_deg<0?'below horizon':number(scene.moon_altitude_deg)+'° high'} · ${number(scene.moon_illumination_percent)}% illuminated<br><span class="sky-pill">${scene.sun_altitude_deg<-18?'ASTRONOMICAL NIGHT':scene.sun_altitude_deg<-6?'TWILIGHT':'BRIGHT SKY'} · BORTLE ${state.bortle}</span>` : 'Scene is awaiting capture.';
    $('wide-grid').innerHTML=renderCards('wide'); $('second-grid').innerHTML=renderCards('second');
    const maks=instrumentList().filter(i=>i.id==='mak102'||i.id==='mak127');
    $('reducer-section').hidden=maks.length===0;
    $('reducer-jump').hidden=maks.length===0;
    $('mak-baseline-grid').innerHTML=renderCards('wide',maks);
    $('reducer063-grid').innerHTML=renderCards('reducer063',maks);
    $('reducer050-grid').innerHTML=renderCards('reducer050',maks);
    $('capture-count').textContent=`${data.captures.length} original captures · PNG`;
    $('limitations').innerHTML='<ul>'+data.limitations.map(x=>`<li>${escape(x)}</li>`).join('')+'</ul>';
    document.querySelectorAll('[data-bortle]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.bortle)===state.bortle)));
    document.querySelectorAll('[data-filter]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.filter===state.filter)));
    document.querySelectorAll('[data-instrument]').forEach(b=>b.addEventListener('click',()=>openViewer(b.dataset.instrument,b.dataset.cohort)));
    document.title=`${o.name} · The eyepiece atlas`;
    document.documentElement.dataset.object=state.object;
    document.documentElement.dataset.bortle=state.bortle;
    document.documentElement.dataset.filter=state.filter;
    window.dispatchEvent(new CustomEvent("atlas:render",{detail:{object:state.object,bortle:state.bortle,filter:state.filter}}));
  }
  function openViewer(instrumentId,cohort) {
    const instrument=data.instruments.find(i=>i.id===instrumentId), c=captureFor(instrument,cohort); if(!c)return;
    state.viewer={instrumentId,cohort}; state.inspection=false;
    $('viewer-object').textContent=target().name+' / '+cohortLabel(cohort).toUpperCase();
    $('viewer-title').textContent=`${instrument.name} · ${number(c.magnification)}× · ${number(c.field_of_view_deg)}° field`;
    $('viewer-detail').textContent=`Bortle ${state.bortle} · ${timeLabel(c.scene.at)} · ${c.width} × ${c.height} original pixels${c.reducer && c.reducer!==1 ? " · IDEALIZED REDUCER: compatibility and edge illumination unverified" : ""}`;
    $('viewer-image').src=c.image; $('viewer-image').alt=`${target().name} through ${instrument.name}`;
    $('download-image').href=c.image; $('download-image').download=c.image.split('/').pop();
    const upgrade=cohort.startsWith("upgrade_");
    $("previous-image").setAttribute("aria-label",upgrade?"Previous eyepiece":"Previous instrument");
    $("next-image").setAttribute("aria-label",upgrade?"Next eyepiece":"Next instrument");
    if(upgrade) $("viewer-detail").textContent+=" · SCALE ONLY: no seeing, diffraction or brand sharpness simulation";
    setInspection(false); if(!$('viewer').open)$('viewer').showModal();
  }
  function setInspection(on) { state.inspection=on; $('viewer-image').style.setProperty('--inspection',on?4:1); $('inspect').textContent=`Center inspection: ${on?'4× crop':'off'}`; $('inspection-note').textContent=on?'4× image crop · this adds no optical detail or magnification':'Full field · optical magnification is unchanged'; }
  function moveViewer(delta) { if(!state.viewer)return; if(state.viewer.cohort.startsWith("upgrade_")){const products=data.eyepiece_planner.eyepieces,index=products.findIndex(p=>"upgrade_"+p.id===state.viewer.cohort);openViewer("mak102","upgrade_"+products[(index+delta+products.length)%products.length].id);return;} const list=instrumentList().filter(i=>captureFor(i,state.viewer.cohort)), index=list.findIndex(i=>i.id===state.viewer.instrumentId); openViewer(list[(index+delta+list.length)%list.length].id,state.viewer.cohort); }
  document.querySelectorAll('[data-bortle]').forEach(b=>b.addEventListener('click',()=>{state.bortle=Number(b.dataset.bortle);render();}));
  document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{state.filter=b.dataset.filter;render();}));
  $('close-viewer').addEventListener('click',()=>$('viewer').close());
  $('previous-image').addEventListener('click',()=>moveViewer(-1)); $('next-image').addEventListener('click',()=>moveViewer(1));
  $('inspect').addEventListener('click',()=>setInspection(!state.inspection));
  document.addEventListener('keydown',event=>{if(!$('viewer').open)return;if(event.key==='ArrowLeft'){event.preventDefault();moveViewer(-1);}if(event.key==='ArrowRight'){event.preventDefault();moveViewer(1);}});
  window.ATLAS_VIEWER={open:openViewer,selectObject:id=>{state.object=id;render();}};
  render();
})();
