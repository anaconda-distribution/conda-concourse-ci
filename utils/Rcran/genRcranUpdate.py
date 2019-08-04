#!/usr/bin/env python
# coding: utf-8

from bs4 import BeautifulSoup
import rpy2.robjects as robjects
from rpy2.robjects import pandas2ri
import requests
import json
import pandas as pd
import numpy as np
import re, os, time, shutil

do_max_pkg_cnt = 100 # set to -1 if all packages shall be done

CRAN_BASE = 'https://cran.r-project.org'
Rrepository = 'aggregateR'
RrepositoryURL = 'git@github.com:AnacondaRecipes/aggregateR.git'
#CRAN_BASE = 'https://cran.microsoft.com/snapshot/2018-01-01'
RecipeMaintainer = 'katietz'
Rver = '36'
Rfullver = '3.6.1'

batch_count_max=100
do_recursive = '' # '--dirty --recursive'

# The Microsoft CRAN time machine allows us to select a snapshot of CRAN at any day in time. For instance, 2018-01-01 is (in Microsoft's determination) the "official" snapshot date for R 3.4.3.

def get_r_channel_rdata(arch):
   """ Read from r channel architecture specific information """
   rdata = {}
   url = "https://repo.anaconda.com/pkgs/r/" + arch + "/repodata.json"
   repodata = session.get(url)
   if repodata.status_code != 200:
       print('\n{} returned code {}'.format(url, page.status_code))
   else:
	   rdata = json.loads(repodata.text)
   return rdata;

def build_anaconda_pkglist(rver):
    repodata = get_r_channel_rdata("noarch")
    pkgs = get_anaconda_pkglist(repodata, arch = 'noarch', ver = rver)
    # we don't get mro package
    repodata = get_r_channel_rdata('linux-64')
    anaconda_pkgs2 = get_anaconda_pkglist(repodata, arch = 'linux-64', ver = rver)
    pkgs.update(anaconda_pkgs2)
    repodata = get_r_channel_rdata('linux-32')
    anaconda_pkgs2 = get_anaconda_pkglist(repodata, arch = 'linux-32', ver = rver)
    pkgs.update(anaconda_pkgs2)
    repodata = get_r_channel_rdata('win-32')
    anaconda_pkgs2 = get_anaconda_pkglist(repodata, arch = 'win-32', ver = rver)
    pkgs.update(anaconda_pkgs2)
    repodata = get_r_channel_rdata('win-64')
    anaconda_pkgs2 = get_anaconda_pkglist(repodata, arch = 'win--64', ver = rver)
    pkgs.update(anaconda_pkgs2)
    repodata = get_r_channel_rdata('osx-64')
    anaconda_pkgs2 = get_anaconda_pkglist(repodata, arch = 'osx-64', ver = rver)
    pkgs.update(anaconda_pkgs2)

    print('{} Total Anaconda R packages found.'.format(len(pkgs)))
    # print(list(pkgs))
    return pkgs

def write_out_bld_script(stages, mode = 'sh'):
    cnt = do_max_pkg_cnt
    comment_line = '#'
    sep_line = ' \\\n    '
    if mode != 'sh':
        comment_line = 'REM'
        sep_line = ' '
    with open(f'./build-stage.{mode}', 'w') as bd:
        if mode == 'sh':
            bd.write('#!/bin/bash\n\n')
        for i, stage in enumerate(stages):
            bd.write('{} stage {}\n'.format(comment_line, i))
            scount = len(stage)
            j = 0
            elno = 0
            while elno < scount and (cnt == -1 or cnt > 0):
                # Write out build steps ...
                bd.write('conda-build --skip-existing -c https://repo.continuum.io/pkgs/main --R={}{}'.format(Rfullver, sep_line))
                el = 0
                while elno < scount and el < batch_count_max and (cnt == -1 or cnt > 0):
                    p = stage[elno]
                    bd.write(' r-' + p + '-feedstock{}'.format(sep_line))
                    elno += 1
                    el += 1
                    if cnt != -1:
                        cnt -= 1
                j += 1
                # terminate lines ...
                bd.write('\n')
            bd.write('\n')
            print("State {} is splitted into {} parts".format(i, j))
            if cnt == 0:
                break
        # end for

def get_anaconda_pkglist(rdata, arch = 'linux-64', start_with = 'r', ver = '36'):
    """ Read from r channel architecture specific package list with specific version """
    pkgs = set(v['name'][2:] for v in rdata['packages'].values() if v['name'].startswith('r-') and v['build'].startswith('' + start_with + Rver))
    print('{} Anaconda R {} packages in {} found.'.format(len(pkgs), arch, start_with))
    return pkgs

