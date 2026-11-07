(function(){
  function post(d){ try{ fetch('http://127.0.0.1:8899/data',{method:'POST',body:d}); }catch(e){} }
  var found = [];
  function check(w, label, depth){
    if(depth > 6) return;
    try{
      if(typeof w.addTab === 'function'){
        found.push(label + ':addTab');
      }
      if(w.Pages){
        found.push(label + ':Pages');
      }
    }catch(e){}
    // check frames
    try{
      var fs = w.frames || [];
      for(var i=0;i<fs.length&&depth<6;i++){
        check(fs[i], label+'>'+(fs[i].name||'f'+i), depth+1);
      }
    }catch(e){}
  }
  check(window, 'top', 0);
  // also check all iframes in document
  try{
    var ifs = document.querySelectorAll('iframe');
    for(var i=0;i<ifs.length;i++){
      try{
        check(ifs[i].contentWindow, 'iframe['+(ifs[i].name||i)+']', 1);
      }catch(e){}
    }
  }catch(e){}
  post('ADDTAB_FOUND: ' + (found.length ? found.join(', ') : 'NONE'));
})();
