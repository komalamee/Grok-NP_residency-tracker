// Nomad Pro dashboard: tabs, tax-year switch, hover tips, line-chart guide, day-log filter. No network calls.
(function(){
function sel(kind,val){
  document.querySelectorAll('button.'+kind).forEach(function(b){b.classList.toggle('on',b.dataset.v===val);b.setAttribute('aria-selected',b.dataset.v===val);});
  document.querySelectorAll(kind==='ty'?'.year':'.view').forEach(function(e){e.classList.toggle('on',e.dataset.v===val);});
  if(kind==='tab'){try{history.replaceState(null,'','#'+val);}catch(e){}}
}
window.sel=sel;
document.querySelectorAll('button.ty').forEach(function(b){b.onclick=function(){sel('ty',b.dataset.v);};});
document.querySelectorAll('button.tab').forEach(function(b){b.onclick=function(){sel('tab',b.dataset.v);window.scrollTo({top:0});};});
document.querySelectorAll('[data-go]').forEach(function(b){b.onclick=function(){sel('tab',b.dataset.go);window.scrollTo({top:0});};});
var h=location.hash.slice(1).split('&');
h.forEach(function(p){
  if(document.querySelector("button.tab[data-v='"+p+"']"))sel('tab',p);
  var y=p.replace('ty=','').replace('-','/');
  if(p.indexOf('ty=')===0&&document.querySelector("button.ty[data-v='"+y+"']"))sel('ty',y);
});
var tip=document.createElement('div');tip.id='tip';document.body.appendChild(tip);
function place(e){var x=e.clientX+14,y=e.clientY+16,w=tip.offsetWidth,hh=tip.offsetHeight;
  if(x+w>innerWidth-8)x=e.clientX-w-14;if(y+hh>innerHeight-8)y=e.clientY-hh-14;tip.style.left=Math.max(8,x)+'px';tip.style.top=Math.max(8,y)+'px';}
function show(t,e){tip.textContent=t;tip.classList.add('on');place(e);}
function hide(){tip.classList.remove('on');}
document.addEventListener('mousemove',function(e){
  var hv=e.target.closest&&e.target.closest('svg.hov');
  if(hv){hover(hv,e);return;}
  var t=e.target.closest&&e.target.closest('[data-tip]');
  if(t)show(t.getAttribute('data-tip'),e);else hide();
});
document.addEventListener('click',function(e){var t=e.target.closest&&e.target.closest('[data-tip]');if(t&&!e.target.closest('a,button,summary'))show(t.getAttribute('data-tip'),e);else if(!e.target.closest('svg.hov'))hide();});
function hover(svg,e){
  var r=svg.getBoundingClientRect(),W=+svg.dataset.w,x=(e.clientX-r.left)/r.width*W,x0=+svg.dataset.x0,x1=+svg.dataset.x1;
  var L=svg._l||(svg._l=JSON.parse(svg.dataset.l)),V=svg._v||(svg._v=JSON.parse(svg.dataset.v));
  var n=V.length,i=Math.round((x-x0)/(x1-x0)*(n-1));
  var g=svg.querySelector('.guide'),d=svg.querySelector('.gdot');
  if(i<0||i>=n){hide();g.setAttribute('opacity',0);d.setAttribute('opacity',0);return;}
  var gx=x0+(x1-x0)*i/Math.max(n-1,1);g.setAttribute('x1',gx);g.setAttribute('x2',gx);g.setAttribute('opacity',.4);
  d.setAttribute('opacity',0);
  show(L[i]+' · '+svg.dataset.fmt.replace('{v}',V[i]),e);
}
document.addEventListener('touchstart',function(e){var hv=e.target.closest&&e.target.closest('svg.hov');if(hv&&e.touches[0])hover(hv,e.touches[0]);},{passive:true});
window.filt=function(i){var q=i.value.toLowerCase();i.closest('section').querySelectorAll('table.dl tr').forEach(function(r,n){if(n)r.style.display=r.textContent.toLowerCase().indexOf(q)>-1?'':'none';});};
})();
