(function(){
  function post(d){ try{ fetch('http://127.0.0.1:8899/data',{method:'POST',body:d}); }catch(e){} }

  // Step 1: 确保 addTab 可用
  var w = window;
  if (typeof w.addTab !== 'function') {
    post('NO_ADDTAB typeof=' + typeof w.addTab);
    return;
  }

  // Step 2: 打开列表页
  try {
    w.addTab(Pages, '档案终止、移交、封存管理', '/pages/PersonInfoManagement/FilesTransferring/FilesTransferringList.aspx', '');
    post('TAB_OPENED');
  } catch(e) {
    post('TAB_ERR ' + e);
  }

  // Step 3: 等列表页加载（8s）
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

    // Step 4: 设置筛选条件：终止(3) + 死亡(0) + 清空姓名
    try{
      var ddlState = ldoc.querySelector('#ctl00_ContentPlaceHtml_ddlState');
      var ddlsDeath = ldoc.querySelector('#ctl00_ContentPlaceHtml_ddlsDeath');
      var sb = ldoc.querySelector('#ctl00_ContentPlaceHtml_txtPersonName');
      if(ddlState) ddlState.value = '3';
      if(ddlsDeath) ddlsDeath.value = '0';
      if(sb) sb.value = '';
      post('FILTERS_SET state=' + (ddlState?ddlState.value:'?') + ' death=' + (ddlsDeath?ddlsDeath.value:'?') + ' name=' + (sb?sb.value:'?'));

      // Step 5: 点查询
      var qb = ldoc.querySelector('#lbtnSearch');
      if(qb) qb.click();
      post('QUERY_CLICKED');
    }catch(e){ post('SEARCH_ERR ' + e); }

    // Step 6: 等 postback 完成，然后点导出
    setTimeout(function(){
      var bodyTxt = ldoc.body.innerText || '';
      var m = bodyTxt.match(/(\d+)\s*条记录/);
      var total = m ? m[1] : '?';
      post('QUERY_DONE total=' + total);

      // 点导出按钮
      try{
        ldoc.defaultView.confirm = function(){ return true; };
        ldoc.defaultView.alert = function(){};
        var eb = ldoc.querySelector('#ctl00_ContentPlaceHtml_lbtnExport');
        if(eb){ eb.click(); post('EXPORT_CLICKED'); }
        else { post('NO_EXPORT_BTN'); }
      }catch(e){ post('EXPORT_ERR ' + e); }

      // Step 7: 等下载完成
      setTimeout(function(){ post('EXPORT_WAIT_DONE'); }, 15000);
    }, 8000);
  }, 8000);
})();
