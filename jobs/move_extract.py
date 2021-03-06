#!/usr/bin/env python

# Copyright 2017 The Kubernetes Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Migrate --extract flag from an JENKINS_FOO env to a scenario flag."""

import json
import os
import re
import sys

ORIG_CWD = os.getcwd()  # Checkout changes cwd

def test_infra(*paths):
    """Return path relative to root of test-infra repo."""
    return os.path.join(ORIG_CWD, os.path.dirname(__file__), '..', *paths)

def sort():
    """Sort config.json alphabetically."""
    # pylint: disable=too-many-branches,too-many-statements,too-many-locals
    with open(test_infra('jobs/config.json'), 'r+') as fp:
        configs = json.loads(fp.read())
    regexp = re.compile('|'.join([
        r'E2E_OPT=(--check_version_skew=false|true)'
    ]))
    problems = []
    for job, values in configs.items():
        if 'args' not in values:
            continue
        new_args = []
        found = False
        for arg in values['args']:
            if arg == '--check-leaked-resources=true':
                found = True
                new_args.append('--check-leaked-resources')
            elif arg == '--check-leaked-resources=false':
                found = True
            elif arg == '--check_version_skew=false':
                found = True
                new_args.append('--check-version-skew=false')
            else:
                new_args.append(arg)
        if not found:
            continue
        if found and values.get('scenario') != 'kubernetes_e2e':
            problems.append('Weird %s' % job)
            continue
        values['args'] = new_args
        if values:
            continue
        # old stuff
        with open(test_infra('jobs/%s.env' % job)) as fp:
            env = fp.read()
        lines = []
        skew = None
        for line in env.split('\n'):
            mat = regexp.search(line)
            if not mat:
                lines.append(line)
                continue
            args = mat.group(1)
            if args:
                if skew:
                    problems.append('Duplicate %s' % job)
                    break
                skew = args
                continue
        else:
            if not skew:
                continue
            for arg in values['args']:
                if not arg.startswith('--check_version_skew'):
                    continue
                if arg != skew:
                    problems.append('Mismatch in %s: %s != %s' % (job, arg, skew))
                    continue
                break
            else:
                values['args'].append(skew)
            with open(test_infra('jobs/%s.env' % job), 'w') as fp:
                fp.write('\n'.join(lines))
    with open(test_infra('jobs/config.json'), 'w') as fp:
        fp.write(json.dumps(configs, sort_keys=True, indent=2, separators=(',', ': ')))
        fp.write('\n')
    if not problems:
        sys.exit(0)
    print >>sys.stderr, '%d problems' % len(problems)
    print '\n'.join(problems)

if __name__ == '__main__':
    sort()
