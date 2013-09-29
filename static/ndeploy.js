/*
 * go ndeploy, go!
 */

function fixUUID(uuid) {
  var uuidArray = uuid.split('-');
  // only the first half of the UUID is wrong, so iterate
  // over first 3 array values and reverse in pairs
  for ( var j = 0; j < 3; j++ ) {
    uuidArray[j] = uuidArray[j].match(/../g).reverse().join('');
  }
  var fixedUUID = uuidArray.join('-').toLowerCase();
  return fixedUUID;
}

function getProvision(uuid) {
  window.location.href = window.location.href + 'provisions/' + uuid;
}

function createProvision(provision) {
  
  $.ajax({
    type: 'POST',
    url: '/provisions/',
    contentType: 'application/json',
    data: provision
  })
  .done(function(data) {
    document.getElementById('status').innerHTML = data;
  });
}


function getTemplates() {
  $.getJSON('templates', function(data) {
    var os_html = '<option value=""></option>'
      , boot_html = '<option value=""></option>'
      , os_t_len = data.os.length
      , boot_t_len = data.boot.length;
   
    for (var i = 0; i < os_t_len; i++) {
      os_html += '<option value="' + data.os[i] + '">' + data.os[i] + '</option>';
    }

    for (var i = 0; i < boot_t_len; i++) {
      boot_html += '<option value="' + data.boot[i] + '">' + data.boot[i] + '</option>';
    }

    $('select#os_template').append(os_html);
    $('select.boot_sequence').append(boot_html);

  });
}

function doEet() {
  var fqdn = document.getElementById('fqdn').value.toLowerCase()
    , os_template = document.getElementById('os_template').value
    , boot_sequence = {}
    , re = new RegExp('^([0-9a-f]){8}-([0-9a-f]){4}-([0-9a-f]){4}-([0-9a-f]){4}-([0-9a-f]){12}$')
    , uuid = re.exec(document.getElementById('uuid').value.toLowerCase())
    , host_uuid = uuid[0];

  if (!host_uuid) {
    document.getElementById('status').innerHTML = 'Enter a valid UUID (including dashes)!';
  } else {

    if (document.getElementById('fix_uuid').checked) {
      host_uuid = fixUUID(host_uuid);
    }

    if (fqdn === '' || os_template === '') {
      getProvision(host_uuid);
    } else {

      // for each element with class boot_sequence get value
      
      var boot_list = $('select.boot_sequence');
      boot_list.each(function() {
        if (this.value != '') {
          var boot_id = this.id.replace('boot_sequence_', '');
          // boot_sequence is not 0 based on the other end
          boot_sequence[parseInt(boot_id) + 1] = this.value;
        }
      });
     
      var provision_json = {
                              uuid: host_uuid,
                              fqdn: fqdn,
                              os_template: os_template,
                              boot_sequence: boot_sequence
                           };
 
      createProvision(JSON.stringify(provision_json));
    }
  }

}
