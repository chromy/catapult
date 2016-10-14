console.log('Side loaded hack.js');
var report = document.querySelector('report-page');

function makeCheckbox(id) {
  var checkbox = document.createElement('input');
  checkbox.type = "checkbox";
  checkbox.id = id;
  checkbox.setAttribute('style', 'vertical-align: middle;');
  return checkbox;
}

function makeLabel(text, forId) {
  var label = document.createElement('label')
  label.htmlFor = forId;
  label.appendChild(document.createTextNode(text));
  return label;
}

function makeCheckboxFromChild(child, callback, name) {
  if (!name) {
    name = getLastSegment(child.id);
  }
  var checkbox = makeCheckbox(child.id);
  var label = makeLabel(name, child.id);
  checkbox.addEventListener('click', (e) => callback(e));
  checkbox.model = child;
  checkbox.checked = child.checked;

  var div = document.createElement('div');
  div.appendChild(checkbox);
  div.appendChild(label);
  return div;
}

function getLastSegment(id) {
  var parts = id.split(':');
  return parts[parts.length-1];
}

function getNthSegment(child, i) {
  if (child.group && child.group !== child.id && i === 0) {
    return child.group;
  }
  var id = child.id;
  var parts = id.split(':');
  if (i < parts.length-1) {
    return parts[i];
  } else {
    return '';
  }
}

function dataToSearchTerms(data) {
  var terms = [];
  for (var group of data) {
    for (var child of group.children) {
      terms.push({
        label: group.id + ': ' + child.id,
        child: child,
      });
    }
  }
  return terms;
}

function makeCheckBoxSubGroupChildren(i, children, callback) {
  var nodes = [];
  var first = {};
  for (var child of children) {
    var firstSegement = getNthSegment(child, i);
    if (!first[firstSegement]) {
      first[firstSegement] = [];
    }
    first[firstSegement].push(child);
  }
  if (first['']) {
    for (var child of first['']) {
      nodes.push(makeCheckboxFromChild(child, callback));
    }
  }
  for (let segment in first) {
    if (segment === '') continue;
    var subchildren = children.filter((child) => getNthSegment(child, i) == segment);
    if (subchildren.length === 1) {
      let singlechild = subchildren[0];
      if (singlechild.group) {
        var name = segment + ' / ' + singlechild.id;
        nodes.push(makeCheckboxFromChild(singlechild, callback, name));
        continue;
      } else {
        var name = segment + ':' + getLastSegment(singlechild.id);
        nodes.push(makeCheckboxFromChild(singlechild, callback, name));
        continue;
      }
    }
    let div = document.createElement('div');
    let h = document.createElement('p');
    h.appendChild(document.createTextNode(segment));
    h.setAttribute("style", "margin-bottom: 3px; margin-top: 5px;");
    nodes.push(h);
    for (subchild of makeCheckBoxSubGroupChildren(i+1, subchildren, callback)) {
      div.appendChild(subchild);
    }
    div.setAttribute("style", "padding-left: 10px;");
    let updateVis = function() {
      div.style.display = div.hidden ? 'none' : 'block';
      let arrow = div.hidden ? "&#9668;" : "&#9660;";
      h.innerHTML = segment + arrow
    }
    h.addEventListener('click', function() {
      div.hidden = !div.hidden;
      updateVis();
    });
    div.hidden = div.querySelectorAll('input:checked').length === 0;
    updateVis();
    nodes.push(div);
  }
  return nodes;
}

function makeCheckBoxGroup(group, callback) {
  var groupname = group.name;
  var groupid = group.id;

  var div = document.createElement('div');
  div.model = group;

  var h3 = document.createElement('h3');
  h3.appendChild(document.createTextNode(groupname));
  div.appendChild(h3);

  //for (var child of group.children) {
  //  var id = groupid + '-' + child.id;
  //  div.appendChild(makeCheckboxFromChild(id, child, callback));
  //}
  for (var checkbox of makeCheckBoxSubGroupChildren(0, group.children, callback)) {
    div.appendChild(checkbox);
  }
  return div;
}

var data = [
  {
    name: 'Bots',
    id: 'bots',
    children: [
        { id: 'android-nexus5',  checked: false, },
        { id: 'android-nexus5X', checked: false, },
    ],
  },
  {
    name: 'x Processes',
    id: 'processes',
    children: [
        { id: 'all_processes', checked: false, },
        { id: 'browser',       checked: false, },
    ],
  },
  {
    name: 'x Story',
    id: 'story',
    children: [
        { group: 'browse_media', id: 'browse_media_imgur',    checked: false, },
        { group: 'browse_media', id: 'browse_media_facebook', checked: false, },
        { group: 'load_social',  id: 'load_social_facebook',  checked: false, },
        { group: 'load_social',  id: 'load_social_twitter',   checked: false, },
    ],
  },
  {
    name: '+ Metric',
    id: 'metric',
    children: [
        { id: 'reported_by_chrome:sqlite:effective_size_avg',  checked: false, },
        { id: 'reported_by_os:system_memory:resident_size_avg', checked: false, },
    ],
  },
];

