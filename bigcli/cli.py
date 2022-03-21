import inspect, sys, os, platform, argparse, json, getpass, subprocess, csv
import webbrowser
import bigcommerce
from dotenv import dotenv_values
from pathlib import Path
from bigcommerce.api import BigcommerceApi
from bigcommerce.resources.base import *
from collections import OrderedDict
from inspect import isclass

"""
bigcli - A CLI tool for BigCommerce.

Author: Austin Smith
"""

def main():
    v = dotenv_values(dotenv_path=os.path.join(os.getcwd(), '.env'))
    parser = get_parser()
    args = parser.parse_args()
    args.func(args, parser)

# Argument parsers ############################################################
def get_parser():
    prog             = 'bigcli'
    desc             = 'A BigCommerce CLI tool'
    epi              = 'See README.md for additional usage instructions'
    api_help         = 'make API requests'
    tasks_help       = 'run pre-programmed tasks'
    file_help        = 'list .bigcli files'
    resource_help    = 'An API resource (run bigcli a -l to see all)'
    ids_help         = 'specify resource IDs for path'
    prod_help        = 'use production credential env vars'
    creds_help       = 'get prompted for api credentials'
    list_help        = 'list available api resources'
    pretty_help      = 'minify json output'
    out_help         = 'specify outfile'
    in_help          = 'specify file path to request body json'
    method_help      = 'get, all, update, or delete'
    data_help        = 'include json data for request body'
    attr_help        = 'specify a single resource attribute to'
    methods          = ['get', 'all', 'delete', 'create', 'update']
    fil_o_help       = 'open all .bigcli files'
    resources        = Resources.all

    __parser   = argparse.ArgumentParser(prog=prog, description=desc, epilog=epi)
    __parser.set_defaults(func=cli)

    # shared arguments
    _shr = argparse.ArgumentParser(add_help=False)
    
    in_group = _shr.add_argument_group('input options')
    in_group.add_argument('-d', dest='data', help=data_help)
    in_group.add_argument('-in', dest='instream', metavar='path', nargs='?', type=argparse.FileType('r'), default=sys.stdin, help=in_help)
    
    out_group = _shr.add_argument_group('output options')
    out_group.add_argument('-m', '--minify', dest='pretty_print', action='store_false', help=pretty_help)
    out_group.add_argument('-o', dest='out', nargs='?', type=argparse.FileType('w'), default=sys.stdout, help=out_help)
    out_group.add_argument('-a', dest='attr', metavar='attribute', help=attr_help)


    cred_group = _shr.add_argument_group('credentials options')
    cred_group.add_argument('-c', '--creds', dest='prompt_for_creds', action='store_true', help=creds_help)
    cred_group.add_argument('-P', '--PROD', dest='use_production', action='store_true', help=prod_help)

    subs = __parser.add_subparsers(title='Commands')
    _api = subs.add_parser('api',   aliases=['a'], help=api_help,   parents=[_shr])
    _tsk = subs.add_parser('task',  aliases=['t'], help=tasks_help, parents=[_shr])
    _fil = subs.add_parser('files', aliases=['f'], help=file_help, parents=[])
    _api.set_defaults(func=api)
    _fil.set_defaults(func=files)
    _tsk.set_defaults(func=tasks)

    _api.add_argument('-l', '--list', dest='list', help=list_help, action='store_true')


    # api only arguments
    req_group = _api.add_argument_group('request')
    req_group.add_argument('resource', nargs='?', metavar='resource', choices=resources, help=resource_help)
    req_group.add_argument('method', metavar='method', nargs='?', choices=methods, default='get', help=method_help)
    req_group.add_argument('-i', dest='ids', metavar='id', nargs='*', default=[], help=ids_help)

    # file only orguments
    _fil.add_argument('-o', action='store_true', help=fil_o_help)

    # task only arguments
    _tsk.add_argument('-l', '--list', dest='list', help=list_help, action='store_true')
    _tsk.add_argument('task', nargs='?',  choices=Tasks._all())
    _tsk.add_argument('params', nargs='*')
    return __parser

# Argument parser functions ###################################################
def cli(args, parser):
    parser.print_help()

def api(args, parser):
    if args.list:
        return list_api_resources()
    if args.data:
        in_data = json.loads(args.data)
    else:
        in_data = {}
    if args.data and args.instream and not args.instream.isatty():
        in_data = json.load(args.instream)
    if not args.data and (args.instream and not args.instream.isatty()):
        in_data = json.load(args.instream)
    if not args.resource:
        return parser.parse_args(['api', '--help'])    
    if not validate_ids(Resources.all_dict[args.resource], args.resource, args.ids):
        return
    hash = get_store_hash(args)
    token = get_auth_token(args)
    client = BigcommerceApi(store_hash=hash, access_token=token, version='latest')
    try:
        out_data = do_api_request(client, args.resource, args.method, args.ids, in_data)
        output(args, out_data, hash)
    except bigcommerce.exception.ClientRequestException as e:
        print('bigcommerce.exception.ClientRequestException:\n')
        print(e)
        if 'response' in vars(e) and 'url' in vars(e.response):
            print('\nFull URL: ' + e.response.url + '\n')     

