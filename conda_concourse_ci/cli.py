import argparse
import logging
import os

from conda_concourse_ci import execute, __version__


def parse_args(parse_this=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--version', action='version',
        help='Show the conda-build version number and exit.',
        version='conda-concourse-ci %s' % __version__)
    sp = parser.add_subparsers(title='subcommands', dest='subparser_name')
    examine_parser = sp.add_parser('examine', help='examine path for changed recipes')
    examine_parser.add_argument('base_name',
                                help="name of your project, to distinguish it from other projects")
    examine_parser.add_argument("path", default='.', nargs='?',
                        help="path in which to examine/build/test recipes")
    examine_parser.add_argument('--folders', default=[], nargs="+",
                        help="Rather than determine tree from git, specify folders to build")
    examine_parser.add_argument('--steps', type=int,
                        help=("Number of downstream steps to follow in the DAG when "
                              "computing what to test.  Used for making sure that an "
                              "update does not break downstream packages.  Set to -1 "
                              "to follow the complete dependency tree."),
                        default=0),
    examine_parser.add_argument('--max-downstream', default=5, type=int,
                        help=("Limit the total number of downstream packages built.  Only applies "
                              "if steps != 0.  Set to -1 for unlimited."))
    examine_parser.add_argument('--git-rev',
                        default='HEAD',
                        help=('start revision to examine.  If stop not '
                              'provided, changes are THIS_VAL~1..THIS_VAL'))
    examine_parser.add_argument('--stop-rev', default=None,
                        help=('stop revision to examine.  When provided,'
                              'changes are git_rev..stop_rev'))
    examine_parser.add_argument('--test', action='store_true',
                        help='test packages (instead of building AND testing them)')
    examine_parser.add_argument('--matrix-base-dir',
                        help='path to matrix configuration, if different from recipe path')
    examine_parser.add_argument('--output-dir', help="folder where output plan and recipes live",
                                default='../output')

    submit_parser = sp.add_parser('submit', help="submit plan director to configured server")
    submit_parser.add_argument('base_name',
                               help="name of your project, to distinguish it from other projects")
    submit_parser.add_argument('--pipeline-name', help="name for the submitted pipeline",
                               default='{base_name} plan director')
    submit_parser.add_argument('--pipeline-file', default='plan_director.yml',
                               help="path to pipeline .yml file containing plan")
    submit_parser.add_argument('--config-root-dir',
                               help="path containing config.yml and matrix definitions")
    submit_parser.add_argument('--src-dir', help="folder where git repo of source code lives",
                               default=os.getcwd())
    submit_parser.add_argument('--private', action='store_false',
                        help='hide build logs (overall graph still shown in Concourse web view)',
                        dest='public')

    bootstrap_parser = sp.add_parser('bootstrap',
                                     help="create default configuration files to help you start")
    bootstrap_parser.add_argument('base_name',
                            help="name of your project, to distinguish it from other projects")

    one_off_parser = sp.add_parser('one-off',
                                   help="submit local recipes and plan to configured server")
    one_off_parser.add_argument('pipeline_label',
                                help="name of your project, to distinguish it from other projects")
    one_off_parser.add_argument('folders', nargs="+",
                                help=("Specify folders, relative to --recipe-root-dir, to upload "
                                      "and build"))
    one_off_parser.add_argument('--recipe-root-dir', default=os.getcwd(),
                                help="path containing recipe folders to upload")
    one_off_parser.add_argument('--config-root-dir',
                                help="path containing config.yml and matrix definitions")
    one_off_parser.add_argument('--private', action='store_false',
                        help='hide build logs (overall graph still shown in Concourse web view)',
                        dest='public')
    one_off_parser.add_argument('--rebuild-world', action='store_true',
                                help=("Recurse up dependency tree, rebuilding all recipes from"
                                      "specified packages"))
    return parser.parse_args(parse_this)


def main(args=None):
    if not args:
        args = parse_args()
    else:
        args = parse_args(args)

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.subparser_name == 'submit':
        args_dict = args.__dict__
        if not args_dict.get('config_root_dir'):
            args_dict['config_root_dir'] = args_dict['base_name']
        execute.submit(**args_dict)
    elif args.subparser_name == 'bootstrap':
        execute.bootstrap(**args.__dict__)
    elif args.subparser_name == 'examine':
        execute.compute_builds(**args.__dict__)
    elif args.subparser_name == 'one-off':
        execute.submit_one_off(**args.__dict__)
    else:
        # this is here so that if future subcommands are added, you don't forget to add a bit
        #     here to enable them.
        raise NotImplementedError("Command {} is not implemented".format(args.subparser_name))