function getCheckedOptions(tree) {
  if (!tree.children) {
    if (tree.checked) {
      return [tree];
    } else {
      return [];
    }
  }
  var results = [];
  for (child of tree.children) {
    for (path of getCheckedOptions(child)) {
      results.push([tree].concat(path));
    }
  }
  return results;
}

function getAllCheckedOptions(root) {
  var results = {};
  for (tree of root) {
    results[tree.id] = getCheckedOptions(tree);
  }
  return results;
}

function product() {
  if (arguments.length === 1) {
    return arguments[0].map((x) => [x]);
  }
  var args = Array.from(arguments);
  var xs  = args.shift();
  var yss = product.apply(this, args);
  var results = [];
  for (x of xs) {
    for (ys of yss) {
      results.push([x].concat(ys));
    }
  }
  return results;
}

function optionsToGraphSpec(options) {
  var bot = options.bots[1].id;
  var processes = options.processes[1].id;
  var metric = options.metric[1].id;
  var storygroup = options.story[1].group;
  var story = options.story[1].id;
  var path = "ChromiumPerf/" + bot + "/system_health.memory_mobile/" + "memory:chrome:" + processes + ':' + metric + "/" + storygroup + "/" + story;
  if (story === storygroup) {
    path = "ChromiumPerf/" + bot + "/system_health.memory_mobile/" + "memory:chrome:" + processes + ':' + metric + "/"  + story;
  }
  var selected = [story];
  return [[path, selected]];
}

function addSpecToGraph(spec, graph) {
  console.log('Adding spec:', spec);
  graph.addSeriesGroup(spec, false);
}

function addGraph(spec) {
  console.log('Adding graph:', spec);
  report.addChart(spec, true);
}

function updateDataFromSubTestDict() {
  var d = report.testPicker.subtestDict;
  if (d === undefined) {
    alert("Please set suite=system_health.memory_infra and bot=nexus5x then load the hack again, thanks! :)");
    return;
  }
  var processes = [];
  var metrics = [];
  var stories = [];
  // memory:chrome:renderer_processes:reported_by_chrome:malloc:effective_size_avg
  var r = new RegExp('memory:chrome:([^:]*):(.*)');
  for (var test in d) {
    var match = r.exec(test);
    var p = match[1];
    if (processes.indexOf(p) === -1) processes.push(p);
    var m = match[2];
    if (metrics.indexOf(m) === -1) metrics.push(m);
    for (var subtest in d[test]['sub_tests']) {
      if (subtest === 'ref') continue;
      if (/ref/.exec(subtest)) continue;
      if (stories.indexOf(subtest) === -1) stories.push(subtest);
      for (var subsubtest in d[test]['sub_tests'][subtest]['sub_tests']) {
        if (subsubtest === 'ref') continue;
        if (/ref/.exec(subsubtest)) continue;
        if (stories.indexOf(subsubtest) === -1) stories.push(subsubtest);
      }
    }
  }
  stories.sort(function(a, b) {
    if (a.split('_').length === b.split('_').length) {
      return ( ( a == b ) ? 0 : ( ( a > b ) ? 1 : -1 ) );
    } else {
      return a.split('_').length - b.split('_').length;
    }
  });
  metrics.sort().reverse();
  processes.sort();
  data[1].children = processes.map((x) => ({ id: x, checked: false, }));
  data[2].children = stories.map((x) => ({ group: /^[^_]*_[^_]*/.exec(x)[0], id: x, checked: false, }));
  data[3].children = metrics.map((x) => ({ id: x, checked: false, }));
}

function objectify(array) {
    return array.reduce(function(p, c) {
         p[c[0]] = c[1];
         return p;
    }, {});
}

function values(o) {
  var xs = [];
  for (var k in o) {
    xs.push(o[k]);
  }
  return xs;
}

var displayedGraphs = [];
function checkboxCallback(e) {
  var checkbox = e.target;
  var checked = checkbox.checked;
  var id = checkbox.id;
  checkbox.model.checked = checked;
  var allInputs = document.querySelectorAll('input');
  Array.from(allInputs).filter((c) => c.id === id).forEach((c) => c.checked = checked);
  update();
}

