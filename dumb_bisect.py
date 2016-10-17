#!/usr/bin/env python
# Copyright (c) 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""

"""
from __future__ import print_function
import sys
import os
import re
import json
import tempfile
import sh

DEFAULT_BUILD_DIR = 'builds'
DEFAULT_RESULT_DIR = 'results'
DEFAULT_RUN_BENCHMARK_PATH = 'tools/perf/run_benchmark'

BUILD_BOT_REPORT_URL = 'https://build.chromium.org/p/chromium.perf/builders/Android%20Builder/builds/{}'
gsutil = sh.Command('gsutil')
unzip = sh.Command('unzip')
mv = sh.Command('mv')
git = sh.Command('git')
touch = sh.Command('touch')

def eprint(*args, **kwargs):
  print(*args, file=sys.stderr, **kwargs)

def log(*args):
  start = "\033[1;31m"
  end = "\033[0;0m"
  s = start + ' '.join(args) + end
  eprint(s)

def url_to_gs(url):
  gs = url.replace('https://storage.cloud.google.com/', 'gs://')
  return gs

def get_url_for_commit(commit):
  return 'https://storage.cloud.google.com/chrome-test-builds/official-by-commit/Android Builder/full-build-linux_{}.zip'.format(commit)

def commit_to_apk_path(build_dir, commit):
  name = '{}.apk'.format(commit)
  return os.path.join(build_dir, name)

def commit_to_chartjson_path(results_dir, commit):
  result_dir = 'results_{}'.format(commit)
  return os.path.join(results_dir, result_dir, 'results-chart.json')

def commit_to_result_dir(results_dir, commit):
  return os.path.join(results_dir, 'results_{}'.format(commit))

def get_tempory_zip_path(commit):
  directory = tempfile.mkdtemp(suffix='chrome_android_zip'.format(commit))
  return os.path.join(directory, '{}.zip'.format(commit))

def read_json(path):
  with open(path) as f:
    return json.load(f)

def get_tested_commits(results_dir):
  names = os.listdir(results_dir)
  matches = [re.match('results_(\d+)', name) for name in names]
  vaild_matches = [m.group(1) for m in matches if m is not None]
  commits = map(int, vaild_matches)
  return commits

class RealBackend(object):
  def mv(self, src, target):
    mv(src, target)

  def ensure_directory(self, path):
    if not os.path.exists(path):
      os.makedirs(path)

  def write_to_output_file(self, path, s):
    with open(path, 'w') as f:
      f.write(s)

  def run_benchmark(self, path, *args):
    run_benchmark = sh.Command(path)
    return run_benchmark(*args)

  def unzip(self, *args):
    unzip(*args)

  def gsutil(self, *args):
    gsutil(*args)

  def touch(self, *args):
    touch(*args)

  def tested_build(self, commit):
    pass

  def fetched_build(self, commit):
    pass

  def get_tested_commits(self, results_dir):
    return get_tested_commits(results_dir)

  def has_build(self, build_dir, commit):
    return os.path.exists(commit_to_apk_path(build_dir, commit))


class FakeBackend(object):
  def __init__(self):
    self.ensured_directories = []
    self.tested = []
    self.fetched = []

  def mv(self, src, target):
    log('MV', src, target)

  def ensure_directory(self, path):
    if path not in self.ensured_directories:
      log('MKDIR', path)
      self.ensured_directories.append(path)

  def write_to_output_file(self, path, s):
    log('[Would have written the following to {}]'.format(path))
    print(s)

  def run_benchmark(self, path, *args):
    log('RUN_BENCHMARK', path, ' '.join(args))
    return '[Benchmark output would appear here.]'

  def unzip(self, *args):
    log('UNZIP', ' '.join(args))

  def gsutil(self, *args):
    log('GSUTIL', ' '.join(args))

  def touch(self, *args):
    log('TOUCH', ' '.join(args))

  def tested_build(self, commit):
    self.tested.append(commit)

  def fetched_build(self, commit):
    self.fetched.append(commit)

  def get_tested_commits(self, results_dir):
    return self.tested

  def has_build(self, build_dir, commit):
    return commit in self.fetched

class Config(object):
  def __init__(self, results_directory, build_directory, run_benchmark_path):
    self.results_dir = results_directory
    self.build_dir = build_directory
    self.run_benchmark_path = run_benchmark_path

class Bisector(object):
  def __init__(self, config, backend):
    self.config = config
    self.backend = backend
    self.build_dir = self.config.build_dir
    self.results_dir = self.config.results_dir

  def bisect(self, benchmark, start, end, extra_args=None):
    extra_args = extra_args if extra_args else []
    self.backend.ensure_directory(self.config.build_dir)
    self.backend.ensure_directory(self.config.results_dir)
    while True:
      tested_commits = self.backend.get_tested_commits(self.results_dir)
      next_commit = best_commit_to_test_next(tested_commits, start, end)
      if next_commit is None:
        print('Done.')
        break
      tested = [c in tested_commits for c in range(start, end+1)]
      next   = [c == next_commit    for c in range(start, end+1)]
      print('Done:', ''.join(map(lambda c: '.*'[c], tested)))
      print('Next:', ''.join(map(lambda c: ' ^'[c], next)))
      self.fetch_build(next_commit)
      self.test_build(benchmark, next_commit, extra_args)

  def fetch_build(self, commit):
    self.backend.ensure_directory(self.config.build_dir)
    url = get_url_for_commit(commit)
    print('Fetching zip for commit {} from {}'.format(commit, url))
    print('Downloading...',)
    zip_path = get_tempory_zip_path(commit)
    self.backend.gsutil('cp', url_to_gs(url), zip_path)
    print(' ...done')
    print('Extracting apk...')
    apk_path = commit_to_apk_path(self.config.build_dir, commit)
    self.backend.unzip('-j', zip_path, 'ChromePublic.apk', '-d', self.build_dir)
    self.backend.mv(os.path.join(self.build_dir, 'ChromePublic.apk'), apk_path)
    print(' ...done')
    self.backend.fetched_build(commit)

  def test_build(self, benchmark, commit, extra_args=None):
    extra_args = extra_args if extra_args else []
    self.backend.ensure_directory(self.config.results_dir)
    self.backend.ensure_directory(self.config.results_dir)
    result_dir = commit_to_result_dir(self.config.results_dir, commit)
    apk_path = commit_to_apk_path(self.build_dir, commit)
    args = [
        "run",
        benchmark,
        "--browser=exact",
        "--browser-executable={}".format(apk_path),
        "--results-label={}".format(commit),
        "--output-dir={}".format(result_dir),
        "--output-format=chartjson",
        "--output-format=json",
    ] + extra_args
    print('Running', 'run_benchmark', ' '.join(args))
    print(self.backend.run_benchmark(self.config.run_benchmark_path, *args))
    print('...done')
    self.backend.tested_build(commit)

  def ensure_build_present(self, commit):
    print('Looking for build for commit {}'.format(commit),)
    if self.backend.has_build(self.config.build_dir, commit):
      print('...found it.')
    else:
      print("...couldn't find it.")
      self.fetch_build(commit)

class Csver(object):
  def __init__(self, config, backend):
    self.config = config
    self.backend = backend

  def json_for_commit(self, commit):
    path = commit_to_chartjson_path(self.config.results_dir, commit)
    return read_json(path)

  def json_to_rows(self, j, commit):
    charts = j['charts']
    for metric, page in charts.items():
      if metric == 'trace':
        continue
      for page_name, results_for_page in page.items():
        if page_name == 'summary':
          continue
        for value in results_for_page['values']:
          yield commit, metric, page_name, value

  def rows_for_commit(self, commit):
    j = self.json_for_commit(commit)
    return self.json_to_rows(j, commit)

  def rows_for_commits(self, commits):
    return [row for commit in commits for row in self.rows_for_commit(commit)]

  def write_results_to_csv(self, path):
    commits = get_tested_commits(self.config.results_dir)
    rows = self.rows_for_commits(commits)
    columns = ['commit', 'metric', 'page', 'value']

    lines = []
    for row in [columns] + rows:
      lines.append(','.join(map(str, row)))
    s = '\n'.join(lines)
    self.backend.write_to_output_file(path, s)

def best_commit_order(start, end):
  if end < start:
    return []

  new = [start]
  if end != start:
    new.append(end)

  seen = set(new)
  n = end - start + 1
  while len(new) < n:
    s = sorted(new)
    for i, j in zip(s, s[1:]):
      mid = (j - i) / 2 + i
      if mid not in seen:
        new.append(mid)
        seen.add(mid)
  return new

def commit_order(seen, start=None, end=None):
  start = start if start else min(seen)
  end = end if end else max(seen)
  return [c for c in best_commit_order(start, end) if c not in seen]

def best_commit_to_test_next(commits, start=None, end=None):
  order = commit_order(commits, start, end)
  if not order:
    return None
  return order[0]

def test_commit_order_empty():
  assert commit_order([], 2, 1) == []

def test_commit_order_same():
  assert commit_order([], 1, 1) == [1]

def test_commit_order_adjecent():
  assert commit_order([], 1, 2) == [1, 2]

def test_commit_order_gap():
  assert commit_order([], 1, 3) == [1, 3, 2]

def test_commit_order_bigger_gap():
  assert commit_order([], 1, 4) == [1, 4, 2, 3]

def test_commit_order_very_big_gap():
  assert commit_order([], 1, 5) == [1, 5, 3, 2, 4]

def test_commit_order_very_very_big_gap():
  assert commit_order([], 1, 10) == [1, 10, 5, 3, 7, 2, 4, 6, 8, 9]

def test_commit_order_copes_with_initially_seen():
  assert commit_order([1, 10, 9, 8], 1, 10) == [5, 3, 7, 2, 4, 6]

def test_commit_order_copes_with_odd_lengths():
  assert commit_order([], 1, 9) == [1, 9, 5, 3, 7, 2, 4, 6, 8]

def test_commit_order_copes_with_offsets():
  assert commit_order([], 101, 104) == [101, 104, 102, 103]

def test_url_to_gs():
  assert url_to_gs('https://storage.cloud.google.com/chrome-test-builds/official-by-commit/Android Builder/full-build-linux_423548.zip') == 'gs://chrome-test-builds/official-by-commit/Android Builder/full-build-linux_423548.zip'

def test():
  test_url_to_gs()
  test_commit_order_empty()
  test_commit_order_same()
  test_commit_order_adjecent()
  test_commit_order_gap()
  test_commit_order_bigger_gap()
  test_commit_order_very_big_gap()
  test_commit_order_very_very_big_gap()
  test_commit_order_copes_with_initially_seen()
  test_commit_order_copes_with_odd_lengths()
  test_commit_order_copes_with_offsets()

def as_int(n, error='Expected int'):
  try:
    return int(n)
  except ValueError:
    raise Exception(error)

def get_arg(args, name):
  if name not in args:
    display_usage_and_exit(1)
  index = rfind(args, name)
  if index + 1 >= len(args):
    display_usage_and_exit(1)
  arg = args[index + 1]
  if arg.startswith('-'):
    display_usage_and_exit(1)
  return arg

def rfind(l, x):
  return len(l) - 1 - l[::-1].index(x)

def display_usage_and_exit(code):
  display_usage()
  exit(code)

def display_usage():
  print("""Dumb local bisect.