def files(args, parser): 
    if args.o and tmp_path_exists():
        open_files_using_default_editor()
    else:
        list_files()

def tasks(args, parser):
    if args.list:
        for k,v in Tasks._all().items():
            print(k)
            print(v.__doc__)
        return
    hash = get_store_hash(args)
    token = get_auth_token(args)
    client = BigcommerceApi(store_hash=hash, access_token=token, version='latest')
    out_data = Tasks._all()[args.task](args, client)
    output(args, out_data, hash)

# Tasks #######################################################################
class Tasks():

    def _all():
        return {k:v for k,v in vars(Tasks).items() if not k.startswith('_')}

    def get_all_category_ids(args, api):
        """
        list all category IDs
        """
        categories = api.Categories.iterall()
        category_ids = [c.id for c in categories]
        return category_ids

    def non_existent_categories(args, api):
        """
        list deleted category IDs assigned to products
        """
        categories = Tasks.get_all_category_ids(api)
        non_existent = []
        products = api.Products.iterall()
        for product in products:
            for catid in product.categories:
                if catid not in categories:
                    non_existent.append(catid)
        return non_existent

    def map(args, api):
        """
        list all of a {Resource} by {unique_attr}:{attr}
        Ex: bigcli t map Products id name
        """
        d = {}
        all = getattr(api, args.params[0]).iterall()
        AttributeError
        for i in all:
            try:
                d[getattr(i, args.params[1])] = getattr(i, args.params[2])
            except AttributeError:
                d[getattr(i, args.params[1])] ='[bigcli]: this obj has no ' + args.params[2]
        return d
    
    def widget_templates(args, api):
        """
        list widget templates by [uuid], name
        Ex: bigcli t widget_templates
        """
        templates = api.WidgetTemplates.iterall()
        return {t['uuid']:t['name'] for t in templates}

    def widget_template_html(args, api):
        """
        get a widget template's html by [uuid]
        Ex: bigcli t widget_template_html 
        """
        if len(args.params) < 1:
            args.pretty_print = True
            output(args, Tasks.widget_templates(args, api))
            uuid = input ('\n [bigcli] UUID: ')
            args.params.append(uuid)
        template = api.WidgetTemplates.get(args.params[0])
        return template.template

    def widget_template_schema(args, api):
        """
        get a widget template's schema by [uuid]
        Ex: bigcli t widget_template_schema [uuid]
        """
        if len(args.params) < 1:
            args.pretty_print = True
            output(args, Tasks.widget_templates(args, api))
            uuid = input ('\n [bigcli] UUID: ')
            args.params.append(uuid)
        template = api.WidgetTemplates.get(args.params[0])
        return template.schema

# Helpers #####################################################################
def do_api_request(api, resource, method=None, ids=[], data=None, **params):
    """Uses CLI args to make api request and returns the response"""
    resource_str = resource
    cls = Resources.all_dict[resource]
    resource = getattr(api, resource)
    
    if method == 'all':
        method = 'iterall'

    if not validate_ids(cls, resource_str, ids):
        return

    if method == 'update':
        if method and len(ids) == 0:
            return getattr(resource, 'get')().update(**data)
        if method and len(ids) == 1:
            return getattr(resource, 'get')(ids[0]).update(**data)
        if method and len(ids) == 2:
            return getattr(resource, 'get')(ids[0], ids[1]).update(**data)
        if method and len(ids) == 3:
            return getattr(resource, 'get')(ids[0], ids[1], ids[2]).update(**data)
    if method != 'delete':
        if method and len(ids) == 0:
            return getattr(resource, method)(**data)
        if method and len(ids) == 1:
            return getattr(resource, method)(ids[0], **data)
        if method and len(ids) == 2:
            return getattr(resource, method)(ids[0], ids[1], **data)
        if method and len(ids) == 3:
            return getattr(resource, method)(ids[0], ids[1], ids[2], **data)
    if method == 'delete':
        if not confirm(api, resource_str, ids):
            print('\n[bigcli] Delete aborted.')
            return
        if method and len(ids) == 0:
            return getattr(resource, 'get')().delete_all()
        if method and len(ids) == 1:
            return getattr(resource, 'get')(ids[0]).delete()
        if method and len(ids) == 2:
            return getattr(resource, 'get')(ids[0], ids[1]).delete()
        if method and len(ids) == 3:
            return getattr(resource, 'get')(ids[0], ids[1], ids[2]).delete()