def write_out_skeleton_script(stages):
    sep_line = ' \\\n    '
    cnt = do_max_pkg_cnt

    with open(f'./build-skeleton.sh', 'w') as bsd:
        bsd.write('#!/bin/bash\n\n')
        bsd.write('# do imports via conda skeleton cran\n\n')
        bsd.write('# first checkout the R repository\n')
        bsd.write('rm -rf {}\ngit clone {} --recursive\n'.format(Rrepository, RrepositoryURL))
        bsd.write('pushd {}\ngit submodule update --init\n'.format(Rrepository))
        bsd.write('git checkout -b latest_update\n')
        for i, stage in enumerate(stages):
            scount = len(stage)
            j = 0
            elno = 0
            while elno < scount and (cnt == -1 or cnt > 0):
                # Write out skeleton creation ...
                bsd.write('conda skeleton cran --cran-url={} --output-suffix=-feedstock/recipe {}{}'.format(CRAN_BASE, do_recursive, sep_line))
                bsd.write(' --add-maintainer={} --update-policy=merge-keep-build-num --r-interp=r-base --use-noarch-generic{}'.format(RecipeMaintainer, sep_line))
                el = 0
                while elno < scount and el < batch_count_max and (cnt == -1 or cnt > 0):
                    p = stage[elno]
                    bsd.write(' ' + p)
                    elno += 1
                    el += 1
                    if cnt != -1:
                        cnt -= 1
                j += 1
                # terminate lines ...
                bsd.write('\n')
            print("State {} is splitted into {} parts".format(i, j))
            if cnt == 0:
                break
        # end for
        bsd.write('# now write out git commands to list and add new files\n')
        bsd.write('git add -N . >new_files_added.txt\n')
        bsd.write('git add .\n')
        bsd.write('git commit -m "Updated CRAN recipes"\n')
        bsd.write('git push latest_update latest_update\n')
        # leave the git repository
        bsd.write('popd\n')

pandas2ri.activate()
readRDS = robjects.r['readRDS']
session = requests.Session()

get_ipython().run_line_magic('matplotlib', 'qt')

anaconda_pkgs = build_anaconda_pkglist(rver = Rver)

from binstar_client.utils.config import DEFAULT_URL, load_token
built_pkgs = set()

# In[61]:


from email.parser import BytesParser
from email import message_from_string

pkgs = requests.get(CRAN_BASE + '/src/contrib/PACKAGES').text
items = [message_from_string(pkg) for pkg in pkgs.split('\n\n')]


def deps_set(dep):
    if dep is None:
        return emptyset
    return set(it.replace('(', ' (').strip().split()[0] for it in dep.split(',') if it.strip())


# We're only looking for the tarballs in the `/src/contrib` directory, so the easiest way to do that is to scrape the index page.

packages = set(item['package'] for item in items)
print('{} CRAN R packages found, {} not found in defaults.'.format(len(packages), len(packages-anaconda_pkgs)))

emptyset = set()
BASE_PACKAGES = {'R', 'base', 'compiler', 'datasets', 'graphics', 'grDevices', 'grid', 'methods',
                 'parallel', 'splines', 'stats', 'stats4', 'tcltk', 'tools', 'translations', 'utils'}
summary = {}
for data in items:
    deps = deps_set(data.get('depends')) | deps_set(data.get('imports')) | deps_set(data.get('linkingto'))
    record = {'compiled':data.get('needscompilation', 'no'), 'depends':deps - BASE_PACKAGES, 'version': data.get('version')}
    summary[data['package']] = record
    
summary = pd.DataFrame(summary).T
summary.index.name = 'name'
summary.reset_index(inplace=True)
summary.compiled = summary.compiled.str.lower() != 'no'
summary

packages = set(summary['name'])

summary['valid'] = summary.depends.apply(lambda x: x.issubset(packages))
summary[~summary.valid]


all_supers = pd.Series([None] * len(summary), index=summary.name)
all_deps = pd.Series(summary.depends.values, index=summary.name)
def compute_super(name):
    superdeps = all_supers[name]
    if superdeps is None:
        deps = all_deps[name]
        all_supers[name] = superdeps = deps.copy()
        for dep in deps:
            if dep in packages:
                superdeps.update(compute_super(dep))
    return superdeps
for name in summary.name:
    compute_super(name)
summary['superdepends'] = all_supers.values
summary['n_depends'] = summary.depends.apply(len)
summary['n_superdepends'] = summary.superdepends.apply(len)
summary


summary['valid'] = summary.superdepends.apply(lambda x: x.issubset(packages))
summary[~summary.valid]

completed = built_pkgs | anaconda_pkgs
candidates = summary[summary.valid & ~summary.name.str.lower().isin(completed)].set_index('name')

to_compile = []
stages = []
while len(candidates):
    can_do = candidates.superdepends.apply(lambda x: completed.issuperset(a.lower() for a in x))
    can_do = candidates.index[can_do]
    if len(can_do) == 0:
        break
    completed.update(a.lower() for a in can_do)
    to_compile.extend(can_do)
    stages.append(can_do)
    candidates = candidates.drop(can_do, 'index')
    if len(candidates) != 0:
        print("Remaining candidates {}".format(len(candidates)))

write_out_skeleton_script(stages)
write_out_bld_script(stages, mode = 'sh')
write_out_bld_script(stages, mode = 'bat')

print("Done.")
