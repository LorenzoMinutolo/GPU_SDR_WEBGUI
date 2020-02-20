var socket = io.connect('http://' + document.domain + ':' + location.port);
// I can use this method because the server backend has a lock

var old_job_table = [{"":0}]
var old_meas_table = [{"":0}]

var disable_notifications = true

jQuery(document).ready(function(){
    $("#submit_button_worker").click(function(){
    $("#modal_add_worker").modal();
  });
});

function disable_worker(btn){
  socket.emit('worker_action', {
    remove_:btn.value
  });
}

function add_worker(){
  var worker_n = parseInt(document.getElementById("number_tag").value);
  var worker_name = document.getElementById("name_tag").value;
  if(Number.isInteger(worker_n)){
    socket.emit('worker_action', {
      add_:worker_n,
      name_:worker_name
    });
  } else {
    alert("Invalid worker number");
  }
}

socket.on( 'deletion_respone', function( msg ) {
  var res = Boolean(JSON.parse(msg)['response'])
  if(res){
    location.reload();
  }else{
    alert("Cannot delete worker")
  }
})

socket.on( 'creation_respone', function( msg ) {
  var res = Boolean(JSON.parse(msg)['response'])
  if(res){
    location.reload();
  }else{
    alert("Cannot create workers")
  }
})

function array2string(arr){
  var str = "x"
  iterator = arr.values();
  for (const value of iterator) {
    str += JSON.stringify(value)
  }
  return str;
}

function clear_terminated_jobs(){
  socket.emit('clear_terminated_jobs', {});
}

function loadTable_jobs(tableId, fields, data) {
    var rows = '';
    $.each(data, function(index, item) {

        if (item['status'] == 'finished'){
          var row = '<tr class="success">';
        }else if(item['status'] == 'queued'){
          var row = '<tr class="secondary>';
        }else if(item['status'] == 'failed'){
          var row = '<tr class="danger">';
        }else{
          var row = '<tr>';
        }
        $.each(fields, function(index, field) {
              row += '<td>' + item[field+''] + '</td>';
        });
        rows += row + '<tr>';
    });
    $('#' + tableId).html(rows);
}

function loadTable_measure(tableId, fields, data) {
    //$ TODO: add color for different status
    var rows = '';
    $.each(data, function(index, item) {

        if (item['status'] == 'finished'){
          var row = '<tr class="success">';
        }else if(item['status'] == 'queued'){
          var row = '<tr class="secondary>';
        }else if(item['status'] == 'failed'){
          var row = '<tr class="danger">';
        }else{
          var row = '<tr>';
        }
        $.each(fields, function(index, field) {
          if(field+'' == 'progress'){
            row += '<td>' + '<div class="progress-bar progress-bar-info progress-bar-striped" role="progressbar" aria-valuenow="' + item[field]*100 + '" aria-valuemin="0" aria-valuemax="100" style="width:'+item[field]*100 +'%">'
            row += (item[field]*100).toFixed(2) + '%'
            row += '</td>' + '</div>'
          }else{
              row += '<td>' + item[field+''] + '</td>';
          }
        });
        rows += row + '<tr>';
    });
    $('#' + tableId).html(rows);
}

socket.on( 'update_job_resopnse', function( msg ) {
  //console.log('jobs Update received')
  var res = JSON.parse(msg)
  if(array2string(old_job_table).localeCompare(array2string(res)) == 0){
    //console.log("identical json jobs")
    //pass
  }else{
    //console.log(array2string(old_job_table))
    //console.log(array2string(res))
    loadTable_jobs("job_table_id", ['name','status','started','enqueued'], res)
    old_job_table = res
  }
})

socket.on( 'update_measure_resopnse', function( msg ) {
//console.log('measure Update received')
  var measures = JSON.parse(msg)
  if(array2string(old_meas_table).localeCompare(array2string(measures)) == 0 ){
    //console.log("identical measure jobs")
  }else{
    //console.log(array2string(old_meas_table))
    //console.log(array2string(measures))
    loadTable_measure("meas_table_id", ['name','author','status','progress','errors','started','enqueued'], measures)
    old_meas_table = measures
  }
})

socket.on('connect',function() {
  //console.log('First connection, fetching jobs');
  request_jobs_update();
  request_measure_update();
});
