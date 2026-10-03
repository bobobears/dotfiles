(function(){
  function post(d){ try{ fetch('http://127.0.0.1:8899/data',{method:'POST',body:d}); }catch(e){} }
  try{
    fetch('http://127.0.0.1:8899/gdd_bao.js').then(function(r){
      post('FETCH_STATUS '+r.status);
      return r.text();
    }).then(function(t){
      post('FETCH_LEN '+t.length+' HEAD '+t.slice(0,60).replace(/\n/g,'\\n'));
    }).catch(function(e){ post('FETCH_ERR '+e); });
  }catch(e){ post('OUTER_ERR '+e); }
})();
