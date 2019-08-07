#!/usr/bin/env python
# coding: utf-8

# requires ipython rpy2 matplotlib tzlocal pandas

from bs4 import BeautifulSoup
import rpy2.robjects as robjects
from rpy2.robjects import pandas2ri
import requests
import json
import pandas as pd
import numpy as np
import re, os, time, shutil
from email.parser import BytesParser
from email import message_from_string

do_max_pkg_cnt = 100 # set to -1 if all packages shall be done

CRAN_BASE = 'https://cran.r-project.org'
RrepositoryName = 'aggregateR'
RrepositoryURL = 'git@github.com:AnacondaRecipes/aggregateR.git'
RrepositoryURL2 = 'https://github.com/AnacondaRecipes/aggregateR.git'
#CRAN_BASE = 'https://cran.microsoft.com/snapshot/2018-01-01'
RecipeMaintainer = 'katietz'
Rver = '36'
Rfullver = '3.6.1'

batch_count_max=100
do_recursive = '' # '--dirty --recursive'

# The Microsoft CRAN time machine allows us to select a snapshot of CRAN at any day in time. For instance, 2018-01-01 is (in Microsoft's determination) the "official" snapshot date for R 3.4.3.

def get_anaconda_pkglist(rdata, arch, start_with = 'r', ver = '36'):
    """ Read from r channel architecture specific package list with specific version """
    pkgs = set(v['name'][2:] for v in rdata['packages'].values() if v['name'].startswith('r-') and v['build'].startswith('' + start_with + Rver))
    print('{} Anaconda R {} packages in {} found.'.format(len(pkgs), arch, start_with))
    return pkgs

def build_anaconda_pkglist(rver, rchannel = 'r'):
    """ Get list of available packages from r or r_test channel for given version """
    pkgs = set()
    archs = ['noarch', 'linux-32', 'linux-64', 'win-32', 'win-64', 'osx-64']
    for arch in archs:
        rdata = {}
        url = 'https://repo.anaconda.com/pkgs/{}/{}/repodata.json'.format(rchannel, arch)
        repodata = session.get(url)
        if repodata.status_code != 200:
            print('\n{} returned code {}'.format(url, page.status_code))
        else:
            rdata = json.loads(repodata.text)
            pkgs2 = get_anaconda_pkglist(rdata, arch, ver = rver)
            pkgs.update(pkgs2)
            # we don't look at mro packages

    print('{} Total Anaconda packages found in {}.'.format(len(pkgs), rchannel))
    # print(list(pkgs))
    return pkgs

def write_out_resources(fd):
    name = 'build_r_script'
    fd.write('resources:\n')
    fd.write('- name: rsync-build-pack\n')
    fd.write('  type: rsync-resource\n')
    fd.write('  source:\n')
    fd.write('    base_dir: /ci/build_pack\n')
    fd.write('    disable_version_path: true\n')
    fd.write('    private_key: ((common.intermediate-private-key))\n')
    fd.write('    server: bremen.corp.continuum.io\n')
    fd.write('    user: ci\n')
    # resource for linux-64
    fd.write('- name: rsync_{}-on-linux_64\n'.format(name))
    fd.write('  type: rsync-resource\n')
    fd.write('  source:\n')
    fd.write('    base_dir: /ci/ktietz/artifacts\n')
    fd.write('    disable_version_path: true\n')
    fd.write('    private_key: ((common.intermediate-private-key))\n')
    fd.write('    server: bremen.corp.continuum.io\n')
    fd.write('    user: ci\n')
    # resource for osx-64
    fd.write('- name: rsync_{}-on-osx\n'.format(name))
    fd.write('  type: rsync-resource\n')
    fd.write('  source:\n')
    fd.write('    base_dir: /ci/ktietz/artifacts\n')
    fd.write('    disable_version_path: true\n')
    fd.write('    private_key: ((common.intermediate-private-key))\n')
    fd.write('    server: bremen.corp.continuum.io\n')
    fd.write('    user: ci\n')
    fd.write('resource_types:\n')
    fd.write('- name: rsync-resource\n')
    fd.write('  type: docker-image\n')
    fd.write('  source:\n')
    fd.write('    repository: conda/concourse-rsync-resource\n')
    fd.write('    tag: latest\n')