def output(args, obj, hash=None):
    """Writes obj to file or stdout depending on args"""

    # make we obj is a dict
    if inspect.isgenerator(obj) or type(obj) is list:
        obj = iterall(obj)
    elif not inspect.isgenerator(obj) and issubclass(type(obj), ApiResource):
        obj = obj.__json__()

    # we have a dict now, go ahead and serialize
    if args.pretty_print and (args.out is None or args.out.name != 'csv'):
        obj = json.dumps(obj, indent=4)


    # if -o, but no
    make_tmp_dirs_if_not_exist(hash)

    filename = ''

    if 'resource' in args and args.resource and hash:
        filename = hash + '-' + args.resource + '-' + args.method
    elif hash:
        filename = hash + '-' + args.task

    if not args.out:
        args.out = open(tmp_path() + '/' + '_last.json', 'w')
        args.out.write(obj)
        args.out = open(tmp_path() + '/' + filename + '.json', 'w')
    if args.out.name == 'json':
        args.out = open(tmp_path() + '/' + filename + '.json', 'w')
    if args.out.name == 'html':
        args.out = open(tmp_path() + '/' + filename + 'html', 'w')
    if args.out.name == 'txt':
        args.out = open(tmp_path() + '/' + filename + '.txt', 'w')
    if args.out.name == 'csv':
        tocsv(obj, tmp_path() + '/' + filename + '.csv')
        return 

    args.out.write(obj)

def tmp_path(hash=None):
    if hash:
        return tmp_path() + '/' + hash
    return str(Path.home()) + '/.bigcli'

def make_tmp_dirs_if_not_exist(hash):
    if not tmp_path_exists():
        os.mkdir(tmp_path())

def tmp_path_exists(hash=None):
    if hash:
        return os.path.exists(tmp_path() + '/' + hash)
    return os.path.exists(tmp_path())

def list_files():
    for file in os.listdir(tmp_path()):
        print("{}/{}".format(tmp_path(), file))

def open_files_using_default_editor():
    editor = os.getenv('EDITOR')
    path = tmp_path() + '/*'
    if platform.system() == "Darwin": 
        os.system('open {}'.format(path))
    elif editor:
        os.system('%s %s' % (os.getenv('EDITOR'), path))
    else:
        print('[bigcli] Can\'t open files because EDITOR env var not set.')

def list_api_resources():
    for key in Resources.all:
        cls = Resources.all_dict[key]
        if issubsub(cls) and 'Resource' not in key and 'Mapping' not in key:
            print('{} -ids {{{}}} {{{}}} [id]'.format(key, cls.gparent_key, cls.parent_key))
        elif issub(cls) and 'Resource' not in key and 'Mapping' not in key:
            print('{} -ids {{{}}} [id]'.format(key, cls.parent_key))
        elif isroot(cls) and 'Resource' not in key and 'Mapping' not in key:
            print('{} [-ids [id]]'.format(key))

def issubsub(cls):
    """returns true if cls is a bigcommerce sub sub resource"""
    if not isclass(cls):
        return False
    if issubclass(cls, ApiSubSubResource):
        return True

def issub(cls):
    """returns true if cls is a bigcommerce api sub resource"""
    if not isclass(cls):
        return False
    if issubsub(cls):
        return False
    if issubclass(cls, ApiSubResource):
        return True

def isroot(cls):
    """returns true if cls passed in is a bigcommerce api root-level resource"""
    if not isclass(cls):
        return False
    if issub(cls):
        return False
    if issubsub(cls):
        return False
    if issubclass(cls, ApiResource):
        return True

def validate_ids(cls, resource_str, ids):
    error   = '\n[bigcli] ids are invalid. {} takes min {}, max {} ids.'
    example = '[bigcli] Ex: {} -i {{{}}} {{{}}} [id]\n'
    if issubclass(cls, ApiSubSubResource) and (len(ids) < 2 or len(ids) > 3):
        print(error.format(resource_str, 2, 3))
        print(example.format(resource_str, cls.gparent_key, cls.parent_key))
    elif issub(cls) and (len(ids) < 1 or len(ids) > 2):
        print(error.format(resource_str, 1, 2))
        print('[bigcli] Ex: {} -i {{{}}} [id]\n'.format(resource_str, cls.parent_key))
    elif isroot(cls) and len(ids) > 1:
        print(error.format(cls.resource_name, 0, 1))
        print('[bigcli] Ex: {} [-i [id]]\n'.format(resource_str))
    else: 
        return True

