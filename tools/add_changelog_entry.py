# SPDX-License-Identifier: MIT

"""
Adds an entry to the changelog in README.md, optionally after increasing the patch version in manifest.json.

With --bump-patch the version in manifest.json is increased (e.g. 0.6.0 -> 0.6.1) and a new changelog
section is created for it. Without it the entry is added to the section of the current version, which
is created if it does not exist yet. An entry that is already present in the section is not added again.

Usage: python tools/add_changelog_entry.py [--bump-patch] "Entry text"
"""

import argparse
import os
import re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MANIFEST_PATH = os.path.join(ROOT, 'manifest.json')
README_PATH = os.path.join(ROOT, 'README.md')

VERSION_RE = re.compile(r'("version"\s*:\s*")(\d+)\.(\d+)\.(\d+)(")')
CHANGELOG_HEADER = '## Changelog\n\n'


def read(path):
    with open(path, 'r', encoding='utf-8', newline='') as f:
        return f.read()


def write(path, content):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(content)


def get_version(manifest):
    match = VERSION_RE.search(manifest)
    if match is None:
        raise RuntimeError('no version found in manifest.json')
    return match


def bump_patch():
    manifest = read(MANIFEST_PATH)
    match = get_version(manifest)
    major, minor, patch = int(match.group(2)), int(match.group(3)), int(match.group(4))
    version = '%d.%d.%d' % (major, minor, patch + 1)
    write(MANIFEST_PATH, VERSION_RE.sub(r'\g<1>%s\g<5>' % version, manifest, count=1))
    return version


def add_entry(version, entry):
    readme = read(README_PATH)
    if CHANGELOG_HEADER not in readme:
        raise RuntimeError('no "## Changelog" section found in README.md')
    line = '* %s\n' % entry
    header = '### %s\n\n' % version

    if header not in readme:
        readme = readme.replace(CHANGELOG_HEADER, CHANGELOG_HEADER + header + line + '\n', 1)
    else:
        start = readme.index(header) + len(header)
        end_match = re.compile(r'\n(### |## |Older versions:)').search(readme, start)
        end = end_match.start() if end_match else len(readme)
        section = readme[start:end]
        if line in section:
            return False
        section = section.rstrip('\n') + '\n' + line
        readme = readme[:start] + section + readme[end:]

    write(README_PATH, readme)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--bump-patch', action='store_true', help='increase the patch version in manifest.json first')
    parser.add_argument('entry', help='changelog entry text')
    args = parser.parse_args()
    if not args.entry.strip():
        parser.error('the changelog entry must not be empty')

    if args.bump_patch:
        version = bump_patch()
        print('version increased to %s' % version)
    else:
        version = get_version(read(MANIFEST_PATH)).group(0).split('"')[-2]

    if add_entry(version, args.entry):
        print('changelog entry added to %s' % version)
    else:
        print('changelog entry already present in %s' % version)


if __name__ == '__main__':
    main()