def write_out_onlinux64(fd, feedstocks):
    # job for linux 64
    name = 'build_r_script'
    fd.write('- name: {}-on-linux_64\n'.format(name))
    fd.write('  plan:\n')
    fd.write('  - task: build\n')
    fd.write('    config:\n')
    fd.write('      platform: linux\n')
    fd.write('      image_resource:\n')
    fd.write('        type: docker-image\n')
    fd.write('        source:\n')
    fd.write('          repository: conda/c3i-linux-64\n')
    fd.write('          tag: latest\n')
    fd.write('      params:\n')
    fd.write('        GITHUB_TOKEN: ((common.recipe-repo-access-token))\n')
    fd.write('        GITHUB_USER: SA-PCR-RO\n')
    fd.write('      run:\n')
    fd.write('        path: sh\n')
    fd.write('        args:\n')
    fd.write('        - -exc\n')
    fd.write('        - conda update -y conda-build&& conda config --set add_pip_as_python_dependency\n')
    fd.write('          False&& conda config --add default_channels https://repo.anaconda.com/pkgs/main&&\n')
    fd.write('          conda config --add default_channels https://repo.anaconda.com/pkgs/r&& conda\n')
    fd.write('          info&& set +x&& echo machine github.com login $GITHUB_USER password $GITHUB_TOKEN\n')
    fd.write('          protocol https > ~/.netrc&& set -x &&\n')
    fd.write('          git clone {} &&\n'.format(RrepositoryURL2))
    fd.write('          cd aggregateR && git submodule update --init && git checkout latest_update && cd .. &&\n')
    fd.write('          conda-build --no-anaconda-upload --error-overlinking --R 3.6.1 -c r_test\n')
    fd.write('          --output-folder=output-artifacts --cache-dir=output-source --stats-file=stats/{}-on-linux_64_1564756033.json\n'.format(name))
    fd.write('          --skip-existing --croot .\n')
    # write the list of feedstocks ...
    fd.write(feedstocks)
    fd.write('          \n')
    fd.write('      outputs:\n')
    fd.write('      - name: output-artifacts\n')
    fd.write('      - name: output-source\n')
    fd.write('      - name: stats\n')
    fd.write('  - put: rsync_{}-on-linux_64\n'.format(name))
    fd.write('    params:\n')
    fd.write('      rsync_opts:\n')
    fd.write('      - --archive\n')
    fd.write('      - --no-perms\n')
    fd.write('      - --omit-dir-times\n')
    fd.write('      - --verbose\n')
    fd.write('      - --exclude\n')
    fd.write('      - \'"**/*.json*"\'\n')
    fd.write('      - --exclude\n')
    fd.write('      - \'"**/*.*ml"\'\n')
    fd.write('      - --exclude\n')
    fd.write('      - \'"**/.cache"\'\n')
    fd.write('      sync_dir: output-artifacts\n')
    fd.write('    get_params:\n')
    fd.write('      skip_download: true\n')

def bld_feedstocks_lines(stages):
    rslt = ''
    cnt = do_max_pkg_cnt
    for i, stage in enumerate(stages):
        scount = len(stage)
        j = 0
        elno = 0
        while elno < scount and (cnt == -1 or cnt > 0):
            el = 0
            while elno < scount and el < batch_count_max and (cnt == -1 or cnt > 0):
                p = stage[elno]
                rslt += '         {}/r-{}-feedstock\n'.format(RrepositoryName, p)
                elno += 1
                el += 1
                if cnt != -1:
                    cnt -= 1
            j += 1
        if cnt == 0:
            break
    # end for
    return rslt