def confirm(api, resource_str, ids=[]):
        domain = color(api.Store.all().domain, 'blue')
        action = color('DELETE', 'red')
        if len(ids) > 0:
            id = color(ids[-1], 'red')
            print("\n{} {} {} on {}?".format(action, resource_str, id, domain))
            check = 'delete it now'
            return input("Type '{}': ".format(check)) == check
        else:
            print("\n{} {} {} on {}?".format(action, 'ALL', resource_str, domain))
            check = "delete all {} on {}".format(resource_str, domain)
            return input("Type '{}': ".format(check)) == check

def iterall(g):
    l = []
    for thing in g:
        if issubclass(type(thing), ApiResource):
            thing = thing.__json__()
        l.append(thing)
    return l

def init_api_client(args):
    hash = get_store_hash(args)
    token = get_auth_token(args)
    return BigcommerceApi(store_hash=hash, access_token=token, version='latest')

def get_cwd_dot_env_value_for(var):
    values = dotenv_values(dotenv_path=os.path.join(os.getcwd(), '.env'))
    if var in values:
        return values[var]

def get_tmp_dir_env_value_for(var):
    values = dotenv_values(dotenv_path=os.path.join(tmp_path(), '.env'))
    if var in values:
        return values[var]

def get_store_hash(args):
    if args.prompt_for_creds:
        store_hash = input('Store Hash:')
    elif args.use_production:
        store_hash = get_cwd_dot_env_value_for('BIGCLI_STORE_HASH_PROD')
        if not store_hash:
            store_hash = get_tmp_dir_env_value_for('BIGCLI_STORE_HASH_PROD')
        if not store_hash:
            store_hash = os.environ.get("BIGCLI_STORE_HASH_PROD")
        if not store_hash or len(store_hash) < 4:
            store_hash = getpass.getpass(prompt='[bigcli] Enter Store Hash:')
    else:
        store_hash = get_cwd_dot_env_value_for('BIGCLI_STORE_HASH_DEV')
        if not store_hash:
            store_hash = get_tmp_dir_env_value_for('BIGCLI_STORE_HASH_DEV')
        if not store_hash:
            store_hash = os.environ.get("BIGCLI_STORE_HASH_DEV")
        if not store_hash or len(store_hash) < 4:
            store_hash = getpass.getpass(prompt='[bigcli] Enter Store Hash:')
    return store_hash

def get_auth_token(args):
    if args.prompt_for_creds:
        access_token = input('X-Auth-Token:')
    elif args.use_production:
        access_token = get_cwd_dot_env_value_for('BIGCLI_AUTH_TOKEN_PROD')
        if not access_token:
            access_token = get_tmp_dir_env_value_for('BIGCLI_AUTH_TOKEN_PROD')
        if not access_token:
            access_token = os.environ.get("BIGCLI_AUTH_TOKEN_PROD")
        if not access_token or len(access_token) < 10:
            print('\n[bigcli] BIGCLI_AUTH_TOKEN_PROD envar not found or invalid.')
            access_token = getpass.getpass(prompt='[bigcli] Enter X-Auth-Token:')
    else:
        access_token = get_cwd_dot_env_value_for('BIGCLI_AUTH_TOKEN_DEV')
        if not access_token:
            access_token = get_tmp_dir_env_value_for('BIGCLI_AUTH_TOKEN_DEV')
        if not access_token:
            access_token = os.environ.get("BIGCLI_AUTH_TOKEN_DEV")
        access_token = os.environ.get("BIGCLI_AUTH_TOKEN_DEV")
        if not access_token or len(access_token) < 10:
            print('\n[bigcli] BIGCLI_AUTH_TOKEN_DEV envar not found or invalid.')
            access_token = getpass.getpass(prompt='[bigcli] Enter X-Auth-Token:')
    return access_token

def tocsv(dict_list, filename):
    """writes specified fields from list of dicts to csv"""
    keys = [k for k in dict_list[0].keys()]
    
    with open(filename, 'a') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=keys, lineterminator='\n')
        writer.writeheader()
        for dict in dict_list:
            writer.writerow(dict)

def color(text, option):
    return { "red": '\033[95m', "blue": '\033[94m',"green": '\033[92m', 
    "yellow": '\033[93m', "red": '\033[91m'}[option] + text + '\033[0m'

class Resources():

    def map_resources(all, type=ApiResource):
        l = [k for k,v in all.items() if isclass(v) and issubclass(v, type)]
        return [i for i in l if not i.startswith("_") and 'Resource' not in i and 'Mapping' not in i]

    all = vars(bigcommerce.bigcommerce.resources.v2)
    all.update(vars(bigcommerce.bigcommerce.resources.v3))
    all_dict = all
    all = map_resources(all, ApiResource)
    all.sort()

if __name__ == '__main__':
    main()
    