#!/usr/bin/env python
"""

"""
import sys
import os
import requests
import sh
from lxml import html
import tempfile

ZIP_DIR = 'zips'
BUILD_DIR = 'builds'
RESULT_DIR = 'results'

BUILD_BOT_REPORT_URL = 'https://build.chromium.org/p/chromium.perf/builders/Android%20Builder/builds/{}'
gsutil = sh.Command('gsutil')
unzip = sh.Command('unzip')
mv = sh.Command('mv')
run_benchmark = sh.Command('/usr/local/google/home/hjd/proj/chromium/src/tools/perf/run_benchmark')

def commit_order(commits, start=None, end=None):
  start = start if start else min(commits)
  end = end if end else max(commits)

  if end < start:
    return []

  if end == start:
    return [] if start in commits else [start]

  seen = set(commits)
  new = []
  gap = end - start
  while gap:
    more = [i for i in range(start, end+1, gap) if i not in seen]
    seen.update(more)
    new.extend(more)
    gap /= 2
  return new

def best_commit_to_test_next(commits, start=None, end=None):
  order = commit_order(commits, start, end)
  if not order:
    return None
  return order[0]

def get_tested_commits(wanted_suffix='json'):
  commits = []
  for name in os.listdir(RESULT_DIR):
    commit, suffix = name.split('.')
    if suffix == wanted_suffix:
      commits.append(as_int(commit))
  return commits

def ensure_directory(path):
  if not os.path.exists(path):
    os.makedirs(path)

def url_to_gs(url):
  gs = url.replace('https://storage.cloud.google.com/', 'gs://')
  return gs

def get_url_for_commit(commit):
  r = requests.get(BUILD_BOT_REPORT_URL.format(commit))
  assert r.status_code == 200
  tree = html.fromstring(r.text)
  links = tree.xpath("//a[text()='gsutil.upload']")
  assert links
  url = links[0].get('href')
  return url

def commit_to_apk_path(commit):
  name = '{}.apk'.format(commit)
  return os.path.join(BUILD_DIR, name)

def commit_to_result_path(commit):
  name = '{}.json'.format(commit)
  return os.path.join(RESULT_DIR, name)

def get_tempory_zip_path(commit):
  directory = tempfile.mkdtemp(suffix='chrome_android_zip'.format(commit))
  return os.path.join(directory, '{}.zip'.format(commit))

def has_build(commit):
  ensure_directory(BUILD_DIR)
  return os.path.exists(commit_to_apk_path(commit))

def fetch_build(commit):
  print 'Fetching zip for commit {}'.format(commit)
  url = get_url_for_commit(commit)
  print 'Zip for commit {} lives at {}'.format(commit, url)
  print 'Downloading...',
  ensure_directory(BUILD_DIR)
  zip_path = get_tempory_zip_path(commit)
  gsutil('cp', url_to_gs(url), zip_path)
  print ' ...done'
  print 'Extracting apk...',
  unzip('-j', zip_path, 'ChromePublic.apk', '-d', BUILD_DIR)
  mv(os.path.join(BUILD_DIR, 'ChromePublic.apk'), commit_to_apk_path(commit))
  print ' ...done'

def ensure_build_present(commit):
  print 'Looking for build for commit {}'.format(commit),
  if has_build(commit):
    print ' ...found'
  else:
    print ' ...not found'
    fetch_build(commit)

def test_build(commit):
  print 'Testing commit {}'.format(commit)
  ensure_directory(RESULT_DIR)
  args = [
      "run",
      "--browser=exact",
      "system_health.memory_mobile",
      "--story-filter=load:search:google",
      "--browser-executable={}".format(commit_to_apk_path(commit)),
      #"--output={}".format(commit_to_result_path(commit)),
      "--output-dir={}".format(RESULT_DIR),
      "--output-format=json"
  ]
  print 'Running', 'run_benchmark', ' '.join(args)
  print run_benchmark(args)
  print '...done'

def bisect(start, end):
  while True:
    tested_commits = get_tested_commits()
    next_commit = best_commit_to_test_next(tested_commits, start, end)
    if next_commit is None:
      print 'Done.'
      break
    print ''.join([c in tested_commits for c in range(start, end+1)].map(lambda c: '*.'[c]))
    print ''.join([c is next_commit    for c in range(start, end+1)].map(lambda c: '^ '[c]))
    fetch_build(next_commit)
    test_build(next_commit)

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
  assert commit_order([], 1, 10) == [1, 10, 5, 9, 3, 7, 2, 4, 6, 8]

def test_commit_order_copes_with_initially_seen():
  assert commit_order([1, 10, 9, 8], 1, 10) == [5, 3, 7, 2, 4, 6]

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
  test_commit_order_copes_with_offsets()

def as_int(n, error='Expected int'):
  try:
    return int(n)
  except ValueError:
    raise Exception(error)

def usage():
  return """
cantors_bisect.py fetch [commit]
cantors_bisect.py bisect [start_commit] [end_commit]
cantors_bisect.py test [commit]
"""

if __name__ == '__main__':
  test()
  if len(sys.argv) < 2:
    print usage()
    exit()

  cmd = sys.argv[1]
  if cmd == 'fetch' and len(sys.argv) >= 3:
    commit = as_int(sys.argv[2])
    ensure_build_present(commit)
  elif cmd == 'test' and len(sys.argv) >= 3:
    commit = as_int(sys.argv[2])
    test_build(commit)
  elif cmd == 'bisect' and len(sys.argv) >= 4:
    start_commit_raw = sys.argv[2]
    end_commit_raw = sys.argv[3]
    start_commit = as_int(start_commit_raw, 'start was "{}" should be an int'.format(start_commit_raw))
    end_commit = as_int(end_commit_raw, 'end was "{}" should be an int'.format(end_commit_raw))
    bisect(start_commit, end_commit)
  else:
    print usage()

