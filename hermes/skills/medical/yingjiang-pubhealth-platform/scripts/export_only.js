(function(){
  function post(d){ try{ fetch('http://127.0.0.1:8899/data',{method:'POST',body:d}); }catch(e){} }
  function findListDoc(){
    var d=null;
    (function walk(w2,depth){
      try{ if(depth<6 && w2.location.href.indexOf('FilesTransferringList.aspx')>=0 && w2.document.body) d=w2; }catch(e){}
      try{ var fs=w2.frames||[]; for(var i=0;i<fs.length&&depth<6;i++) walk(fs[i],depth+1); }catch(e){}
    })(window,0);
    return d ? d.document : null;
  }
  var ldoc = findListDoc();
  if(!ldoc || !ldoc.body){ post('NOLIST'); return; }
  post('LIST_FOUND');
  try{
    ldoc.defaultView.confirm = function(){ return true; };
    ldoc.defaultView.alert = function(){};
    var eb = ldoc.querySelector('#ctl00_ContentPlaceHtml_lbtnExport');
    if(eb){ eb.click(); post('EXPORT_CLICKED'); }
    else { post('NO_EXPORT_BTN'); }
  }catch(e){ post('EXPORT_ERR ' + e); }
  setTimeout(function(){ post('EXPORT_WAIT_DONE'); }, 15000);
})();
