# SPDX-License-Identifier: MIT

"""
Regenerates gw2/db/achievements.json (achievement id -> name) from the Guild Wars 2 API.

The plugin requests names of achievements missing in this file from the API at runtime,
an up to date file only reduces the number of these requests.

Prints how many achievements were added, changed (renamed) and removed compared to the previous file.
With --summary-file this summary is also written to the given file (used for the changelog entry).

Usage: python tools/update_achievements_db.py [--summary-file PATH]
"""

import argparse
import json
import os
import time
import urllib.request

API_URL = 'https://api.guildwars2.com/v2/achievements'
IDS_PER_REQUEST = 200
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'gw2', 'db', 'achievements.json')


def get_json(url):
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            print('request failed (%s), retrying: %s' % (e, url))
            time.sleep(2 * (attempt + 1))
    raise RuntimeError('failed to request %s' % url)


def load_db():
    if not os.path.exists(DB_PATH):
        return dict()
    with open(DB_PATH, mode='r', encoding='utf-8') as f:
        return json.load(f)


def get_summary(old, new):
    added = len(new.keys() - old.keys())
    removed = len(old.keys() - new.keys())
    changed = sum(1 for k in new.keys() & old.keys() if new[k] != old[k])
    return 'Updated achievements DB: %s added, %s changed, %s removed' % (added, changed, removed)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--summary-file', help='write the summary of the changes to this file')
    args = parser.parse_args()

    old = load_db()

    ids = get_json(API_URL)
    print('found %s achievements' % len(ids))

    names = dict()
    for i in range(0, len(ids), IDS_PER_REQUEST):
        chunk = ids[i:i + IDS_PER_REQUEST]
        for achievement in get_json('%s?ids=%s' % (API_URL, ','.join(str(x) for x in chunk))):
            names[achievement['id']] = achievement['name']

    #do not replace the DB with an incomplete one if the API returned partial data
    if len(names) < len(ids) * 0.9:
        raise RuntimeError('received only %s names for %s achievements' % (len(names), len(ids)))

    new = {str(k): names[k] for k in sorted(names)}
    with open(DB_PATH, mode='w', encoding='utf-8', newline='\n') as f:
        json.dump(new, f, ensure_ascii=False, indent=4)
        f.write('\n')

    print('written %s achievements to %s' % (len(names), os.path.normpath(DB_PATH)))

    summary = get_summary(old, new)
    print(summary)
    if args.summary_file:
        with open(args.summary_file, mode='w', encoding='utf-8') as f:
            f.write(summary + '\n')


if __name__ == '__main__':
    main()
