"""simple script that santizes the `output` directory.
works even if no santitation required."""

import sys, os, core, json
from os.path import join

def do():
    output_dir = core.output_dir()
    for dirname in os.listdir(output_dir):
        for filename in os.listdir(join(output_dir, dirname)):
            path = join(output_dir, dirname, filename)
            if path.endswith('.json'):
                sys.stdout.write('santizing %s' % path)
                core.write_results(
                    core.sanitize_ga_response(json.load(open(path, 'r'))),
                    path)
                sys.stdout.write(" ...done\n")
                sys.stdout.flush()

if __name__ == '__main__':
    do()