def write_out_onosx64(fd, feedstocks):
    # job for linux 64
    name = 'build_r_script'
    fd.write('- name: {}-on-osx\n'.format(name))
    fd.write('  plan:\n')
    fd.write('  - get: rsync-build-pack\n')
    fd.write('    params:\n')
    fd.write('      rsync_opts:\n')
    fd.write('      - --include\n')
    fd.write('      - osx_build_env_latest.zip\n')
    fd.write('      - --exclude\n')
    fd.write('      - \'*\'\n')
    fd.write('      - -v\n')
    fd.write('  - task: build\n')
    fd.write('    config:\n')
    fd.write('      platform: darwin\n')
    fd.write('      params:\n')
    fd.write('        GITHUB_TOKEN: ((common.recipe-repo-access-token))\n')
    fd.write('        GITHUB_USER: SA-PCR-RO\n')
    fd.write('      run:\n')
    fd.write('        path: sh\n')
    fd.write('        args:\n')
    fd.write('        - -exc\n')
    fd.write('        - hostname&& pwd&& mkdir build_env&& unzip -o -q rsync-build-pack/osx_build_env_latest.zip\n')
    fd.write('          -d build_env&& source build_env/bin/activate&& conda-unpack&& conda init&&\n')
    fd.write('          source build_env/etc/profile.d/conda.sh&& conda config --set add_pip_as_python_dependency\n')
    fd.write('          False&& conda config --add default_channels https://repo.anaconda.com/pkgs/main&&\n')
    fd.write('          conda config --add default_channels https://repo.anaconda.com/pkgs/r&& conda\n')
    fd.write('          info&& set +x&& echo machine github.com login $GITHUB_USER password $GITHUB_TOKEN\n')
    fd.write('          protocol https > ~/.netrc&& set -x&& set +x&& echo machine github.com login\n')
    fd.write('          $GITHUB_USER password $GITHUB_TOKEN protocol https > ~/.netrc&& set -x&&\n')
    fd.write('          set +x&& echo machine github.com login $GITHUB_USER password $GITHUB_TOKEN\n')
    fd.write('          protocol https > ~/.netrc&& set -x&& set +x&& echo machine github.com login\n')
    fd.write('          $GITHUB_USER password $GITHUB_TOKEN protocol https > ~/.netrc&& set -x&&\n')
    fd.write('          git clone {} &&\n'.format(RrepositoryURL2))
    fd.write('          cd aggregateR && git submodule update --init && git checkout latest_update && cd .. &&\n')
    fd.write('          conda-build --no-anaconda-upload --error-overlinking --output-folder=output-artifacts\n')
    fd.write('          --cache-dir=output-source --stats-file=stats/{}-on-osx_1564756033.json\n'.format(name))
    fd.write('          --skip-existing -c r_test --R 3.6.1 --croot .\n')
    # write the list of feedstocks ...
    fd.write(feedstocks)
    fd.write('          \n')
    fd.write('      inputs:\n')
    fd.write('      - name: rsync-build-pack\n')
    fd.write('      outputs:\n')
    fd.write('      - name: output-artifacts\n')
    fd.write('      - name: output-source\n')
    fd.write('      - name: stats\n')
    fd.write('  - put: rsync_{}-on-osx\n'.format(name))
    fd.write('    params:\n')
    fd.write('      rsync_opts:\n')
    fd.write('      - --archive\n')
    fd.write('      - --no-perms\n')
    fd.write('      - --omit-dir-times\n')
    fd.write('      - --verbose\n')
    fd.write('      - --exclude\n')
    fd.write('      - \'"**/*.json*"\'\n')
    fd.write('      - --exclude\n')
    fd.write('      - \'"**/*.*ml"\'\n')
    fd.write('      - --exclude\n')
    fd.write('      - \'"**/.cache"\'\n')
    fd.write('      sync_dir: output-artifacts\n')
    fd.write('    get_params:\n')
    fd.write('      skip_download: true\n')

def write_out_bld_job(stages):
    feedstocks = bld_feedstocks_lines(stages)
    # write out 
    with open(f'./pipeline-build-stage.yaml', 'w') as fd:
        fd.write('groups: []\n')
        write_out_resources(fd)
        fd.write('jobs:\n')
        write_out_onlinux64(fd, feedstocks)
        # write_out_onlinux32(fd)
        # write_out_onwin64(fd)
        write_out_onosx64(fd, feedstocks)

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

def write_out_skeleton_script(stages, mode = 'sh'):
    sep_line = ' \\\n    '
    comment_line = '#'
    bash_cmd = ''
    if mode != 'sh':
      sep_line = ' '
      comment_line = 'REM'
      bash_cmd = 'cmd /C '
    cnt = do_max_pkg_cnt

    with open(f'./build-skeleton.{mode}', 'w') as bsd:
        if mode == 'sh':
            bsd.write('#!/bin/bash\n\n')
        bsd.write('{} do imports via conda skeleton cran\n\n'.format(comment_line))
        bsd.write('{} first checkout the R repository\n'.format(comment_line))
        if mode == 'sh':
            bsd.write('rm -rf {}\ngit clone {} --recursive\n'.format(RrepositoryName, RrepositoryURL))
        else:
            # fetch via https as there might be no RSA key for github
            bsd.write('del /F /S /Q {}\ngit clone {} --recursive\n'.format(RrepositoryName, RrepositoryURL2))
        bsd.write('pushd {}\ngit submodule update --init\n'.format(RrepositoryName))
        bsd.write('git checkout latest_update\n')
        for i, stage in enumerate(stages):
            scount = len(stage)
            j = 0
            elno = 0
            while elno < scount and (cnt == -1 or cnt > 0):
                # Write out skeleton creation ...
                bsd.write('{}conda skeleton cran --cran-url={} --output-suffix=-feedstock/recipe {}{}'.format(bash_cmd, CRAN_BASE, do_recursive, sep_line))
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
        bsd.write('{} now write out git commands to list and add new files\n'.format(comment_line))
        bsd.write('git add -N . >new_files_added.txt\n')
        bsd.write('git add .\n')
        bsd.write('git commit -m "Updated CRAN recipes"\n')
        bsd.write('git push latest_update latest_update\n')
        # leave the git repository
        bsd.write('popd\n')

pandas2ri.activate()
readRDS = robjects.r['readRDS']
session = requests.Session()

get_ipython().run_line_magic('matplotlib', 'auto')

anaconda_pkgs = build_anaconda_pkglist(rver = Rver)

built_pkgs = set()

# get the CRAN packages ...
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

write_out_skeleton_script(stages, mode = 'sh')
write_out_skeleton_script(stages, mode = 'bat')
write_out_bld_script(stages, mode = 'sh')
write_out_bld_script(stages, mode = 'bat')
write_out_bld_job(stages)
print("Done.")