function gridCallback(e) {
  var entry = e.target;
  entry.story.checked = entry.checked
  entry.metric.checked = entry.checked;
  update();
  //refreshUi();
}

function update() {
  document.querySelectorAll('paper-button#close-chart').forEach((x) => x.click());
  var allCheckedOptionsByGroup = getAllCheckedOptions(data);
  var allCheckedOptions = values(allCheckedOptionsByGroup);
  for (var x of allCheckedOptions) {
    if (x.length === 0) {
      return;
    }
  }

  var allMetrics = allCheckedOptions[3];
  allCheckedOptions[3] = [allMetrics[0]];

  var groups = Object.keys(allCheckedOptionsByGroup);
  var allGraphs = product.apply(this, allCheckedOptions);
  var allGraphsByGroup = allGraphs.map((xs) => objectify(xs.map((x, i) => [groups[i], x])));
  var graphsToBeAdded = allGraphsByGroup;
  var graphsToBeRemoved = [];
  for (var graph of graphsToBeAdded) {
    addGraph(optionsToGraphSpec(graph));
    for (var metric of allMetrics) {
      let c = document.querySelector('chart-container');
      graph.metric = metric;
      var spec = optionsToGraphSpec(graph);
      addSpecToGraph(spec, c)
    }
  }
  //for (var graph of graphsToBeAdded) {
  //  addGraph(optionsToGraphSpec(graph));
  //}

 // for (var story of allGraphsByGroup)
 // if (graphsToBeAdded.length > 0) {
 //   let c = document.querySelector('chart-container');
 //   window.setTimeout(function() {
 //     var spec = optionsToGraphSpec(graphsToBeAdded[0]);
 //     addSpecToGraph(spec, c)
 //   }, 10);
 // }
//  var options = getOptions();
  displayedGraphs = allGraphsByGroup;
}

function makeGrid(stories, metrics, callback) {
  let grid = document.createElement('div');
  for (story of stories.children) {
    let row = document.createElement('div');
    for (metric of metrics.children) {
      let entry = makeCheckbox('');
      entry.story = story;
      entry.metric = metric;
      entry.checked = story.checked && metric.checked;
      entry.addEventListener('click', (e) => callback(e));
      entry.title = story.id + ' & ' + metric.id;
      row.appendChild(entry);
    }
    grid.appendChild(row);
  }
  grid.setAttribute("style", "clear: both");
  return grid;
}

function matchingTerms(query, terms) {
  if (query === '') {
    return [];
  }
  var matches = [];
  var r = new RegExp('.*'+query.split('').join('.*')+'.*');
  console.log(r);
  for (var term of terms) {
    if (r.exec(term.label)) {
      matches.push(term);
    }
  }
  return matches;
}

function makeSearchBox(data) {
  var terms = dataToSearchTerms(data);
  var div = document.createElement('div');
  var searchbox = document.createElement('input');
  var results = document.createElement('div');
  searchbox.setAttribute('style', 'font-size: 2em; width: auto; max-width: 100%;');
  searchbox.type = 'text';
  searchbox.size = 50;
  searchbox.placeholder = 'Search all options';
  div.appendChild(searchbox);
  div.appendChild(results);
  searchbox.addEventListener('keyup', function() {
    while (results.firstChild) results.removeChild(results.firstChild);
    var query = searchbox.value;
    for (var term of matchingTerms(query, terms)) {
      var name = term.label;
      results.appendChild(makeCheckboxFromChild(term.child, checkboxCallback, name));
    }
  })
  return div;
}

function refreshUi() {
  var newui = document.createElement('div');
  newui.id = 'newui'
  newui.appendChild(makeSearchBox(data));
  for (var group of data) {
    var checkboxGroup = makeCheckBoxGroup(group, checkboxCallback);
    checkboxGroup.setAttribute("style", "margin: 15px; float: left");
    newui.appendChild(checkboxGroup);
  }
  //newui.appendChild(document.createElement('div'));
  //newui.appendChild(makeGrid(data[3], data[2], gridCallback));

  if (oldnewui = document.querySelector('#newui')) {
    report.removeChild(oldnewui);
  }
  report.insertBefore(newui, document.querySelector('#charts-container'));
}

//var suiteInput = document.evaluate('//label[text()="Test suite"]', document, null, XPathResult.ANY_TYPE, null).iterateNext().nextSibling;
//var botInput = document.evaluate('//label[text()="Bot"]', document, null, XPathResult.ANY_TYPE, null).iterateNext().nextSibling;
//suiteInput.value = "system_health.memory_mobile";
//suiteInput.click();
////botInput.value = "android-nexus5";
////botInput.blur();

updateDataFromSubTestDict();
refreshUi();
