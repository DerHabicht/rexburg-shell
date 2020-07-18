#!/usr/bin/env pipenv-shebang
"""Seagull

Usage:
    seagull list
    seagull describe <project>
    seagull build <project> [--for-print --to-pdf --watch]
    seagull clean <project>

Options:
    -h --help       Show this screen.
    --version       Show version.
    --for-print     Configure the LaTeX template for printed output.
    --to-pdf        Carry the build process all the way to the PDF stage.
    --watch         Watch this directory and rebuild on change (hot reload).
"""
import projects
from docopt import docopt

from latex import BuildWatch, LaTeXDocument

VERSION = '0.1.0'

if __name__ == '__main__':
    args = docopt(__doc__, version=VERSION)
    all_projects = projects.load_projects()

    if args['list']:
        print(all_projects)
    elif args['describe']:
        try:
            doc = LaTeXDocument.load_document(args['<project>'], all_projects)
            print(doc)
        except KeyError as e:
            print(f'{args["<project>"]} is not a valid project identifier. Valid projects are {all_projects}')
        except FileNotFoundError as e:
            print(f'Project {args["<project>"]} does not have a valid build.yml file.')
    elif args['build']:
        try:
            doc = LaTeXDocument.load_document(args['<project>'], all_projects)
            doc.make(for_print=args['--for-print'], to_pdf=args['--to-pdf'])

            if args['--watch']:
                watch = BuildWatch(doc, for_print=args['--for-print'], to_pdf=args['--to-pdf'])
                watch.run()
        except KeyError as e:
            print(f'{args["<project>"]} is not a valid project identifier. Valid projects are {all_projects}')
        except FileNotFoundError as e:
            print(f'Project {args["<project>"]} does not have a valid build.yml file.')

    elif args['clean']:
        try:
            doc = LaTeXDocument.load_document(args['<project>'], all_projects)
            doc.clean()
        except KeyError as e:
            print(f'{args["<project>"]} is not a valid project identifier. Valid projects are {all_projects}')
        except FileNotFoundError as e:
            print(f'Project {args["<project>"]} does not have a valid build.yml file.')
