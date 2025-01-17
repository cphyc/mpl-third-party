#!/usr/bin/env python

from collections import defaultdict
from pathlib import Path
import pprint
import warnings

from jinja2 import Template
import requests
from yaml import safe_load


here = Path(__file__).parent.resolve()

print("Opening section names file")
with (here.parent / 'section_names.yml').open() as f:
    section_names = safe_load(f)

section_names = section_names['section_names']

print("section_names", section_names)
config = defaultdict(list)
for path in (here.parent / 'packages').glob('*'):
    with path.open('r') as fin:
        package = safe_load(fin)

    package['section'] = section_names[package.get('section', 'miscellaneous').lower()]

    print(f"  {package['repo']} -> {package['section']}")
    try:
        package['user'], package['repo_name'] = package['repo'].split('/')
    except ValueError:
        warnings.warn(f'Package.repo is not in correct format: {package}')
        continue
    package.setdefault('conda_package', package['repo_name'])
    package.setdefault('pypi_name', package['repo_name'])

    if package.get('badges'):
        package['badges'] = {x.strip() for x in package['badges'].split(',')}
    else:
        package['badges'] = {'pypi', 'conda'}

    needs_newline = False
    if 'pypi' in package['badges']:
        needs_newline = True
        print('    pypi: ', end='', flush=True)
        response = requests.get(f"https://pypi.org/pypi/{package['pypi_name']}/json/")
        if response.status_code == 200:
            print('found')
        else:
            print('not found')
            package['badges'].remove('pypi')
    if package.get('conda_channel'):
        package['badges'].add('conda')
    package.setdefault('conda_channel', 'conda-forge')
    if 'conda' in package['badges']:
        needs_newline = True
        print('    conda: ', end='')
        response = requests.get(f"https://anaconda.org/{package['conda_channel']}/"
                                f"{package['conda_package']}/",
                                allow_redirects=False)
        if response.status_code == 200:
            print('found', end='')
        else:
            print('not found', end='')
            package['badges'].remove('conda')
    if needs_newline:
        print()

    if package.get('sponsors'):
        package['badges'].add('sponsor')
    if package.get('site') and package['badges'].isdisjoint({'site', 'rtd'}):
        package['badges'].add('site')
    if package.get('dormant'):
        package['badges'].add('dormant')

    if 'rtd' in package['badges']:
        package.setdefault('rtd_name', package['repo_name'])

    if 'site' in package['badges']:
        if 'site' not in package:
            package['site'] = f'https://{package["repo_name"]}.org'
        else:
            package['site'] = package['site'].rstrip('/')

    # Divide the yml files into sections based on the section tag...
    config[package['section']].append(package)

# Turn defaultdict into plain dict.
config = {**config}
pprint.pprint(config)

template = Template((here / 'template.rst').read_text(),
                    lstrip_blocks=True, trim_blocks=True)

(here.parent / 'docs/source/packages.rst').write_text(f"""\
Third-party and user-contributed packages
=========================================

.. include:: intro.rst

{template.render(config=config)}
""")
