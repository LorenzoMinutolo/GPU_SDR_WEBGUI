var socket = io.connect('http://' + document.domain + ':' + location.port);

function request_jobs_update(){
  //console.log('requesting jobs update...')
  socket.emit('jobs_update', {
    update:true
  });
}

function request_measure_update(){
  //console.log('requesting measure update...')
  socket.emit('measure_update', {
    update:true
  });
}

var interval_update_jobs = setInterval(request_jobs_update, 1000);
var interval_update_measure = setInterval(request_measure_update, 731);

socket.emit('clear_context', {});
socket.on( 'clear_context', function( msg ) {
  var info = JSON.parse(msg)
  if (parseInt(info['clear'])){
    console.log("WARNING: clearing context")
    localStorage.clear();
  }
})


socket.on( 'analysis_complete', function( msg ) {
  var info = JSON.parse(msg)
  alertify.message('Analysis job complete<br>'+info['name']);
})


// NOTIFICATIONS must be persistent across multiple pages

if (localStorage.getItem("notification_expired") !== null) {
  var notification_expired = JSON.parse(localStorage.getItem("notification_expired").split(" "));
}else{
  var notification_expired = ["none",];
  localStorage.setItem("notification_expired", JSON.stringify(notification_expired));
}

function update_local_storage(name){
  notification_expired.push(name)
  localStorage.setItem("notification_expired", JSON.stringify(notification_expired));
}

socket.on( 'update_job_resopnse', function( msg ) {
  //console.log('receiving response...')

  var notify = false

  if (typeof(disable_notifications) == 'undefined') {
    notify = true
  }else{
    notify = !disable_notifications
  }
  console.log(notification_expired)
  //console.log('notify: '+notify)
  var info = JSON.parse(msg)
  if(notify){
    //console.log(info)
    for (i = 0; i < info.length; i++) {
      if(!notification_expired.includes(info[i]['name'])){
        //console.log(info[i])
        if (info[i]['status'] !== 'failed'){
          //console.log(info[i]['status'])
          var msg = alertify.success('<b>Analysis job compelte</b><br>'+info[i]['name']);
        }else{
          var msg = alertify.error('<b>Analysis job failed</b><br>'+info[i]['name']);
        }
        msg.delay(0);
        update_local_storage(info[i]['name'])
      }
    }
  }else{
    for (i = 0; i < info.length; i++) {
      if(notification_expired.indexOf(info[i]['name']) == -1){
        notification_expired.push(info[i]['name'])
      }
    }
  }

})
