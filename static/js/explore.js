var socket = io.connect('http://' + document.domain + ':' + location.port);
var selected_files_list = document.getElementById("selected_files_list")

$(document).ready(function(){
  console.log("loaded");
  request_update_selected_files()
});

function request_update_selected_files(){
  socket.emit('request_selection', {});
}

socket.on( 'update_selection', function( msg ) {
  if(parseInt(JSON.parse(msg)['err'])!=1){
    alert("Error: cannot add a file twice in present implementation")
  }
  console.log(JSON.parse(msg)['files'].join(", "))
  var file_list = JSON.parse(msg)['files']
  var text = ""
  for (i = 0; i < file_list.length; i++) {
    text += "<tr>" +"<th scope=\"row\">"+ i +"</th>" + "<th>" + file_list[i] + "</th>" + "</tr>";
  }
  document.getElementById('selected_files_list').innerHTML = text
})

function selected_file_op(chk){
  console.log("Operating on selection...");
  if (chk.checked == false){
    socket.emit('remove_from_selection', {
      file:chk.value
    });
  }else{
    socket.emit('add_to_selection', {
      file:chk.value
    });
  }
}

function add_folder_op(chk){
  console.log("Operating on selection from folder...");
  console.log(chk.value);
  console.log(currenpath);
  socket.emit('add_to_selection_from_folder', {
    folder:chk.value,
    path:currenpath
  });
}
function clear_selected(){
  console.log("Clearing selected files");
  socket.emit('explore_clear_selection', {});
  location.reload();
}

function config_single_analysis_headers(jdict){
  for (var key in jdict) {
    if (jdict.hasOwnProperty(key)) {
      if (parseInt(jdict[key]['available'])){

        //fill file table
        var text = ''
        for (i = 0; i < jdict[key]['files'].length; i++) {
          text += "<tr> <td>" + i + "</td> <td>"+ jdict[key]['files'][i] + "</td> <td>"+ jdict[key]['paths'][i] + "</td> </tr>";
        }
        document.getElementById(key+'-analysis-files').innerHTML = text

        //header
        document.getElementById(key+'-analysis-header').innerHTML = "files: "+jdict[key]['files'].length

      }else{

        //header
        document.getElementById(key+'-analysis-header').innerHTML = "<span class=\"glyphicon glyphicon-remove\"></span>"

        //disable file tab
        document.getElementById(key+'-files').style["display"] = "none"

        //display failure message
        document.getElementById(key+'-analysis-body').innerHTML = jdict[key]['reason']

      }
    }
  }
}


socket.on( 'analyze_config_modal', function( msg ) {
  //apply the configuration
  var config = JSON.parse(msg)
  console.log(config)
  config_single_analysis_headers(config['single'])

  //finally activate the modal
  $('#analysis-modal').modal('show');
})

function configure_analyze_modal() {
  //request configuration of the modal, no needs of sending the file list as it's server managed
  socket.emit('analysis_modal_config', {});
}
