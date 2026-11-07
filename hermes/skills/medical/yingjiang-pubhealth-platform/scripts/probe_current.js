(function(){
  function post(d){ try{ fetch('http://127.0.0.1:8899/data',{method:'POST',body:d}); }catch(e){} }
  var out = {
    topHref: location.href,
    topTitle: document.title,
    frames: []
  };
  try{
    var ifs = document.querySelectorAll('iframe');
    for(var i=0;i<ifs.length;i++){
      var info = {src: (ifs[i].src||'').slice(0,150), name: ifs[i].name||ifs[i].id||('#'+i)};
      try{
        info.href = ifs[i].contentWindow.location.href;
        info.title = ifs[i].contentWindow.document.title;
      }catch(e){ info.err = String(e).slice(0,80); }
      out.frames.push(info);
    }
  }catch(e){}
  post(JSON.stringify(out));
})();
