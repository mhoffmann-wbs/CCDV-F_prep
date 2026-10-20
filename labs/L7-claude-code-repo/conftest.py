"""Keeps the starter out of the repo-wide `cd labs && uv run pytest` run.

Why exclude it instead of marking the bug test xfail:
- starter/ and solution/ both ship a package called `gridiron_stats`. One
  pytest process can import only one of them, so collecting both would test
  whichever happened to load first.
- The failing starter tests are the lab's task list. An xfail marker would
  also tell Claude Code "this failure is expected", which defeats the point.

Run the starter on its own (it has its own pyproject.toml, so pytest uses it
as the rootdir and skips this file):  cd starter && uv run pytest
"""

collect_ignore = ["starter"]
