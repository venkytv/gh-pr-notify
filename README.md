gh-pr-notify.py
===============

Simple utility to go through a Github repository's open pull requests and list
those which match a given set of paths.

```shell
./gh-pr-notify.py <github-repo> <path1> <path2>
```

The script needs a Github [personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
with access to read pull requests of the specified repo. On macOS, the token needs to be stored in the keychain.
```shell
security add-internet-password -s github.com -a $USER -w
```

On other platforms, the token is expected to be stored in the file `~/.gh-token`, but this can be overridden:
```shell
$ gh-pr-notify.py -h
usage: gh-pr-notify.py [-h] [--state-dir DIR] [--token-file FILE] [--last-pr NUM] [--debug] [--verbose] repo path [path ...]

positional arguments:
  repo               Github repo URL
  path               File/directory path to filter PRs

optional arguments:
  -h, --help         show this help message and exit
  --state-dir DIR    Directory to store state in (default: /Users/venky/.gh-pr-notify)
  --token-file FILE  Github token file (ignored on macOS) (default: /Users/venky/.gh-token)
  --last-pr NUM      Override last PR to start checking from (default: None)
  --debug            Enable debug logging (default: False)
  --verbose, -v      Print verbose messages (default: False)
```

**NOTE**:
- Paths are always matched by prefix and do not support wildcards (right now).
- The script keeps track of the last PR that was evaluated, but this can be overridden with the `--last-pr` command line parameter.
