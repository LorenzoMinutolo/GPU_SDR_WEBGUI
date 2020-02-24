var coll = document.getElementsByClassName("collapsible");
var goodNumber = /^(\+|-)?((\d+(\.\d+)?)|(\.\d+))$/
var goodPrefix = /^(\+|-)?((\d*(\.?\d*)?)|(\.\d*))$/
var i;
for (i = 0; i < coll.length; i++) {
  coll[i].addEventListener("click", function() {
    this.classList.toggle("active");
    var content = this.nextElementSibling;
    if (content.style.maxHeight){
      content.style.maxHeight = null;
    } else {
      content.style.maxHeight = content.scrollHeight + "px";
    }
  });
}

$('input')
.data("oldValue",'')
.bind('input propertychange', function() {
  var $this = $(this);
  var newValue = $this.val();
  if ( !goodPrefix.test(newValue) )
  return $this.val($this.data('oldValue'));
  set_resolution()
  if ( goodNumber.test(newValue) )
  $this.removeClass("redborder");
  else
  $this.addClass("redborder");
  set_resolution()
  return $this.data('oldValue',newValue)
});

function disable_all(){
  document.getElementById('start_F').disabled = true
  document.getElementById('scan_time').disabled = true
  document.getElementById('end_F').disabled = true
  document.getElementById('central_F').disabled = true
  document.getElementById('N_points').disabled = true
  document.getElementById('pass').disabled = true
  document.getElementById('rate').disabled = true
  document.getElementById('decim').disabled = true
  document.getElementById('amp').disabled = true
  document.getElementById('tx_gain').disabled = true
  document.getElementById('rx_gain').disabled = true
}

function enable_all(){
  document.getElementById('start_F').disabled = false
  document.getElementById('scan_time').disabled = false
  document.getElementById('end_F').disabled = false
  document.getElementById('central_F').disabled = false
  document.getElementById('N_points').disabled = false
  document.getElementById('pass').disabled = false
  document.getElementById('rate').disabled = false
  document.getElementById('decim').disabled = false
  document.getElementById('amp').disabled = false
  document.getElementById('tx_gain').disabled = false
  document.getElementById('rx_gain').disabled = false
}

function set_resolution(){
  var reso = 1e6*Math.abs(document.getElementById('start_F').value - document.getElementById('end_F').value)/parseFloat(document.getElementById('N_points').value)
  unit_string = ''
  if (reso >= 1e6){
    unit_string = 'MHz'
    reso = parseFloat(reso)/1e6
  } else if(reso >= 1000){
    unit_string = 'kHz'
    reso = parseFloat(reso)/1000.0
  }else{
    unit_string = 'Hz'
  }
  if (isNaN(reso) == true){
    document.getElementById('resolution_display').innerHTML = "Resolution: --"
  }else{
    document.getElementById('resolution_display').innerHTML = "Resolution: "+reso.toFixed(2)+' '+unit_string;
  }
  var power = -6 //should be taken by socket... in future
  var tones = document.getElementById('amp').value
  var gain = document.getElementById('tx_gain').value
  if (gain.toString().length != 0){
    power = power + parseFloat(gain)
  }
  if (tones.toString().length != 0){
    var tone_compensation = - 20.0*Math.log10(tones)
    power = power + parseFloat(tone_compensation)
  }
  document.getElementById('resolution_display').innerHTML = document.getElementById('resolution_display').innerHTML + '<br>Scan power' + power.toFixed(1)+ ' dBm'
}

function get_variables(){
  var start_F = document.getElementById('start_F').value
  if (start_F.toString().length == 0){
    alert("Start frequency must be set")
    return
  }
  var scan_time = document.getElementById('scan_time').value
  if (start_F.toString().length == 0){
    alert("Scan time must be set")
    return
  }
  var end_F = document.getElementById('end_F').value
  if (end_F.toString().length == 0){
    alert("End frequency must be set")
    return
  }
  var central_F = document.getElementById('central_F').value
  if (central_F.toString().length == 0){
    alert("Central frequency must be set")
    return
  }
  var N_points = document.getElementById('N_points').value
  if (N_points.toString().length == 0){
    alert("Number of points must be set")
    return
  }
  var tx_gain = document.getElementById('tx_gain').value
  if (tx_gain.toString().length == 0){
    alert("Transmission gain must be set")
    return
  }
  var pass = document.getElementById('pass').value
  if (pass.toString().length == 0){
    pass = 1
  }
  var rate = document.getElementById('rate').value
  if (rate.toString().length == 0){
    rate = "default"
  }
  var decim = document.getElementById('decim').value
  if (decim.toString().length == 0){
    decim = "default"
  }
  var amp = document.getElementById('amp').value
  if (amp.toString().length == 0){
    amp = "default"
  }
  var rx_gain = document.getElementById('rx_gain').value
  if (rx_gain.toString().length == 0){
    rx_gain = "default"
  }
  var socket = io.connect('http://' + document.domain + ':' + location.port);
  socket.emit('vna_param', {
    'start_F': parseFloat(start_F),
    'end_F':parseFloat(end_F),
    'central_F':parseFloat(central_F),
    'N_points':parseInt(N_points),
    'tx_gain':parseFloat(tx_gain),
    'pass':parseInt(pass),
    'rate':parseInt(rate),
    'decim':parseInt(decim),
    'amp':parseFloat(amp),
    'scan_time':parseFloat(scan_time)
  });
  disable_all()
}

var socket = io.connect('http://' + document.domain + ':' + location.port);
var modal_connection = document.getElementById("connection-modal-alert");
socket.on('vna_response', function(msg) {
  var connected = JSON.parse(msg)['connected']
  if (connected){
    console.log("GPU server is connected")
  }else{
    $('#connection-modal-alert').modal('show');
    enable_all();
  }
})


function createFunction(string) {
  string = string.replace(/<(script|\/script).*?>/g,'');
  var elem = document.getElementById("vna_plot");
  var script = document.createElement('script');
  script.innerHTML = string;
  elem.appendChild(script);
}

$(document).ready(function(){
  if(true){
    console.log("ready!");
  }
});
