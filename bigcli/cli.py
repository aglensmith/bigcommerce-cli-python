import inspect, sys, os, argparse, json, getpass
import bigcommerce
from bigcommerce.api import BigcommerceApi
from bigcommerce.resources.base import *
from collections import OrderedDict
from inspect import isclass

"""
bigcli - A CLI tool for BigCommerce.

Author: Austin Smith
"""

# CLI #########################################################################
def main():
    prog             = 'bigcli'
    desc             = 'A BigCommerce CLI tool'
    epi              = 'See README.md for additional usage instructions'
    api_help         = 'make an api request'
    tasks_help       = 'fix stuff'
    resource_help    = 'An API resource (run bigcli a -l to see all)'
    ids_help         = 'specify resource IDs for path'
    prod_help        = 'use prod credentials'
    creds_help       = 'prompt for api credentials'
    list_help        = 'list available api resources'
    pretty_help      = 'pretty print output'
    out_help         = 'specify outfile path, output to stdout'
    in_help          = 'specify infile path, read from stdin'
    method_help      = 'get, all, or delete (default: get)'
    data_help        = 'include json data for request body'
    methods          = ['get', 'all', 'delete', 'create', 'update']
    resources        = Resources.all
    
    parser = argparse.ArgumentParser(prog=prog, description=desc, epilog=epi)
    parser.set_defaults(func=cli)
    
    subparsers = parser.add_subparsers()
    api_parser = subparsers.add_parser('api', aliases=['a'], help=api_help)
    api_parser.add_argument('resource', nargs='?', metavar='resource', choices=resources, help=resource_help)
    api_parser.add_argument('method', metavar='method', nargs='?', choices=methods, default='get', help=method_help)
    api_parser.add_argument('-l', '--list', dest='list', help=list_help, action='store_true')
    api_parser.add_argument('-i', dest='ids', metavar='id', nargs='*', default=[], help=ids_help)
    api_parser.add_argument('-c', '--creds', dest='prompt_for_creds', action='store_true', help=creds_help)
    api_parser.add_argument('-p', '--pretty', dest='pretty_print', action='store_true', help=pretty_help)
    api_parser.add_argument('-o', dest='out', metavar='path', nargs='?', type=argparse.FileType('w'), default=sys.stdout, help=out_help)
    api_parser.add_argument('-in', dest='instream', metavar='path', nargs='?', type=argparse.FileType('r'), default=sys.stdin, help=in_help)
    api_parser.add_argument('-d', dest='data', metavar='json', help=data_help)
    api_parser.add_argument('-P', '--PROD', dest='use_production', action='store_true', help=prod_help)
    api_parser.set_defaults(func=api)

    fix_parser = subparsers.add_parser('task', aliases=['f'], help=tasks_help)
    fix_parser.add_argument('-c', dest='prompt_for_creds', action='store_true', help=creds_help)
    fix_parser.add_argument('-pp', dest='pretty_print', action='store_true', help=pretty_help)
    fix_parser.add_argument('--PROD', dest='use_production', action='store_true', help=prod_help)
    fix_parser.add_argument('task', nargs='?',  choices=Tasks._all())
    fix_parser.set_defaults(func=task)

    args = parser.parse_args()
    args.func(args, parser)

# CLI Default Functions #######################################################
def cli(args, parser):
    parser.print_help()

def api(args, parser):
    if args.list:
        list_api_resources()
        return
    if not args.resource:
        parser.parse_args(['api', '--help'])
        return

    api = init_api_client(args)
    data = {}
    if args.data:
        data = json.loads(args.data)
    if args.instream and not args.instream.isatty():
        data = json.load(args.instream)
    obj = interface(api, args.resource, args.method, args.ids, data)
    output(args, obj)

def task(args, parser):
    api = init_api_client(args)
    output(args, Tasks._all()[args.task](api))

# Classes #####################################################################
class Tasks():

    def _all():
        return {k:v for k,v in vars(Tasks).items() if not k.startswith('_')}

    def get_all_category_ids(api):
        categories = api.Categories.iterall()
        category_ids = [c.id for c in categories]
        return category_ids

    def get_non_existent_categories(self, api):
        categories = self.get_all_category_ids(api)
        non_existent = []
        products = api.Products.iterall()
        for product in products:
            for catid in product.categories:
                if catid not in categories:
                    non_existent.append(catid)
        return non_existent

    def clean_category_assignments(args):
        return

class Resources():

    def map_resources(all, type=ApiResource):
        l = [k for k,v in all.items() if isclass(v) and issubclass(v, type)]
        return [i for i in l if not i.startswith("_") and 'Resource' not in i and 'Mapping' not in i]

    all = vars(bigcommerce.bigcommerce.resources.v2)
    all.update(vars(bigcommerce.bigcommerce.resources.v3))
    all_dict = all
    all = map_resources(all, ApiResource)
    all.sort()

