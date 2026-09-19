(function(){
  function post(d){ try{ fetch('http://127.0.0.1:8899/data',{method:'POST',body:d}); }catch(e){} }
  var doc=null;
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
  doc = findDoc(document);
  if(!doc || !doc.body){ post('NODOC'); return; }

  // remaining two (吴正 already captured: reason=死亡 date=2025-03-27)
  var targets=[
    {name:'苏芳富', sno:'34080200300302880'},
    {name:'操乐成', sno:'34080200300409757'}
  ];

  function findEndingDoc(gkey){
    var t=null;
    (function walk(w,depth){
      try{
        if(depth<6 && w.location.href.indexOf('FilesEndingReason.aspx')>=0 && w.document.body){
          if(!gkey || w.location.href.indexOf(gkey)>=0) t=w;
        }
      }catch(e){}
      try{ var fs=w.frames||[]; for(var i=0;i<fs.length&&depth<6;i++) walk(fs[i],depth+1); }catch(e){}
    })(window,0);
    return t;
  }

  function readDetail(gkey, cb){
    var tries=0;
    function poll(){
      tries++;
      var w=findEndingDoc(gkey);
      if(w && w.document.body){
        try{
          var r=w.document.getElementById('ctl00_ContentPlaceHtml_sEndingReason');
          var d=w.document.getElementById('ctl00_ContentPlaceHtml_dEndingDate');
          if(r||d){ cb({reason:r?r.value:'', date:d?d.value:''}); return; }
        }catch(e){}
      }
      if(tries>35){ cb(null); return; }
      setTimeout(poll,1500);
    }
    setTimeout(poll,2500);
  }

  function process(idx){
    if(idx>=targets.length){ post('ALL_DONE'); return; }
    var t=targets[idx];
    // clear name box and type the target name (exact)
    var nb=doc.getElementById('ctl00_ContentPlaceHtml_txtPersonName');
    if(!nb){ post('NONAMEBOX'); process(idx+1); return; }
    nb.value=t.name;
    // ensure filters still: state=3 death=0
    try{ doc.getElementById('ctl00_ContentPlaceHtml_ddlState').value='3'; doc.getElementById('ctl00_ContentPlaceHtml_ddlsDeath').value='0'; }catch(e){}
    var btn=doc.getElementById('lbtnSearch');
    if(!btn){ post('NOSEARCHBTN'); process(idx+1); return; }
    btn.click();
    post('QUERY '+t.name);

    // wait for re-render, then find the row by sno and check it
    var tries2=0;
    function waitForRow(){
      tries2++;
      var boxes=doc.querySelectorAll("input[id*='chkKey']");
      var tb=null;
      for(var j=0;j<boxes.length;j++){
        if((boxes[j].getAttribute('sno')||'')===t.sno){ tb=boxes[j]; break; }
      }
      if(tb){
        // uncheck others first
        for(var i2=0;i2<boxes.length;i2++){ try{ if(boxes[i2]!==tb && boxes[i2].checked) boxes[i2].click(); }catch(e){} }
        var gkey=tb.value||'';
        try{ tb.click(); }catch(e){}
        try{ doc.defaultView.RepeaterCheckedOne && doc.defaultView.RepeaterCheckedOne(tb); }catch(e){}
        setTimeout(function(){
          var vb=doc.getElementById('ctl00_ContentPlaceHtml_lbtnViewInfo');
          if(!vb){ post('NOBTN '+t.name); process(idx+1); return; }
          try{ vb.click(); }catch(e){ post('CLICKERR '+e); process(idx+1); return; }
          readDetail(gkey, function(res){
            post(t.name+' reason='+(res?res.reason:'?')+' date='+(res?res.date:'?'));
            setTimeout(function(){ process(idx+1); }, 2500);
          });
        }, 1500);
      } else if(tries2>30){ post('ROW_NOT_FOUND '+t.name); process(idx+1); }
      else setTimeout(waitForRow, 1500);
    }
    setTimeout(waitForRow, 4000);
  }
  post('START');
  process(0);
})();
