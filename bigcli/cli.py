"""
bigcli.py - A CLI tool for BigCommerce.

Author: Austin Smith
"""

# argparse for option parsing: https://docs.python.org/3/library/argparse.html

import inspect
import os
from inspect import isclass
import argparse
import bigcommerce
from bigcommerce.resources.base import *
from collections import OrderedDict
import json 
import getpass

class PromptAction(argparse.Action):
    def __init__(self,
             option_strings,
             dest=None,
             nargs=0,
             default=None,
             required=False,
             type=None,
             metavar=None,
             help=None):
        super(PromptAction, self).__init__(
             option_strings=option_strings,
             dest=dest,
             nargs=nargs,
             default=default,
             required=required,
             metavar=metavar,
             type=type,
             help=help)

    def __call__(self, parser, args, values, option_string=None):
        hash = getpass.getpass(prompt='Store Hash: ')
        token = getpass.getpass(prompt='X-Auth-Token: ')
        setattr(args, 'hash', hash)
        setattr(args, 'token', token)

def output(args, obj):
    if type(obj) is list or inspect.isgenerator(obj):
        print_all(obj)
        return
    if args.format == 'pp':
        print('\n')
        print(type(obj).__name__)
        for key, val in obj.items():
            if '_connection' not in key:
                print('- {0}: {1}'.format(key, val))
        print('\n')
    else:
        obj = obj.__json__()
        print(json.dumps(obj))

def print_all(g):
    l = []
    for thing in g:
        j = thing.__json__()
        l.append(OrderedDict(sorted(j.items(), key=lambda t: t[0])))
    print(json.dumps(l))

class Resources():
    """
    Maps bigcommerce resource class name to resource_name and ar
    """

    def map_resources(all, type=ApiResource):
        """Returns all bigcommerce.resources that are sublcasses of type mapped to their resource_name. Ex: {'products': 'ProductsV3'}"""
        l = [k for k,v in all.items() if isclass(v) and issubclass(v, type)]
        return [i for i in l if not i.startswith("_") and 'Resource' not in i and 'Mapping' not in i]


    all = vars(bigcommerce.bigcommerce.resources.v2)
    all.update(vars(bigcommerce.bigcommerce.resources.v3))
    creatable = map_resources(all, CreateableApiResource)
    listable = map_resources(all, ListableApiResource)
    updateable = map_resources(all, UpdateableApiResource)
    deleteable = map_resources(all, DeleteableApiResource)
    collection_deleteable = map_resources(all, CollectionDeleteableApiResource)
    all = map_resources(all, ApiResource)
    all.sort()


def init_store(args):
    if args.environment == 'prod':
        store_hash = os.environ.get("BC_PROD_STORE_HASH", args.hash)
        access_token = os.environ.get("BC_PROD_AUTH_TOKEN", args.token)
    else:
        store_hash = os.environ.get("BC_SANDBOX_STORE_HASH", args.hash)
        access_token = os.environ.get("BC_SANDBOX_AUTH_TOKEN", args.token)

    if not store_hash or len(store_hash) < 3:
        store_hash = getpass.getpass(prompt='Store Hash: ')
    if not access_token or len(access_token) < 10:
        access_token = getpass.getpass(prompt='X-Auth-Token: ')

    return bigcommerce.api.BigcommerceApi(store_hash=store_hash, access_token=access_token, version='latest')

# CLI Default Functions #########################################################

def interface(api, resource, method=None, ids=None, data=None, **params):
    if method and len(ids) == 0:
        return getattr(getattr(api, resource), method)()
    if method and ids and len(ids) == 1:
        return getattr(getattr(api, resource), method)(ids[0])
    if method and ids and len(ids) == 2:
        return getattr(getattr(api, resource), method)(ids[0], ids[1])
    if method and ids and len(ids) == 3:
        return getattr(getattr(api, resource), method)(ids[0], ids[1], ids[2])
    return getattr(getattr(api, resource), 'iterall')()

def cli(args, parser):
    if args.list:
        print('\n=========== Resources ====================')
        for i in Resources.all:
            print(i)
        print('\n==========================================')
        return
    else:
        parser.print_help()

def create(args):
    return

def get(args):
    store = init_store(args)
    interface()

def all(args):
    store = init_store(args)
    store_resource = getattr(store, Resources.listable[args.resource])
    obj = store_resource.all()
    output(args, obj)

