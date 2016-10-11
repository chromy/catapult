console.log('Side loaded hack.js');
var report = document.querySelector('report-page');

var newui = document.createElement('div');
newui.id = 'newui'

function makeCheckbox(id) {
  var checkbox = document.createElement('input');
  checkbox.type = "checkbox";
  checkbox.id = id;
  return checkbox;
}

function makeLabel(text, forId) {
  var label = document.createElement('label')
  label.htmlFor = forId;
  label.appendChild(document.createTextNode(text));
  return label;
}

function addCheckbox(container, id, text, callback) {
  var checkbox = makeCheckbox(id);
  var label = makeLabel(text, id);
  checkbox.addEventListener('click', (e) => callback(e));
  var div = document.createElement('div');
  div.appendChild(checkbox);
  div.appendChild(label);
  container.appendChild(div);
}

function makeCheckBoxGroup(groupname, groupid, boxes, callback) {
  var div = document.createElement('div');
  var h3 = document.createElement('h3');
  h3.appendChild(document.createTextNode(groupname));
  div.appendChild(h3);
  for (var box of boxes) {
    var id = groupid + '-' + box;
    var name = box;
    addCheckbox(div, id, name, callback);
  }
  return div;
}

var data = [
  {
    name: 'Bots',
    id: 'bots',
    options: [
        { id: 'android-nexus5',  checked: false, },
        { id: 'android-nexus5X', checked: false, },
    ],
  },
  {
    name: 'Processes',
    id: 'processes',
    options: [
        { id: 'all_processes', checked: false, },
        { id: 'browser',       checked: false, },
    ],
  },
  {
    name: 'Metric',
    id: 'metric',
    options: [
        { id: 'reported_by_chrome:sqlite:effective_size_avg',  checked: false, },
        { id: 'reported_by_os:system_memory:resident_size_avg', checked: false, },
    ],
  },
  {
    name: 'Story Group',
    id: 'group',
    options: [
        { id: 'load_social',  checked: false, },
        { id: 'browse_media', checked: false, },
    ],
  },
  {
    name: 'Story',
    id: 'story',
    options: [
        { id: 'browse_media_imgur',    checked: false, },
        { id: 'browse_media_facebook', checked: false, },
        { id: 'load_social_facebook',  checked: false, },
        { id: 'load_social_twitter',   checked: false, },
    ],
  },
];

function updateData(groupid, optionid, checked) {
  for (var group of data) {
    if (group.id === groupid) {
      for (var option of group.options) {
        if (option.id === optionid) {
          option.checked = checked;
          break;
        }
      }
      break;
    }
  }
}

function fullySpecified() {
  for (var group of data) {
    var anyChecked = false;
    for (var option of group.options) {
      if (option.checked) {
        anyChecked = true;
        break;
      }
    }
    if (!anyChecked) {
      console.log(group);
      return false;
    }
  }
  return true;
}

function getOptions() {
  var checkedOptions = {};
  for (var group of data) {
    for (var option of group.options) {
      if (option.checked) {
        checkedOptions[group.id] = option.id;
        break;
      }
    }
  }
  return checkedOptions;
}

function addGraph(options) {
  var path = "ChromiumPerf/" + options.bots + "/system_health.memory_mobile/" + "memory:chrome:" + options.processes + ":" + options.metric + "/" + options.group + "/"  + options.story;
  var selected = [options.story];
  report.addChart([[path, selected]], true);
}

function checkboxCallback(e) {
  var checkbox = e.target;
  var checked = checkbox.checked;
  var groupid = checkbox.id.split(/(.+?)-(.+)/)[1]
  var id = checkbox.id.split(/(.+?)-(.+)/)[2]
  updateData(groupid, id, checked);
  console.log(checked, groupid, id);
  console.log(data);
  if (fullySpecified()) {
    var options = getOptions();
    console.log("adding chart");
    addGraph(options);
  }
}

for (groupData of data) {
  var groupname = groupData.name;
  var groupid = groupData.id;
  var options = groupData.options.map((x) => x.id);
  var group = makeCheckBoxGroup(groupname, groupid, options, checkboxCallback);
  group.setAttribute("style", "margin: 15px; float: left");
  newui.appendChild(group);
}

if (oldnewui = document.querySelector('#newui')) {
  report.removeChild(oldnewui);
}
report.insertBefore(newui, document.querySelector('#charts-container'));
