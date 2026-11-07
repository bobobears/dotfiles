// open_and_check.js — 自包含版：打开列表页 + 查询 + 健康档案遍历，一次跑完
// 用法: xtype.py js open_and_check.js  (先替换下方 NAME)
// 与 check_services.js 的区别：先 addTab 打开 FilesTransferringList，不依赖浏览器当前页面状态
(function(){
  function post(d){ try{ fetch('http://127.0.0.1:8899/data',{method:'POST',body:d}); }catch(e){} }
  var NAME = '__NAME__';   // ← 改成目标姓名

  var w = window;
  if (typeof w.addTab !== 'function') {
    post('NO_ADDTAB typeof=' + typeof w.addTab);
    return;
  }

  try {
    w.addTab(Pages, '档案终止、移交、封存管理', '/pages/PersonInfoManagement/FilesTransferring/FilesTransferringList.aspx', '');
    post('TAB_OPENED');
  } catch(e) {
    post('TAB_ERR ' + e);
  }

  // 等列表页加载
  setTimeout(function(){
    post('TAB_READY');

    function findListDoc(){
      var d=null;
      (function walk(w2,depth){
        try{ if(depth<6 && w2.location.href.indexOf('FilesTransferringList.aspx')>=0 && w2.document.body) d=w2; }catch(e){}
        try{ var fs=w2.frames||[]; for(var i=0;i<fs.length&&depth<6;i++) walk(fs[i],depth+1); }catch(e){}
      })(window,0);
      return d ? d.document : null;
    }

    var ldoc = findListDoc();
    if(!ldoc || !ldoc.body){ post('NOLIST after open'); return; }
    post('LIST_FOUND');

    // 设置筛选条件：终止+死亡
    try{
      var ddlState = ldoc.querySelector('#ctl00_ContentPlaceHtml_ddlState');
      var ddlsDeath = ldoc.querySelector('#ctl00_ContentPlaceHtml_ddlsDeath');
      var sb = ldoc.querySelector('#ctl00_ContentPlaceHtml_txtPersonName');
      if(ddlState) ddlState.value = '3';
      if(ddlsDeath) ddlsDeath.value = '0';
      if(sb) sb.value = NAME;
      post('FILTERS_SET state=' + (ddlState?ddlState.value:'?') + ' death=' + (ddlsDeath?ddlsDeath.value:'?') + ' name=' + (sb?sb.value:'?'));
      var qb = ldoc.querySelector('#lbtnSearch');
      if(qb) qb.click();
      post('QUERY_CLICKED');
    }catch(e){ post('SEARCH_ERR ' + e); }

    // 等查询 postback 完成
    setTimeout(function(){
      var rows = ldoc.querySelectorAll('tr');
      var found = null;
      for(var i=0;i<rows.length;i++){
        if((rows[i].innerText||'').indexOf(NAME)>=0){ found=rows[i]; break; }
      }
      if(!found){ post('ROW_NOT_FOUND ' + NAME + ' rows=' + rows.length); return; }

      var as = found.querySelectorAll('a');
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

      try{ ldoc.defaultView.Visiting(personid, NAME); post('VISITING_CALLED'); }
      catch(e){ post('VISIT_ERR ' + e); return; }

      function findSL(){
        var t=null;
        (function walk(w2,depth){
          try{ if(depth<6 && w2.location.href.indexOf('ShortcutsList.aspx')>=0 && w2.location.href.indexOf(personid)>=0 && w2.document.body) t=w2; }catch(e){}
          try{ var fs=w2.frames||[]; for(var i=0;i<fs.length&&depth<6;i++) walk(fs[i],depth+1); }catch(e){}
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
        for(var i=0;i<l.length;i++){
          if((l[i].innerText||'').replace(/\s+/g,' ').trim()===name){
            try{l[i].click(); return true;}catch(e){}
          }
        }
        return false;
      }

      var tries=0;
      (function poll(){
        tries++;
        var sl=findSL();
        if(sl && sl.document.body){
          var doc=sl.document;
          var tl=doc.querySelectorAll('.headerMenu li');
          var tops=[];
          for(var i=0;i<tl.length;i++) tops.push((tl[i].innerText||'').replace(/\s+/g,' ').trim());
          if(tops.length>0){
            post('READY TOPS ' + JSON.stringify(tops));
            var bodyTxt=doc.body.innerText||'';
            var mEnd=bodyTxt.match(/终止日期：\s*([^\n]+)/);
            if(mEnd) post('TERMINATE_DATE ' + mEnd[1].trim());

            var tops2=[];
            for(var i=0;i<tops.length;i++) tops2.push({name:tops[i]});

            function processTop(idx){
              if(idx>=tops2.length){ post('ALL_DONE'); return; }
              var top=tops2[idx];
              clickTab(doc,'.headerMenu li',top.name);
              setTimeout(function(){
                var subs=[];
                var sl3=doc.querySelectorAll('.headersubMenu li');
                for(var i=0;i<sl3.length;i++){
                  var s=(sl3[i].innerText||'').replace(/\s+/g,' ').trim();
                  if(s) subs.push({name:s});
                }
                post('TOP['+top.name+'] SUBS ' + JSON.stringify(subs.map(function(x){return x.name;})));
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
                          post('SUB['+top.name+'/'+sub.name+'] ROWS('+rows.length+'): ' + JSON.stringify(rows).slice(0,6000));
                          processSub(j+1);
                        } else if(w2>25){
                          var t='';
                          try{t=(f.contentDocument&&f.contentDocument.body)?f.contentDocument.body.innerText.slice(0,300):'';}catch(e){}
                          post('SUB['+top.name+'/'+sub.name+'] EMPTY: ' + JSON.stringify(t));
                          processSub(j+1);
                        }
                      }catch(e){ post('SUB['+top.name+'/'+sub.name+'] ERR ' + e); processSub(j+1); }
                    })();
                  }, 4000);
                }
                if(subs.length===0){ processTop(idx+1); return; }
                processSub(0);
              }, 2500);
            }
            processTop(0);
            return;
          }
        }
        if(tries>25){ post('SL_NOT_FOUND_OR_NO_NAV'); return; }
        setTimeout(poll,2000);
      })();
    }, 6000);
  }, 8000);
})();