Usage:
  dumb_bisect.py bisect <benchmark> <start_commit> <end_commit>
      [-- --story-filter=foo ...]
  dumb_bisect.py fetch <commit>
  dumb_bisect.py test <benchmark> <commit>
  dumb_bisect.py csv <path>
  dumb_bisect.py help
  dumb_bisect.py (-h|--help)

Options:
  -h --help           Display this screen.
  -n --dry-run        Print what would happen but don't actually do anything.
  --build-dir <dir>   Directory to put APKs in (default: ./build)
  --result-dir <dir>  Directory to put results in (default: ./results)
  --run-benchmark-path <path> (default: ./tools/perf/run_benchmark)

Detail:
  bisect <benchmark> <start_commit> <end_commit> [-- ...run_benchmark args]
    Runs the benchmark <benchmark> on a build for each commit in the range
    [start_commit...end_commit]. Outputs the results for each commit into a
    directory named 'result_<commit number>' within result-dir.

    Tests the range in the sensible order given that run_benchmark takes a long
    time and our script could be killed at anytime.
    For example the five commits:
    .....
    are tested in the order:
    14352

  fetch <commit>
    Download the APK for the commit numbered <commit> put it in to build-dir.

  test <benchmark> <commit>
    Runs the benchmark <benchmark> on the APK for <commit> and puts the result
    into a directory named 'result_<commit number>' within result-dir.

  csv <path>
    Collect all the results in result-dir, combine them and output the result
    at <path> in csv format with the columns [commit, metric, page, value].
