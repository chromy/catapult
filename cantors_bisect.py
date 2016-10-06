#!/usr/bin/env python
"""

"""
import sys

def commit_order(commits, start=None, end=None):
  start = start if start else min(commits)
  end = end if end else max(commits)

  if end < start:
    return []

  next_commits = []

  if start not in commits:
    next_commits.append(start)
  if start != end and end not in commits:
    next_commits.append(end)

  if end - start > 1:
    mid = (end - start) / 2 + start
    next_commits.extend(commit_order(commits + next_commits, start, mid))
    next_commits.extend(commit_order(commits + next_commits, mid, end))

  return next_commits

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
  assert commit_order([], 1, 9) == [1, 9, , 2, 4]

def test():
  test_commit_order_empty()
  test_commit_order_same()
  test_commit_order_adjecent()
  test_commit_order_gap()
  test_commit_order_bigger_gap()
  test_commit_order_very_big_gap()

if __name__ == '__main__':
  start_commit_raw = sys.argv[1]
  end_commit_raw = sys.argv[2]

  start_commit = int(start_commit_raw)
  end_commit = int(end_commit_raw)
  print commit_order([], start=start_commit, end=end_commit)
  test()

