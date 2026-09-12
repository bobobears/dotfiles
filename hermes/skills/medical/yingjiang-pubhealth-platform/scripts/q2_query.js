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

  // capture pre-query total for comparison
  var before=''; try{
    var m=doc.body.innerText.match(/\u663e\u793a\s*(\d+)\s*\u6761\u8bb0\u5f55/); // 显示N条记录
    if(m) before=m[1];
  }catch(e){}

  var st=doc.getElementById('ctl00_ContentPlaceHtml_ddlState');
  var de=doc.getElementById('ctl00_ContentPlaceHtml_ddlsDeath');
  if(!st||!de){ post('NOSELECTS'); return; }
  st.value='3';   // 档案状态: 终止
  de.value='0';   // 是否死亡: 是 (options: 否=1, 是=0)

  var btn=doc.getElementById('lbtnSearch');
  if(!btn){ post('NOSearchBtn state='+st.value+' death='+de.value); return; }
  btn.click();
  post('QUERY_CLICKED before_total='+before+' state='+st.value+' death='+de.value);

  // poll for the new total (page re-renders after postback)
  var tries=0, lastTotal='';
  function poll(){
    tries++;
    try{
      var m2=doc.body.innerText.match(/\u663e\u793a\s*(\d+)\s*\u6761\u8bb0\u5f55/);
      if(m2 && m2[1]!==lastTotal){ lastTotal=m2[1]; }
    }catch(e){}
    var sample='';
    try{
      var rows=doc.querySelectorAll('table tr');
      var cnt=0;
      for(var i=0;i<rows.length && cnt<3;i++){
        var t=(rows[i].innerText||'').replace(/\s+/g,' ').trim();
        if(t.indexOf('\u6863\u6848\u7f16\u53f7')>=0) continue; // header
        if(t.length>20){ sample+=t.slice(0,90)+' || '; cnt++; }
      }
    }catch(e){}
    if((lastTotal && lastTotal!==before) || tries>40){
      post('RESULT total='+lastTotal+' (was '+before+') rows_sample: '+sample);
      return;
    }
    setTimeout(poll, 1500);
  }
  setTimeout(poll, 3000);
})();
