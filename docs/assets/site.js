(function(){
  // ---- filtros da home ----
  var form=document.getElementById("filters"), grid=document.getElementById("grid");
  if(form&&grid){
    var cards=[].slice.call(grid.children), count=document.getElementById("count"), none=document.getElementById("none");
    function apply(){
      var f=new FormData(form), reg=f.get("regiao"), q=+f.get("quartos"), v=f.get("valor"), ord=f.get("ord");
      var lo=0,hi=Infinity; if(v){var p=v.split("-");lo=+p[0]||0;hi=p[1]?+p[1]:Infinity}
      var vis=cards.filter(function(c){
        var val=+c.dataset.valor, ok=(!reg||c.dataset.regiao===reg)&&(+c.dataset.quartos>=q);
        if(v) ok=ok&&val>0&&val>=lo&&val<hi;
        c.hidden=!ok; return ok});
      var sorted=cards.slice().sort(function(a,b){
        if(ord==="vmenor") return (+a.dataset.valor||9e12)-(+b.dataset.valor||9e12);
        if(ord==="vmaior") return (+b.dataset.valor)-(+a.dataset.valor);
        if(ord==="area") return (+b.dataset.area)-(+a.dataset.area);
        return 0});
      sorted.forEach(function(c){grid.appendChild(c)});
      count.textContent=vis.length+(vis.length===1?" imóvel":" imóveis");
      none.hidden=vis.length>0;
    }
    form.addEventListener("change",apply);
    document.querySelectorAll("[data-goreg]").forEach(function(a){a.addEventListener("click",function(){
      var s=form.elements.regiao, val=a.dataset.goreg;
      var opt=[].slice.call(s.options).find(function(o){return o.value===val||o.value.indexOf(val.split(" ")[0])===0});
      s.value=opt?opt.value:""; apply();
    })});
  }
  // ---- galeria do imóvel ----
  var gal=document.getElementById("gal"), lb=document.getElementById("lb");
  if(gal&&lb){
    var fotos=JSON.parse(gal.dataset.fotos), main=gal.querySelector(".gal-main img"), ths=gal.querySelectorAll(".th"), cur=0;
    var img=lb.querySelector("img"), cap=lb.querySelector(".lb-c");
    function sel(i){cur=(i+fotos.length)%fotos.length; main.src=fotos[cur]; gal.querySelector(".gal-main").dataset.i=cur;
      ths.forEach(function(t,k){t.classList.toggle("on",k===cur)}); if(!lb.hidden){img.src=fotos[cur];cap.textContent=(cur+1)+" / "+fotos.length}}
    function open(){lb.hidden=false; img.src=fotos[cur]; cap.textContent=(cur+1)+" / "+fotos.length; document.body.style.overflow="hidden"}
    function close(){lb.hidden=true; document.body.style.overflow=""}
    ths.forEach(function(t){t.addEventListener("click",function(){sel(+t.dataset.i)})});
    gal.querySelector(".gal-main").addEventListener("click",open);
    lb.querySelector(".lb-x").addEventListener("click",close);
    lb.querySelector(".lb-p").addEventListener("click",function(){sel(cur-1)});
    lb.querySelector(".lb-n").addEventListener("click",function(){sel(cur+1)});
    lb.addEventListener("click",function(e){if(e.target===lb)close()});
    document.addEventListener("keydown",function(e){if(lb.hidden)return; if(e.key==="Escape")close(); if(e.key==="ArrowLeft")sel(cur-1); if(e.key==="ArrowRight")sel(cur+1)});
    var x0=null; lb.addEventListener("touchstart",function(e){x0=e.touches[0].clientX},{passive:true});
    lb.addEventListener("touchend",function(e){if(x0===null)return; var dx=e.changedTouches[0].clientX-x0; if(Math.abs(dx)>40) sel(cur+(dx<0?1:-1)); x0=null});
    sel(0);
  }
})();