""")

if __name__ == '__main__':
  if len(sys.argv) < 2:
    display_usage()
    exit()

  args = []
  rest = []
  if '--' in sys.argv:
    index = rfind(sys.argv, '--')
    rest = sys.argv[index+1:]
    args = sys.argv[:index]
  else:
    args = sys.argv

  backend = RealBackend()
  if '-n' in sys.argv or '--dry-run' in sys.argv:
    backend = FakeBackend()

  results_dir = DEFAULT_RESULT_DIR
  if '--results-dir' in sys.argv:
    results_dir = get_arg(sys.argv, '--results-dir')

  build_dir = DEFAULT_BUILD_DIR
  if '--build-dir' in sys.argv:
    build_dir = get_arg(sys.argv, '--build-dir')

  run_benchmark_path = DEFAULT_RUN_BENCHMARK_PATH
  if '--run-benchmark-path' in sys.argv:
    run_benchmark_path = get_arg(sys.argv, '--run-benchmark-path')

  config = Config(results_dir, build_dir, run_benchmark_path)
  bisector = Bisector(config, backend)

  cmd = sys.argv[1]
  if cmd == 'help' or '--help' in sys.argv or '-h' in sys.argv:
    display_usage()
  elif cmd == 'fetch' and len(sys.argv) >= 3:
    commit = as_int(sys.argv[2])
    bisector.ensure_build_present(commit)
  elif cmd == 'test' and len(sys.argv) >= 4:
    benchmark = sys.argv[2]
    commit = as_int(sys.argv[3])
    bisector.test_build(benchmark, commit, extra_args=rest)
  elif cmd == 'bisect' and len(sys.argv) >= 5:
    benchmark = sys.argv[2]
    start_commit_raw = sys.argv[3]
    end_commit_raw = sys.argv[4]
    start_error = 'start was "{}" should be an int'.format(start_commit_raw)
    end_error = 'end was "{}" should be an int'.format(end_commit_raw)
    start_commit = as_int(start_commit_raw, start_error)
    end_commit = as_int(end_commit_raw, end_error)
    bisector.bisect(benchmark, start_commit, end_commit, extra_args=rest)
  elif cmd == 'csv' and len(sys.argv) >= 3:
    path = sys.argv[2]
    csver = Csver(config, backend)
    csver.write_results_to_csv(path)
  elif cmd == 'selftest':
    test()
  else:
    display_usage()

