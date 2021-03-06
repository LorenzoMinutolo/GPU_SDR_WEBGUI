var socket = io.connect('http://' + document.domain + ':' + location.port);
var selected_files_list = document.getElementById("selected_files_list")

jQuery(document).ready(function(){
  console.log("loading selecte files from database...");
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
  file_list = JSON.parse(msg)['files']
  var text = ""

  for (i = 0; i < file_list.length; i++) {
    text += "<tr>" +"<th scope=\"row\">"+ i +"</th>" + "<th>" + file_list[i] + "</th>" + "</tr>";
  }

  document.getElementById('selected_files_list').innerHTML = text
  document.getElementById('selected-files-btn').value = "Selected files (" + file_list.length + ")"
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



function config_excluded_files(jdict){
  var text = ''
  for (i = 0; i < jdict['excluded_files'].length; i++) {
    text += "<tr> <td>" + i + "</td> <td>"+ jdict['excluded_files'][i] + "</td> <td>"+ jdict['excluded_paths'][i] + "</td> ";
    text += "<td>" + jdict['exclusion_reason'][i]+ "</td> </tr>"

  }
  document.getElementById('exclusion-analysis-files').innerHTML = text
  document.getElementById('exclusion-analysis-header').innerHTML = "files: "+jdict['excluded_files'].length
}

function config_single_analysis_headers(jdict){
  for (var key in jdict) {
    if (jdict.hasOwnProperty(key)) {
      if (parseInt(jdict[key]['available'])){
        //fill file table
        var text = ''
        for (i = 0; i < jdict[key]['files'].length; i++) {
          text += "<tr> <td>" + i + "</td> <td>"+ jdict[key]['files'][i] + "</td> <td>"+ jdict[key]['paths'][i] + "</td> ";
          text += "<td>"
          if(jdict[key]['override'][i]){
            text += "<span class=\"glyphicon glyphicon-ok\"></span>"
          }else{
            text += "<span class=\"glyphicon glyphicon-remove\"></span>"
          }
          text += "</td> </tr>"
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
        //uncheckable item
        document.getElementById(key+'-analysis-chk').disabled = true
      }
    }
  }
}


socket.on( 'analyze_config_modal', function( msg ) {
  //apply the configuration
  analysis_config = JSON.parse(msg)
  //console.log(config)
  config_excluded_files(analysis_config)
  config_single_analysis_headers(analysis_config['single'])

  //finally activate the modal
  setTimeout(function(){
    jQuery('#analysis-modal').modal('show');
  }, 300)

})

function configure_analyze_modal() {
  //request configuration of the modal, no needs of sending the file list as it's server managed
  socket.emit('analysis_modal_config', {});
}

function diasble_init_fit_panel(sel){
  // Manage the fit initialization options
  var thr = document.getElementById("fit-thr-chk")
  var alt = document.getElementById("fit-alt-chk")
  var src = document.getElementById("fit-source-chk")
  if (sel.id == "fit-thr-chk"){
    src.checked = false;
    alt.checked = false;
    thr.checked = true;
    jQuery('#fit-alt-opt :input').attr('disabled', true);
    jQuery('#sel_group_fit').attr('disabled', true);
    jQuery('#sel_source_fit').attr('disabled', true);
    jQuery('#fit-thr-opt :input').attr('disabled', false);
  }else if (sel.id == "fit-alt-chk"){
    thr.checked = false;
    src.checked = false;
    alt.checked = true;
    jQuery('#sel_group_fit').attr('disabled', true);
    jQuery('#sel_source_fit').attr('disabled', true);
    jQuery('#fit-thr-opt :input').attr('disabled', true);
    jQuery('#fit-alt-opt :input').attr('disabled', false);
  } else {
    thr.checked = false;
    src.checked = true;
    alt.checked = false;
    jQuery('#sel_group_fit').attr('disabled', false);
    jQuery('#sel_source_fit').attr('disabled', false);
    jQuery('#fit-thr-opt :input').attr('disabled', true);
    jQuery('#fit-alt-opt :input').attr('disabled', true);
  }
}
function show_fit_sourcefiles(option){
  group = option.options[option.selectedIndex].text;
  text = ''
  for (i = 0; i < source_table_json.length; i++) {
    if(source_table_json[i].source_group == group){
      if(source_table_json[i].source_kind == 'VNA'){
        text += '<option value = "'+source_table_json[i].source_path + '">' + source_table_json[i].source_path + '</option>'
      }
    }
  }
  document.getElementById("sel_source_fit").innerHTML = text
}

function collect_init_fit_params(){
  var thr = document.getElementById("fit-thr-chk")
  var alt = document.getElementById("fit-alt-chk")
  var src = document.getElementById("fit-source-chk")
  if(thr.checked){
    var threshold = document.getElementById("fit-opt-thr").value
    var smoothing = document.getElementById("fit-opt-smooth-thr").value
    var width = document.getElementById("fit-opt-width").value
    return {
      'threshold':threshold,
      'smoothing':smoothing,
      'width':width
    }
  }else if (src.checked){
    var src = document.getElementById("sel_source_fit")
    try{
      var vna_file = src.options[src.selectedIndex].text;
      return {'vna_file':vna_file}
    }catch(err){
      alert("Please select a source file first")
      return false
    }
  }else{
    var npeaks = document.getElementById("fit-opt-npeaks").value
    var smoothing = document.getElementById("fit-opt-smooth-alt").value
    var a_cutoff = document.getElementById("fit-opt-A").value
    var q_cutoff = document.getElementById("fit-opt-qr").value
    var mag_cutoff = document.getElementById("fit-opt-depth").value
    return {
      'npeaks':npeaks,
      'smoothing':smoothing,
      'a_cutoff':a_cutoff,
      'q_cutoff':q_cutoff,
      'mag_cutoff':mag_cutoff,
    }
  }
}
function init_test_run(){
  init_params = collect_init_fit_params()
  if(init_params){
    socket.emit('init_test_run', {'params':init_params, files:analysis_config['single']['fitting']['files']});
    // Emit a test run request, enqueue measure and return the name of the last
    // check if the queues are empty? execute in local? with thread control?(pretty cool)?
    // block until the socket push is received
  }
}

jQuery(document).ready(function(){
  console.log("loading dfault analysis options...");
  diasble_init_fit_panel(document.getElementById("fit-thr-chk"))
});

function add_source_file_prompt(){
  //parse modal
  text = "<b>Files to be added as source:</b><br>"
  for (i = 0; i < file_list.length; i++) {
    text += '<span id = "'+ file_list[i].substring(0, file_list[i].length - 3) +'">' + file_list[i] + "</span><br>"
  }
  document.getElementById("source-files-list").innerHTML = text
  $("#source-files-modal").modal('show');
}

function add_source_file(event) {
  var checked = document.getElementById("permanent_source_checkbox").checked
  var group_name = document.getElementById("source-file-group").value
  for (i = 0; i < file_list.length; i++) {
    socket.emit('explore_add_source', {'file':file_list[i], 'permanent':checked, 'group':group_name});
  }
}

socket.on( 'explore_add_source_done', function( msg ) {
  var res = JSON.parse(msg)
  if(parseInt(res['result']) == 0){
    document.getElementById(res['file'].substring(0, res['file'].length - 3)).style.color = "red";
  }else{
    document.getElementById(res['file'].substring(0, res['file'].length - 3)).style.color = "green";
  }
  if(res["file"] == file_list[file_list.length - 1]){
    setTimeout(function(){
      alert("Source file update compelte, click ok to refresh.")
      clear_selected();
    }, 300)
  }
})

function remove_source_group(btn){
  if(confirm("Remove every file from source group "+btn.name+" ?")){
    socket.emit('explore_remove_source', {'group':btn.name});
    location.reload();
  }
}
function revome_safe_source(btn){
  if(confirm("Remove permanent source file "+btn.name+" ?")){
    socket.emit('explore_remove_source', {'file':btn.name});
  }
}

function remove_source(btn){
  socket.emit('explore_remove_source', {'file':btn.name});
}

function consolidate_source_file(){
  socket.emit('consolidate_source_files', {});
}

socket.on( 'consolidate_source_files', function( msg ) {
  //apply the configuration
  console.log(JSON.parse(msg))
  alert('Source files checked, click to refresh.')
  location.reload();
})

function remove_tmp_source_file(){
  socket.emit('remove_temporary_source_files', {});
  location.reload()
}

socket.on( 'remove_temporary_source_files', function( msg ) {
  //apply the configuration
  alert('Non permanent source file removed, click to refresh.')
  location.reload();
})
