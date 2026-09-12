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

  // re-verify filter state before export (postback may have reset dropdowns visually)
  var st=doc.getElementById('ctl00_ContentPlaceHtml_ddlState');
  var de=doc.getElementById('ctl00_ContentPlaceHtml_ddlsDeath');
  post('PRE_EXPORT state='+(st?st.value:'?')+' death='+(de?de.value:'?'));

  var btn=doc.getElementById('ctl00_ContentPlaceHtml_lbtnExport');
  if(!btn){ post('NOEXPORTBTN'); return; }
  var alerts=[];
  doc.defaultView.alert=function(m){alerts.push('ALERT:'+m);};
  doc.defaultView.confirm=function(m){alerts.push('CONFIRM:'+m);return true;};
  btn.click();
  setTimeout(function(){
    post('EXPORT_CLICKED alerts='+JSON.stringify(alerts));
  }, 3000);
})();
