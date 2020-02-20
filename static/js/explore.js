var socket = io.connect('http://' + document.domain + ':' + location.port);

function request_update_selected_files(folders){
  var checked = document.getElementById("recursive_file_loading_chk").checked
  socket.emit('request_selection_file_list', {'folders':folders, 'recursive':checked});
}

//console.log(data_stuct)
jQuery_tree('#file_tree').jstree(
  {
    'core' : {
      'data' : data_stuct
    },

    "search" : {
        'case_sensitive' : false,
        'show_only_matches' : true,
     },
     'checkbox': {
      'three_state' : true, // to avoid that fact that checking a node also check others
      'whole_node' : false,  // to avoid checking the box just clicking the node
      'tie_selection' : false // for checking without selecting and selecting without checking
    },
    "plugins" : ["checkbox","search"]//,"state"
  }
);

jQuery_tree('#file_tree').on("check_node.jstree", function(e, data) {
  var name = data.node.id

  if(name.substr(name.length - 3) !== ".h5"){
    console.log("adding folder " + name)
    socket.emit('add_to_selection_from_folder', {'folder':name});
    console.log("Possible bug! update the page to get the correct checkboxes!!")
    $(".file_checkbox").filter(function(){

       return true
    }).prop('checked', true);
  }
})

jQuery_tree('#file_tree').on("uncheck_node.jstree", function(e, data) {
  var name = data.node.id
  if(name.substr(name.length - 3) !== ".h5"){
    console.log("removing folder " + name)
    socket.emit('remove_selection_from_folder', {'folder':name});
    console.log("Possible bug! update the page to get the correct checkboxes!!")
    $(".file_checkbox").filter(function(){
       return true
    }).prop('checked', false);
  }
})

// Link the check box logics for coherence
jQuery_tree(document).on('click', '.file_checkbox', function(event){
  var chk = event.target;
  console.log("jstree op. id node: "+ chk.value);
  if (chk.checked == true){
    jQuery_tree('#file_tree').jstree('check_node', chk.value);
  }else{
    jQuery_tree('#file_tree').jstree('uncheck_node', chk.value);
  }
});

// listen for event
jQuery_tree('#file_tree').on('changed.jstree', function (e, data) {
  var i, j, r = [];
  for(i = 0, j = data.selected.length; i < j; i++) {
    r.push(data.instance.get_node(data.selected[i]).id);
  }
   // clean the datatable, make a websoket request to populate the datatable

  request_update_selected_files(r)
})


function uncheck_all_tree(){
  //jQuery_tree('#file_tree').jstree(true).uncheck_all(); // THis method has a bug!!!
  var jsonNodes = jQuery_tree('#file_tree').jstree(true).get_json('#', { flat: true });
  jQuery_tree.each(jsonNodes, function (i, val) {
    jQuery_tree('#file_tree').jstree('uncheck_node', jQuery_tree(val).attr('id'));
  })
}


var to = false;
jQuery_tree('#file_tree_search').keyup(function () {
  if(to) { clearTimeout(to); }
  to = setTimeout(function () {
    var v = jQuery_tree('#file_tree_search').val();
    console.log("Searching for "+v)
    jQuery_tree('#file_tree').jstree('search', v);
  }, 250);
});

function splash(splashDivId, fn, msg)
{
    var splashDiv = document.getElementById(splashDivId)
    splashDiv.style.display = "block";
    setTimeout(function() {
       fn(msg)
       splashDiv.style.display = "none";
    }, 100);

}

function open_plot_modal(){
  $("#modal_plot_select").modal('show');
}
function open_selected_modal(){
  $("#selected-files-modal").modal()
};