def iterall(args):
    store = init_store(args)
    store_resource = getattr(store, Resources.listable[args.resource])
    g = store_resource.iterall()
    print_all(g)

def delete(args):
    store = init_store(args)
    domain = color(store.Store.all().domain, 'blue')
    env = args.environment
    resource = args.resource
    id = color(args.id, 'red')
    action = color('DELETE', 'red')
    store_resource = getattr(store, Resources.deleteable[args.resource])
    prompt = "\n{} {} {} on {}?".format(action, resource, id, domain)
    print(prompt)
    choice = input("Type 'delete it now': ")
    
    if choice == 'delete it now':
        r = store_resource.get(args.id).delete()
        print(r)
    print('Aborted.\n')

def store(args, parser):
    store = init_store(args)
    # if args.all:
    obj = interface(store, args.r, 'get', args.ids)
    output(args, obj)

def collection_delete():
    return

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

# CLI #########################################################################
def get_parser():
    """returns an argparse argument parser"""
    
    parser = argparse.ArgumentParser(
        prog="psecli", 
        description='A BigCommerce CLI tool',
        epilog="See README.md for additional usage instructions.")

    # help text
    create_help      = 'create a resource'
    get_help         = 'get a single resource'
    all_help         = 'get a page of a resource'
    iterall_help     = 'get all of a resource'
    delete_help      = 'delete a resource'
    store_hash_help  = 'store hash (ex: dalk23kk)' 
    resource_help    = 'API resource (ex: Product)'
    id_help          = 'resource ID'
    environment_help = 'Use dev or prod credentials.'
    prompt_help      = 'get prompted to enter API credentials'
    list_help        = 'list available api resources'
    format_help      = ''
    api_help         = 'make an api request'

    # main parser
    parser.add_argument('-v', action='version', version='%(prog)s 1.0')
    parser.set_defaults(func=cli)
    parser.add_argument('-l', dest='list', help=list_help, action='store_true')
    subparsers = parser.add_subparsers()

    base_parser = argparse.ArgumentParser(add_help=False)
    base_parser.add_argument('-e', dest='environment', choices=['dev', 'prod'], default='dev', help=environment_help)
    base_parser.add_argument('-p', dest='prompt', action=PromptAction, help=prompt_help)
    base_parser.add_argument('-s', dest='hash', help=store_hash_help)
    base_parser.add_argument('-t', dest='token', help=store_hash_help)
    base_parser.add_argument('-f', dest='format', help=format_help, choices=['pp', 'raw'], default='raw')

    # create subparser
    api_parser = subparsers.add_parser('api', aliases=['a'], parents=[base_parser], help=api_help)
    api_parser.set_defaults(func=store)
    api_parser.add_argument('r', metavar='Resource', help=resource_help, choices=Resources.all)
    api_parser.add_argument('--ids', '-i', nargs='*', type=int, default=None)

    # create subparser
    # create_parser = subparsers.add_parser('create', aliases=['c'], help=create_help, parents=[base_parser])
    # create_parser.set_defaults(func=create)
    # create_parser.add_argument('resource', metavar='resource', choices=Resources.creatable)

    # get subparser
    # get_parser = subparsers.add_parser('get', aliases=['d'], help=delete_help, parents=[base_parser])
    # get_parser.set_defaults(func=get)
    # get_parser.add_argument('resource', metavar='resource', choices=Resources.listable, help=resource_help)
    # get_parser.add_argument('id', help=id_help)

    # all subparser
    # all_parser = subparsers.add_parser('all', help=all_help, aliases=['a'], parents=[base_parser])
    # all_parser.set_defaults(func=all)
    # all_parser.add_argument('resource', metavar='resource', choices=Resources.listable, help=resource_help)

    # iterall subparser
    # iterall_parser = subparsers.add_parser('iterall', aliases=['l'], help=iterall_help, parents=[base_parser])
    # iterall_parser.set_defaults(func=iterall)
    # iterall_parser.add_argument('resource', metavar='resource', choices=Resources.listable, help=resource_help)

    # delete subparser
    # delete_parser = subparsers.add_parser('delete', aliases=['d'], help=delete_help, parents=[base_parser])
    # delete_parser.set_defaults(func=delete)
    # delete_parser.add_argument('resource', metavar='resource', choices=Resources.deleteable, help=resource_help)
    # delete_parser.add_argument('id', help=id_help)

    return parser

def main():
    parser = get_parser()
    args = parser.parse_args()
    args.func(args, parser)

if __name__ == '__main__':
    main()
    