# Helpers #####################################################################
def list_api_resources():
    print('')
    for key in Resources.all:
        cls = Resources.all_dict[key]
        if issubsub(cls) and 'Resource' not in key and 'Mapping' not in key:
            print('{} -ids {{{}}} {{{}}} [id]'.format(key, cls.gparent_key, cls.parent_key))
        elif issub(cls) and 'Resource' not in key and 'Mapping' not in key:
            print('{} -ids {{{}}} [id]'.format(key, cls.parent_key))
        elif isroot(cls) and 'Resource' not in key and 'Mapping' not in key:
            print('{} [-ids [id]]'.format(key))
    print('')

def issubsub(cls):
    if not isclass(cls):
        return False
    if issubclass(cls, ApiSubSubResource):
        return True

def issub(cls):
    if not isclass(cls):
        return False
    if issubsub(cls):
        return False
    if issubclass(cls, ApiSubResource):
        return True

def isroot(cls):
    if not isclass(cls):
        return False
    if issub(cls):
        return False
    if issubsub(cls):
        return False
    if issubclass(cls, ApiResource):
        return True

def interface(api, resource, method=None, ids=[], data=None, **params):
    resource_str = resource
    cls = Resources.all_dict[resource]
    resource = getattr(api, resource)    
    method = {
        'all': 'iterall',
        'get': 'get',
        'delete': 'delete',
        'create': 'create',
        'update': 'update'
    }[method]

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

def validate_ids(cls, resource_str, ids):
    if issubclass(cls, ApiSubSubResource) and (len(ids) < 2 or len(ids) > 3):
        print('\n[bigcli] ids are invalid. {} takes min 2, max 3 ids.'.format(resource_str))
        print('[bigcli] Ex: {} -ids {{{}}} {{{}}} [id]\n'.format(resource_str, cls.gparent_key, cls.parent_key))
        return False
    elif issub(cls) and (len(ids) < 1 or len(ids) > 2):
        print('\n[bigcli] ids are invalid. {}/{{{}}}/{}/[id] takes min 1, max 2 ids.'.format(cls.parent_resource, cls.parent_key, cls.resource_name))
        print('[bigcli] Ex: {} -ids {{{}}} [id]\n'.format(resource_str, cls.parent_key))
        return False
    elif isroot(cls) and len(ids) > 1:
        print('\n[bigcli] ids are invalid. {}/[id] takes max 1 ids.'.format(cls.resource_name))
        print('[bigcli] Ex: {} [-ids [id]]\n'.format(resource_str))
        return False
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

def output(args, obj):
    if inspect.isgenerator(obj) or type(obj) is list:
        args.out.write(iterall(args, obj))
        return
    elif args.pretty_print:
        print('')
        for key, val in obj.items():
            if '_connection' not in key:
                print('- {0}: {1}'.format(key, val))
        print('')
    elif type(obj) is dict:
        print(json.dumps(obj))
    elif not inspect.isgenerator(obj) and issubclass(type(obj), ApiResource):
        obj = obj.__json__()
        args.out.write(json.dumps(obj))

def iterall(args, g):
    l = []
    for thing in g:
        j = thing.__json__()
        l.append(j)
    return json.dumps(l)

def get_store_hash(args):
    if args.prompt_for_creds:
        store_hash = input('Store Hash:')
    elif args.use_production:
        store_hash = os.environ.get("BIGCOMMERCE_STORE_HASH_PROD")
        if not store_hash or len(store_hash) < 3:
            print('\n[bigcli] BIGCOMMERCE_STORE_HASH_PROD envar not found or invalid.')
            store_hash = getpass.getpass(prompt='[bigcli] Enter Store Hash:')
    else:
        store_hash = os.environ.get("BIGCOMMERCE_STORE_HASH_DEV")
        if not store_hash or len(store_hash) < 3:
            print('\n[bigcli] BIGCOMMERCE_STORE_HASH_DEV envar not found or invalid.')
            store_hash = getpass.getpass(prompt='[bigcli] Enter Store Hash:')
    return store_hash

def get_auth_token(args):
    if args.prompt_for_creds:
        access_token = input('X-Auth-Token:')
    elif args.use_production:
        access_token = os.environ.get("BIGCOMMERCE_AUTH_TOKEN_PROD")
        if not access_token or len(access_token) < 10:
            print('\n[bigcli] BIGCOMMERCE_AUTH_TOKEN_PROD envar not found or invalid.')
            access_token = getpass.getpass(prompt='[bigcli] Enter X-Auth-Token:')
    else:
        access_token = os.environ.get("BIGCOMMERCE_AUTH_TOKEN_DEV")
        if not access_token or len(access_token) < 10:
            print('\n[bigcli] BIGCOMMERCE_AUTH_TOKEN_DEV envar not found or invalid.')
            access_token = getpass.getpass(prompt='[bigcli] Enter X-Auth-Token:')
    return access_token

def init_api_client(args):
    hash = get_store_hash(args)
    token = get_auth_token(args)
    return BigcommerceApi(store_hash=hash, access_token=token, version='latest')

def color(text, option):
    choices = {
        "red": '\033[95m',
        "blue": '\033[94m',
        "green": '\033[92m',
        "yellow": '\033[93m',
        "red": '\033[91m',
        "bold": '\033[1m',
        "underline": '\033[4m',
    }
    return choices[option]+ text + '\033[0m'

if __name__ == '__main__':
    main()