( function($) {
  $(document).ready(function() {

    var t = $('#file_selector_table').DataTable({
      language: {
        searchPlaceholder: "Search files...",
        search: "",
      }
    });

    function load_datatable_selected_files(msg){
      var res = JSON.parse(msg)['items']
      //console.log(res)
      for (i = 0; i < res.length; i++) {
        //console.log(res[i])
        if(parseInt(res[i][0])){
          var db_icon = '<span class="glyphicon glyphicon-ok"></span>'
        }else{
          var db_icon = '<span class="glyphicon glyphicon-remove"></span>'
        }
        res[i][0] = db_icon
        if(parseInt(res[i][1])){
          var plot_icon = '<button type="submit" class="plot_this btn btn-link glyphicon glyphicon-picture" style="margin:0px; padding:0px" id="show_plot_'+res[i][2]+'"></button>'
        }else{
          var plot_icon = '<span class="glyphicon glyphicon-remove"></span>'
        }
        res[i][1] = plot_icon
        //console.log(currently_selected)
        if(currently_selected.includes(res[i][2])){
          var current_select_checkbox = '<input class = "file_checkbox" type="checkbox" checked name = "files_selected" value="'+res[i][2]+'">'
        }else{
          var current_select_checkbox = '<input class = "file_checkbox" type="checkbox" name = "files_selected" value="'+res[i][2]+'">'
        }
        res[i].push(current_select_checkbox)
        t.rows.add([res[i]])
        //console.log(x)
      }
      t.draw();
      // Update height of the file explorer to match the <table>
    }

      socket.on( 'update_selection_file_list', function( msg ) {
        t.clear()
        splash('loader', load_datatable_selected_files, msg)
      })
      var plot_table = $('#plot_select_table').DataTable({});

      $(document).on('click', '.plot_this', function(event){
        var plotname = (event.target.id).replace('show_plot_','')
        console.log("Showing plots for: "+plotname)
        document.getElementById('plot_measure_name').innerHTML = plotname
        open_plot_modal()
        plot_table.clear()
        console.log("requesting plots...")
        socket.emit('request_selection_plot_list', {'file':plotname});
      });


      $(document).on('click', '.file_checkbox', function(event){
        var chk = event.target
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
      });

      socket.on( 'update_selection_plot_list', function( msg ) {
        var res = JSON.parse(msg)['items']
        for (i = 0; i < res.length; i++) {
          var split_address = res[i][0].split("/")
          res[i][0] = '<a href="'+url_plotter+'/'+res[i][0]+'" target=”_blank”>'+split_address[split_address.length -1]+'</a>'
        }
        plot_table.rows.add(res)
        plot_table.draw();
      })

      var slected_file_datatable = $('#selected_files-table').DataTable({});

      console.log("loading selecte files from database...");
      socket.emit('request_selection', {});

      socket.on( 'update_selection', function( msg ) {
        if(parseInt(JSON.parse(msg)['err'])!=1){
          // alert("Error: cannot add a file twice in present implementation")

        }
        //console.log(JSON.parse(msg)['files'].join(", "))
        file_list = JSON.parse(msg)['files']

        // Reset
        currently_selected = []

        file_list_expanded = []
        for (i = 0; i < file_list.length; i++) {
          var splitpath = file_list[i].split("/")

          currently_selected.push(splitpath[splitpath.length - 1])

          file_list_expanded.push([
            i, splitpath[splitpath.length - 1], (splitpath.slice(0, splitpath.length -1)).join("/")
          ])
        }
        slected_file_datatable.clear()
        slected_file_datatable.rows.add(file_list_expanded)
        slected_file_datatable.draw()
        document.getElementById('selected-files-btn').value = "Selected files (" + file_list.length + ")"
      })

      $('#clear_selected-file-btn').on('click', function(){
        console.log("Clearing selected files");
        socket.emit('explore_clear_selection', {});
        socket.emit('request_selection', {});
        // Clear all checkboxes (present and list)
        $(".file_checkbox").prop("checked", false);
        uncheck_all_tree()

      });

  } );
} ) ( jQuery );

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
      socket.emit('explore_clear_selection', {});
      socket.emit('request_selection', {});
      $(".file_checkbox").prop("checked", false);
      uncheck_all_tree()
      location.reload()
    }, 300)
  }
});


( function($) {
  $(document).ready(function() {
    var collapsedGroups = {};
    //
    var table = $('#source-file-table').DataTable({
        //data:source_table_json,
        order: [[0, 'asc']],
        rowGroup: {
          // Uses the 'row group' plugin
          dataSrc: 0,
          startRender: function (rows, group) {
            var collapsed = !!collapsedGroups[group];

            rows.nodes().each(function (r) {
              r.style.display = collapsed ? '' : 'none'; // Inverted to start with ollapsed rows
            });
            return $('<tr/>')
            .append('<td colspan="4">' + group + ' (' + rows.count() + ') <input type="submit" class="btn btn-secondary" id = "remove_group_source" value = "Remove group" name = "' + group + '" style=\'float:right\' onclick = "remove_source_group(this)"> </input></td>' )
            .attr('data-name', group)
            .toggleClass('collapsed', collapsed);
          }
        }
    });
    $("#source-file-table").on('click', '.btn-link', function () {
      $(this).parent().parent().remove();
    });

    $('#source-file-table tbody').on('click', 'tr.group-start', function () {
      var name = $(this).data('name');
      collapsedGroups[name] = !collapsedGroups[name];
      table.draw(false);
    });

    } );
  } ) ( jQuery );

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

      document.getElementById(key+'-analysis-chk').checked = false

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

        document.getElementById(key+'-analysis-chk').disabled = false

        document.getElementById(key+'-files').style["display"] = "block"

        jQuery('#'+key+'-analysis-body').show();
      }else{
        //header
        document.getElementById(key+'-analysis-header').innerHTML = "<span class=\"glyphicon glyphicon-remove\"></span>"
        //disable file tab
        document.getElementById(key+'-files').style["display"] = "none"
        //display failure message
        //document.getElementById(key+'-analysis-body').innerHTML = jdict[key]['reason']
        jQuery('#'+key+'-analysis-body').hide();
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

function gather_analysis_parameters(){
  console.log("Gathering analysis parameters...")

  // Common instructions for all analysis, just if it's requested or not
  for (var key in analysis_config['single']) {
    if (analysis_config['single'].hasOwnProperty(key)) {
      if (parseInt(analysis_config['single'][key]['available'])){
        if(document.getElementById(key+'-analysis-chk').checked){
          analysis_config['single'][key]['requested'] = 1
        }else{
          analysis_config['single'][key]['requested'] = 0
        }
      }
    }
  }

}

function enqueue_all_jobs(){
  console.log("RUN analysis")


  // gather parameters
  gather_analysis_parameters()

  // send analysis_config back with parameters
  socket.emit('run_analysis', {'params':analysis_config});

  // Conform the selection
  $(".file_checkbox").prop("checked", false);
  uncheck_all_tree();

  // Close the form
  jQuery('#analysis-modal').modal('hide');
}
