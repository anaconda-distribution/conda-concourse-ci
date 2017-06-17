import logging
import os

import pytest

from conda_concourse_ci import cli


def test_argparse_input():
    # calling with no arguments goes to look at sys.argv, which is our arguments to py.test.
    with pytest.raises((SystemExit, NotImplementedError)):
        cli.main()


def test_submit(mocker):
    mocker.patch.object(cli.execute, 'submit')
    args = ['submit', 'frank']
    cli.main(args)
    cli.execute.submit.assert_called_once_with(base_name='frank', config_root_dir=None, debug=False,
                                               pipeline_file='plan_director.yml',
                                               pipeline_name='{base_name} plan director',
                                               public=True, src_dir=os.getcwd(),
                                               subparser_name='submit')


def test_submit_without_base_name_raises():
    with pytest.raises(SystemExit):
        args = ['submit']
        cli.main(args)


def test_bootstrap(mocker):
    mocker.patch.object(cli.execute, 'bootstrap')
    args = ['bootstrap', 'frank']
    cli.main(args)
    cli.execute.bootstrap.assert_called_once_with(base_name='frank', debug=False,
                                                  subparser_name='bootstrap')


def test_bootstrap_without_base_name_raises():
    with pytest.raises(SystemExit):
        args = ['bootstrap']
        cli.main(args)


def test_examine(mocker):
    mocker.patch.object(cli.execute, 'compute_builds')
    args = ['examine', 'frank']
    cli.main(args)
    cli.execute.compute_builds.assert_called_once_with(base_name='frank', debug=False, folders=[],
                                                       git_rev='HEAD', matrix_base_dir=None,
                                                       max_downstream=5, path='.', steps=0,
                                                       stop_rev=None, subparser_name='examine',
                                                       test=False)


def test_examine_without_base_name_raises():
    with pytest.raises(SystemExit):
        args = ['examine']
        cli.main(args)


def test_consolidate(mocker):
    mocker.patch.object(cli.execute, 'consolidate_packages')
    args = ['consolidate', 'linux-64']
    cli.main(args)
    cli.execute.consolidate_packages.assert_called_once_with(subdir='linux-64', debug=False,
                                                             path='.', subparser_name='consolidate')


def test_consolidate_without_subdir_raises():
    with pytest.raises(SystemExit):
        args = ['consolidate']
        cli.main(args)


# not sure what the right syntax for this is yet.  TODO.
@pytest.mark.xfail
def test_logger_sets_debug_level(mocker):
    mocker.patch.object(cli.execute, 'submit')
    cli.main(['--debug', 'submit', 'frank'])
    assert logging.getLogger().isEnabledFor(logging.DEBUG)


def test_bad_command_raises():
    with pytest.raises(SystemExit):
        cli.main([''])


def test_build_subcommand(mocker):
    mocker.patch.object(cli.installer, 'create_jobs')
    args = ['build', '-p', 'linux']
    cli.main(args)
    cli.installer.create_jobs.assert_called_once_with(platform='linux', config=None,
                                                      debug=False, subparser_name='build')