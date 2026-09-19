// check_services.js — 查询某死亡人员「死亡后是否还有服务记录」
// 用法: xtype.py fetch:check_services.js  (先替换下方 NAME)
// 原理: 列表页按姓名定位行 → 读该行档案号链接 onclick 里的真实 personid(可能是GUID!)
//       → Visiting(personid,name) 打开健康档案浏览器 → 遍历所有子标签提取含日期的服务记录行
(function(){
  function post(d){ try{ fetch('http://127.0.0.1:8899/data',{method:'POST',body:d}); }catch(e){} }
  var NAME='__NAME__';   // ← 改成目标姓名

  function findListDoc(){
    var d=null;
    (function walk(w,depth){
      try{ if(depth<6 && w.location.href.indexOf('FilesTransferringList.aspx')>=0 && w.document.body) d=w; }catch(e){}
      try{ var fs=w.frames||[]; for(var i=0;i<fs.length&&depth<6;i++) walk(fs[i],depth+1); }catch(e){}
    })(window,0);
    return d ? d.document : null;
  }

  // 1) 列表页按姓名精确查询(若当前已筛到终止+死亡则更快)
  var ldoc=findListDoc();
  if(!ldoc || !ldoc.body){ post('NOLIST'); return; }
  try{
    var sb=ldoc.querySelector('#ctl00_ContentPlaceHtml_txtPersonName')||ldoc.querySelector('#txtName');
    if(sb){ sb.value=NAME; sb.dispatchEvent(new Event('change',{bubbles:true})); }
    var qb=ldoc.querySelector('#lbtnSearch');
    if(qb) qb.click();
  }catch(e){ post('SEARCH_ERR '+e); }

  setTimeout(function(){
    // 2) 找含姓名的行, 读档案号链接 onclick 里的真实 personid
    var rows=ldoc.querySelectorAll('tr');
    var found=null;
    for(var i=0;i<rows.length;i++){ if((rows[i].innerText||'').indexOf(NAME)>=0){ found=rows[i]; break; } }
    if(!found){ post('ROW_NOT_FOUND '+NAME); return; }
    var as=found.querySelectorAll('a');
    var personid=null, sno=null;
    for(var j=0;j<as.length;j++){
      var oc=as[j].getAttribute('onclick')||'';
      var m=oc.match(/Visiting\('([^']+)'\s*,\s*'[^']*'\)/);
      if(m){ personid=m[1]; break; }
    }
    var chk=found.querySelector('input[type="checkbox"]');
    if(chk) sno=chk.getAttribute('sno');
    post('FOUND name='+NAME+' sno='+(sno||'?')+' personid='+(personid||'?'));
    if(!personid){ post('NO_PERSONID'); return; }

    // 3) Visiting(真实personid, 姓名) 打开健康档案浏览器
    try{ ldoc.defaultView.Visiting(personid, NAME); post('VISITING_CALLED'); }catch(e){ post('VISIT_ERR '+e); return; }

    function findSL(){
      var t=null;
      (function walk(w,depth){
        try{ if(depth<6 && w.location.href.indexOf('ShortcutsList.aspx')>=0 && w.location.href.indexOf(personid)>=0 && w.document.body) t=w; }catch(e){}
        try{ var fs=w.frames||[]; for(var i=0;i<fs.length&&depth<6;i++) walk(fs[i],depth+1); }catch(e){}
      })(window,0);
      return t;
    }

    function extractRows(idoc){
      var tables=idoc.querySelectorAll('table');
      var rows=[];
      for(var ti=0;ti<tables.length;ti++){
        var trs=tables[ti].rows||[];
        for(var ri=0;ri<trs.length;ri++){
          var cells=trs[ri].cells; if(!cells) continue;
          var row=[];
          for(var ci=0;ci<cells.length;ci++) row.push((cells[ci].innerText||'').replace(/\s+/g,' ').trim());
          var line=row.join(' | ');
          if(/\d{4}-\d{2}-\d{2}/.test(line)) rows.push(line);
        }
      }
      return rows;
    }
    function clickTab(doc, sel, name){
      var l=doc.querySelectorAll(sel);
      for(var i=0;i<l.length;i++){ if((l[i].innerText||'').replace(/\s+/g,' ').trim()===name){ try{l[i].click(); return true;}catch(e){} } }
      return false;
    }

    var tries=0;
    (function poll(){
      tries++;
      var sl=findSL();
      if(sl && sl.document.body){
        var doc=sl.document;
        var tl=doc.querySelectorAll('.headerMenu li');
        var tops=[]; for(var i=0;i<tl.length;i++) tops.push((tl[i].innerText||'').replace(/\s+/g,' ').trim());
        if(tops.length>0){
          post('READY TOPS '+JSON.stringify(tops));
          // 基本信息(含终止日期)
          var bodyTxt=doc.body.innerText||'';
          var mEnd=bodyTxt.match(/终止日期：\s*([^\n]+)/);
          if(mEnd) post('TERMINATE_DATE '+mEnd[1].trim());

          var tops2=[];
          var tl2=doc.querySelectorAll('.headerMenu li');
          for(var i=0;i<tl2.length;i++){ var t=(tl2[i].innerText||'').replace(/\s+/g,' ').trim(); if(t) tops2.push({name:t, el:tl2[i]}); }

          function processTop(idx){
            if(idx>=tops2.length){ post('ALL_DONE'); return; }
            var top=tops2[idx];
            clickTab(doc,'.headerMenu li',top.name);
            setTimeout(function(){
              var subs=[];
              var sl3=doc.querySelectorAll('.headersubMenu li');
              for(var i=0;i<sl3.length;i++){ var s=(sl3[i].innerText||'').replace(/\s+/g,' ').trim(); if(s) subs.push({name:s, el:sl3[i]}); }
              post('TOP['+top.name+'] SUBS '+JSON.stringify(subs.map(function(x){return x.name;})));
              function processSub(j){
                if(j>=subs.length){ processTop(idx+1); return; }
                var sub=subs[j];
                clickTab(doc,'.headersubMenu li',sub.name);
                setTimeout(function(){
                  var f=doc.getElementById(sub.name+'_IFrame');
                  if(!f){ post('SUB['+top.name+'/'+sub.name+'] NOIFRAME'); processSub(j+1); return; }
                  var w2=0;
                  (function waitLoad(){
                    w2++;
                    try{
                      if(f.contentDocument && f.contentDocument.body && (f.contentDocument.body.innerText||'').length>50){
                        var rows=extractRows(f.contentDocument);
                        post('SUB['+top.name+'/'+sub.name+'] ROWS('+rows.length+'): '+JSON.stringify(rows).slice(0,6000));
                        processSub(j+1);
                      } else if(w2>25){
                        var t=''; try{t=(f.contentDocument&&f.contentDocument.body)?f.contentDocument.body.innerText.slice(0,300):'';}catch(e){}
                        post('SUB['+top.name+'/'+sub.name+'] EMPTY: '+JSON.stringify(t));
                        processSub(j+1);
                      }
                    }catch(e){ post('SUB['+top.name+'/'+sub.name+'] ERR '+e); processSub(j+1); }
                  })();
                }, 4000);
              }
              if(subs.length===0){ processTop(idx+1); return; }
              processSub(0);
            }, 2500);
          }
          processTop(0);
          return;
        } else {
          if(tries===18) post('STILL_EMPTY bodylen='+(doc.body.innerText||'').length);
        }
      }
      if(tries>25){ post('SL_NOT_FOUND_OR_NO_NAV'); return; }
      setTimeout(poll,2000);
    })();
  }, 6000);
})();
