(function(){
  function post(d){ try{ fetch('http://127.0.0.1:8899/data',{method:'POST',body:d}); }catch(e){} }
  var out = {top:{href:location.href, title:document.title}, frames:[], addTabFound:false};
  // search for addTab in top and all frames
  function findAddTab(w, label){
    try{ if (typeof w.addTab === 'function' && w.Pages) { out.addTabFound = true; out.addTabWhere = label; } }catch(e){}
  }
  findAddTab(window,'top');
  var frs = document.querySelectorAll('iframe, frame');
  for (var i=0;i<frs.length;i++){
    try{
      var w = frs[i].contentWindow;
      out.frames.push({name:frs[i].name||frs[i].id||('#'+i), src:(frs[i].src||'').slice(0,120), href:w?w.location.href:'<no access>', title:w?w.document.title:'<no doc>'});
      findAddTab(w,'frame:'+ (frs[i].name||'#'+i));
    }catch(e){ out.frames.push({name:frs[i].name||('#'+i), src:(frs[i].src||'').slice(0,120), err:String(e).slice(0,80)}); }
  }
  // login page detection: look for captcha/verify image or login form in top doc
  var body = document.body ? document.body.innerText.slice(0,300) : '';
  out.topBodySnippet = body;
  post(JSON.stringify(out));
})();
