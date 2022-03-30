import inspect, sys, os, platform, argparse, json, getpass, subprocess, csv, time
from operator import indexOf
import bigcommerce
from dotenv import dotenv_values
import threading
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
    _tsk.add_argument('-D', '--dry-run', dest='dry', action='store_true')
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
    try:
        out_data = do_api_request(args, args.resource, args.method, args.ids, in_data)
        output(args, out_data, hash=get_store_hash(args, prompt=False))
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
    if out_data:
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

    def fix_product_cats(args, api):
        """
        Removes deleted category IDs in the categories array of all products.
        """
        all_cat_ids = Tasks.get_all_category_ids(args, api)
        products_updated = []
        deleted_cat_ids = []
        i = 1
        for p in api.Products.iterall():
            new_p_cats = [c for c in p.categories] 
            for catid in p.categories:
                if catid not in all_cat_ids:
                    deleted_cat_ids.append(catid)           
                    new_p_cats.remove(catid)
            if len(p.categories) > len(new_p_cats):
                products_updated.append({p.id: {'before': p.categories, 'after': new_p_cats}})
                if not args.dry:
                    p.update(categories=new_p_cats)
            print_req_info("Products", p, i, f"Deleted cats found: {len(deleted_cat_ids)} in {len(products_updated)} products")
            i += 1
        return {'nonexistent_cats': deleted_cat_ids, 'products': products_updated}

    def map(args, api):
        """
        list all of a {Resource} by {unique_attr}:{attr}
        Ex: bigcli t map Products id name
        """
        d = {}
        resource = getattr(api, args.params[0])
        cls = Resources.all_dict[args.params[0]]
        if islistable(cls):
            all = resource.iterall()
            for i in all:
                try:
                    d[getattr(i, args.params[1])] = getattr(i, args.params[2])
                except AttributeError:
                    d[getattr(i, args.params[1])] ='[bigcli]: this obj has no ' + args.params[2]
        else:
            resource = resource.get()
            try:
                d[getattr(resource, args.params[1])] = getattr(resource, args.params[2])
            except AttributeError:
                d[getattr(resource, args.params[1])] ='[bigcli]: this obj has no ' + args.params[2]
        return d

    def prop(args, api):
        """
        Get the value of a resource's property
        Ex: bigcli t prop Categories 53 name
        """
        if len(args.params) < 3:
            return
        resource = getattr(api, args.params[0])
        resource = resource.get(args.params[1])
        attr = args.params[2]
        return getattr(resource, attr)
    
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
def do_api_request(args, resource, method=None, ids=[], data=None, **params):
    """Uses CLI args to make api request and returns the response"""
    hash = get_store_hash(args)
    token = get_auth_token(args)
    api = BigcommerceApi(store_hash=hash, access_token=token, version='latest',
        rate_limiting_management= {'min_requests_remaining':2,
                                    'wait':True,
                                    'callback_function':None})
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
    if inspect.isgenerator(obj) or type(obj) is list:
        obj = iterall(obj)
    elif not inspect.isgenerator(obj) and issubclass(type(obj), ApiResource):
        obj = obj.__json__()
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

    if type(obj) != str: 
        obj = str(obj)

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

def islistable(cls):
    if issubclass(cls, ListableApiResource):
        return True
    if issubclass(cls, ListableApiSubResource):
        return True
    if issubclass(cls, ListableApiSubSubResource):
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
            print_req_info('Items', thing, len(l), f"Getting all {thing.resource_name}...")
            thing = thing.__json__()
        l.append(thing)
    return l

def iterall_threaded(g, l):
    for thing in g:
        if issubclass(type(thing), ApiResource):
            print_req_info('Items', thing, len(l), f"Getting all {thing.resource_name}...")
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

def get_store_hash(args, prompt=True):
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
    return store_hash

def get_auth_token(args, prompt=True):
    if args.prompt_for_creds:
        access_token = input('X-Auth-Token:')
    elif args.use_production:
        access_token = get_cwd_dot_env_value_for('BIGCLI_AUTH_TOKEN_PROD')
        if not access_token:
            access_token = get_tmp_dir_env_value_for('BIGCLI_AUTH_TOKEN_PROD')
        if not access_token:
            access_token = os.environ.get("BIGCLI_AUTH_TOKEN_PROD")
    else:
        access_token = get_cwd_dot_env_value_for('BIGCLI_AUTH_TOKEN_DEV')
        if not access_token:
            access_token = get_tmp_dir_env_value_for('BIGCLI_AUTH_TOKEN_DEV')
        if not access_token:
            access_token = os.environ.get("BIGCLI_AUTH_TOKEN_DEV")
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

def print_req_info(resource_str, resource, i=None, row=None):
    if 'meta' not in resource._connection._last_response.json():
        return
    meta = resource._connection._last_response.json()['meta']
    rl = resource._connection.rate_limit
    """For printing request and rate limit info when iterative over API resources"""
    flush_print_rows([
        row,
        f"Requests remaining: {rl['requests_remaining']} / {rl['requests_quota']}",
        f"Ms until reset:     {rl['ms_until_reset']}",
        f"{resource_str} scanned:   {i} / {meta['pagination']['total']}"
    ])

def flush_print_rows(rows):
    cursor_up = '\x1b[1A'
    for r in rows:
        print(r, sep='', end='\n', flush=True)
    print(cursor_up*(len(rows)+1))


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
    