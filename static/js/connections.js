var socket = io.connect('http://' + document.domain + ':' + location.port)
var connection_status = document.getElementById("connection-status")

function write_connection_status(msg){
  console.log("Connection: " + msg)
  connection_status.innerHTML = "Connection: " + msg
}

window.onload = function() {
  if(connected){
    document.getElementById("connect_btn").disabled = true;
    write_connection_status("connected")
  }else{
    document.getElementById("disconnect_btn").disabled = true;
    write_connection_status("not connected")
  }
};

function connect(){
  if(connected == 0){
    document.getElementById("connect_btn").disabled = true;
    document.getElementById("disconnect_btn").disabled = true;
    var addr = document.getElementById("addr_val").value
    console.log('attempting connection to:' + addr)
    write_connection_status("connecting...")
    socket.emit('server_connect', {
      action:'connect',
      addr:addr
    });
  }else{
    alert('Server is already connected, disconnect first')
  }
}

function disconnect(){
  if(connected == 1){
    console.log('attempting disconnection')
    write_connection_status("disconnecting...")
    socket.emit('server_connect', {
      action:'disconnect'
    });
  }else{
    alert('Server is already disconnected, connect it first')
  }
}

socket.on( 'connect_resopnse', function( msg ) {
  var res = Boolean(JSON.parse(msg)['response'])
  if(res){
    console.log('connected!')
    location.reload();
  }else{
    console.log('not connected!')
    write_connection_status("not connected")
    document.getElementById("connect_btn").disabled = false;
    //location.reload();
  }
})
