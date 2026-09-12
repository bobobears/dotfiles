(function(){
  function post(d){ try{ fetch('http://127.0.0.1:8899/data',{method:'POST',body:d}); }catch(e){} }

  // find addTab + Pages in top doc or any frame
  var ctx=null;
  function findCtx(w){
    if(!w) return null;
    try{ if(typeof w.addTab==='function' && w.Pages) return w; }catch(e){}
    var fs=[]; try{ fs=w.frames||[]; }catch(e){}
    for(var i=0;i<fs.length;i++){ var r=findCtx(fs[i]); if(r) return r; }
    return null;
  }
  ctx = findCtx(window);
  if(!ctx){ post('NOADDTAB'); return; }

  // open the target tab (idempotent: check existing tabs first)
  var opened=false;
  try{
    function hasTab(d){
      if(!d||!d.querySelectorAll) return false;
      var ifs=d.querySelectorAll('iframe');
      for(var i=0;i<ifs.length;i++){
        var s=''; try{s=ifs[i].src||'';}catch(e){}
        if(s.indexOf('FilesTransferringList')>=0) return true;
        if(hasTab(ifs[i].contentDocument)) return true;
      }
      return false;
    }
    if(!hasTab(document)){
      ctx.addTab(ctx.Pages, '\u6863\u6848\u7ec8\u6b62\u3001\u79fb\u4ea4\u3001\u5c01\u5b58\u7ba1\u7406', '/pages/PersonInfoManagement/FilesTransferring/FilesTransferringList.aspx','');
      opened=true;
    } else { post('TAB_ALREADY_OPEN'); }
  }catch(e){ post('ADDTab_ERR '+e); return; }

  // poll for the iframe to load, then report readiness + total count text
  var tries=0;
  function findDoc(d){
    if(!d||!d.querySelectorAll) return null;
    var ifs=d.querySelectorAll('iframe');
    for(var i=0;i<ifs.length;i++){
      var s=''; try{s=ifs[i].src||'';}catch(e){}
      if(s.indexOf('FilesTransferringList')>=0){
        try{ if(ifs[i].contentDocument && ifs[i].contentDocument.readyState==='complete') return ifs[i].contentDocument; }catch(e){}
      }
      var r=findDoc(ifs[i].contentDocument); if(r) return r;
    }
    return null;
  }
  function poll(){
    tries++;
    var doc=findDoc(document);
    if(doc && doc.body){
      var total=''; try{ var m=doc.body.innerText.match(/\u663e\u793a\s*(\d+)\s*\u6761\u8bb0\u5f55/); if(m) total=m[1]; }catch(e){}
      post('TAB_READY opened='+opened+' current_total='+total);
      return;
    }
    if(tries>40){ post('TIMEOUT_FINDING_TAB'); return; }
    setTimeout(poll, 1500);
  }
  post('START opened='+opened);
  setTimeout(poll, 2000);
})();
