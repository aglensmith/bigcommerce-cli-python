import inspect, sys, os, platform, argparse, json, getpass, csv
import bigcommerce
from dotenv import dotenv_values
from pathlib import Path
from bigcommerce.api import BigcommerceApi
from bigcommerce.resources.base import *
from inspect import isclass

"""
bigcli - Interact with BigCommerce stores via command line.

Author: https://github.com/aglensmith
"""

def main():
    parser = get_parser()
    args = parser.parse_args()
    args.func(args, parser)

# Argument parsers ############################################################
def get_parser():
    prog             = 'bigcli'
    desc             = 'Interact with BigCommerce stores via command line'
    epi              = 'See README.md for additional usage instructions'
    api_help         = 'make API requests'
    tasks_help       = 'run miscellaneous pre-programmed tasks'
    file_help        = 'list .bigcli files'
    resource_help    = 'An API resource (run bigcli a -l to see all)'
    ids_help         = 'specify resource IDs for path'
    creds_help       = 'get prompted for api credentials'
    list_help        = 'list available api resources'
    pretty_help      = 'minify json output'
    out_help         = 'specify outfile'
    in_help          = 'specify file path to request body json'
    method_help      = 'get, all, update, or delete'
    data_help        = 'include json data for request body'
    methods          = ['get', 'all', 'iterall', 'delete', 'create', 'update']
    fil_o_help       = 'open all .bigcli files'
    widgets_help     = 'interact with store widgets'
    themes_help      = 'interact with store themes'
    settings_help    = 'interact with store settings'
    env_help         = 'create or open ~/.bigcli/.env'
    resources        = Resources.all

    __parser   = argparse.ArgumentParser(prog=prog, description=desc, epilog=epi)
    __parser.set_defaults(func=cli)

    # shared arguments
    _shr = argparse.ArgumentParser(add_help=False)
    _subs = argparse.ArgumentParser(add_help=False)
    
    # input options
    in_group = _shr.add_argument_group('input options')
    in_group.add_argument('-d', dest='data', help=data_help)
    in_group.add_argument('-in', dest='instream', metavar='path', nargs='?', type=argparse.FileType('r'), default=sys.stdin, help=in_help)
    in_group.add_argument('-p', dest='params', metavar='params', nargs='*', default=[], help=ids_help)

    # output options
    out_group = _shr.add_argument_group('output options')
    out_group.add_argument('-m', '--minify', dest='pretty_print', action='store_false', help=pretty_help)
    out_group.add_argument('-o', dest='out', nargs='?', type=argparse.FileType('w'), default=sys.stdout, help=out_help)

    # credentials options
    cred_group = _shr.add_argument_group('credentials options')
    cred_group.add_argument('-c', '--creds', dest='prompt_for_creds', action='store_true', help=creds_help)
    cred_group.add_argument('-e', dest='env', metavar='SUFFIX', default='dev', help='specify .env suffix (ex: PROD)')

    # task only arguments
    tsk_group = _subs.add_argument_group('task options')
    tsk_group.add_argument('-l', '--list', dest='list', help=list_help, action='store_true')
    tsk_group.add_argument('-D', '--dry-run', dest='dry', action='store_true')

    # TODO: refactor - dynamically create
    subs = __parser.add_subparsers(title='Commands')
    _api = subs.add_parser('api',   aliases=['a'], help=api_help,   parents=[_shr])
    _env = subs.add_parser('env',   aliases=['e'], help=env_help,   parents=[])
    _fil = subs.add_parser('files', aliases=['f'], help=file_help, parents=[])
    _set = subs.add_parser('settings', aliases=['s'], help=settings_help, parents=[_shr, _subs])
    _tsk = subs.add_parser('task',  aliases=['t'], help=tasks_help, parents=[_shr, _subs])
    _thm = subs.add_parser('themes', aliases=['th'], help=themes_help, parents=[_shr, _subs])
    _wdg = subs.add_parser('widgets', aliases=['w'], help=widgets_help, parents=[_shr, _subs])

    # default functions
    _env.set_defaults(func=env)
    _api.set_defaults(func=api)
    _fil.set_defaults(func=files)
    _set.set_defaults(func=Settings.default)
    _tsk.set_defaults(func=Tasks.default)
    _wdg.set_defaults(func=Widgets.default)
    _thm.set_defaults(func=Themes.default)

    _api.add_argument('-l', '--list', dest='list', help=list_help, action='store_true')

    # api only arguments
    req_group = _api.add_argument_group('request')
    req_group.add_argument('resource', nargs='?', metavar='resource', choices=resources, help=resource_help)
    req_group.add_argument('method', metavar='method', nargs='?', choices=methods, default='get', help=method_help)
    req_group.add_argument('-i', dest='ids', metavar='id', nargs='*', default=[], help=ids_help)

    # subcommand only orguments
    _fil.add_argument('-o', action='store_true', help=fil_o_help)
    _tsk.add_argument('task', nargs='?',  choices=Tasks._all())
    _wdg.add_argument('task', nargs='?',  choices=Widgets._all())
    _set.add_argument('task', nargs='?',  choices=Settings._all())
    _thm.add_argument('task', nargs='?',  choices=Themes._all())
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
        for p in args.params:
            in_data[p.split('=')[0]] = tryParseInt(p.split('=')[1])
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
        handleBigCommerceClientRequestException(e)

def env(args, parser):
    make_tmp_dirs_if_not_exist()
    print(not os.path.exists(dot_env_path()))
    if not os.path.exists(dot_env_path()):
        with open(dot_env_path(), 'w') as f:
            f.write('BIGCLI_STORE_HASH_DEV="hash"\n')
            f.write('BIGCLI_AUTH_TOKEN_DEV="token"\n')
    open_env()

def files(args, parser): 
    if args.o and tmp_path_exists():
        open_files_using_default_editor()
    else:
        list_files()

# Tasks #######################################################################
class SubCommand():

    @classmethod
    def _all(cls):
        return {k:v for k,v in vars(cls).items() if not k.startswith('_')}

    @classmethod
    def default(cls, args, parser):
        if args.list:
            for k,v in cls._all().items():
                print("{} {} {}".format(color(k, 'blue'), " " * (30-len(k)), v.__doc__))
            return
        hash = get_store_hash(args)
        token = get_auth_token(args)
        client = BigcommerceApi(store_hash=hash, access_token=token, version='latest')
        out_data = cls._all()[args.task](args, client)
        if out_data:
            output(args, out_data, hash)

    @classmethod
    def pretty_print_key_values(cls, d):
        cls.print_rows(["{}{}{}".format(color(k, 'blue'), " " * (35-len(k)), v) for k, v in d.items() if not k.startswith('_')])

    @classmethod
    def print_rows(cls, rows):
        for r in rows:
            print(r)


class Settings(SubCommand):

    def all(args, api):
        """list all store settings"""
        settings = {}
        for r in Resources.classes:
            if r and "Settings" in r.__name__:
                if isUpdateable(r) and not (islistable(r) or isCreatable(r)):
                    print(r.__name__)
                    Settings.pretty_print_key_values(getattr(api, r.__name__).get().__json__())
                    settings.update(getattr(api, r.__name__).get().__json__())
                    print("")

    def logo(args, api):
        """List logo settings"""
        settings = api.SettingsLogo.get()
        Settings.pretty_print_key_values(settings)

    def profile(args, api):
        """List logo settings"""
        settings = api.SettingsStoreProfile.get()
        Settings.pretty_print_key_values(settings)

    def email_statuses(args, api):
        """List email status settings"""
        settings = api.SettingsEmailStatuses.get()
        Settings.pretty_print_key_values(settings)


class Themes(SubCommand):

    def list(args, api):
        """List themes"""
        themes = api.Themes.all()
        return {t['uuid']:t['name'] for t in themes}

    def cleanup(args, api):
        """delete all inactive themes"""
        if confirm(api, 'themes'):
            themes = api.Themes.all()
            for t in themes:
                if not t['is_active']:
                    print('[brocli]: deleting theme {} {}'.format(t.name, t.uuid))
                    try:
                        t.delete()
                    except bigcommerce.exception.ClientRequestException as e:
                        handleBigCommerceClientRequestException(e)

    def delete(args, api):
        if len(args.params) < 1:
            args.pretty_print = True
            output(args, Themes.list(args, api))
            uuid = input ('\n [bigcli] UUID: ')
            args.params.append(uuid)

        if confirm(api, uuid):
            api.Themes.get(args.params[0]).delete()


class Tasks(SubCommand):
    
    def list_cat_ids(args, api):
        """list all category IDs"""
        categories = api.Categories.iterall()
        category_ids = [c.id for c in categories]
        return category_ids

    def fix_product_cats(args, api):
        """Removes deleted category IDs in the categories array of all products."""
        all_cat_ids = Tasks.list_cat_ids(args, api)
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


class Widgets(SubCommand):
    
    def templates(args, api):
        """list widget templates by [uuid], name | Ex: bigcli t widget_templates"""
        templates = api.WidgetTemplates.iterall()
        return {t['uuid']:t['name'] for t in templates}

    def placements(args, api):
        """list widget placements by [uuid], name | Ex: bigcli t widget_templates"""
        placements = api.WidgetPlacements.iterall()
        Widgets.print_rows(['{} {} {} {} {}'.format(p['uuid'], p['widget']['name'], p['channel_id'], p['region'], p['status']) for p in placements])

    def regions(args, api):
        """list all widget regions (or specify filenames) Ex: bigcli widgets regions pages/home"""
        templates = [
            'pages/blog-post',
            'pages/blog',
            'pages/brand',
            'pages/brands',
            'pages/cart',
            'pages/category',
            'pages/checkout',
            'pages/compare',
            'pages/contact-us',
            'pages/home',
            'pages/order-confirmation',
            'pages/page',
            'pages/product',
            'pages/search',
            'pages/sitemap',
            'pages/subscribed',
            'pages/unsubscribe'
        ]
        if len(args.params) > 0:
            templates = args.params
        regions = {}
        for t in templates:
            regions[t] = [r.name for r in api.WidgetRegions.all(template_file=t) if 'name' in r]
        for k,v in regions.items():
            print(k)
            for i in v:
                print('  {}'.format(i))
            print('')


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
    if not validate_ids(cls, resource_str, ids):
        return
    if method == 'create':
        if method and len(ids) == 0:
            return getattr(resource, method)(**data)
        if method and len(ids) == 1:
            if type(data) == list:
                return getattr(resource, method)(ids[0], data)
            return getattr(resource, method)(ids[0], **data)
        if method and len(ids) == 2:
            return getattr(resource, method)(ids[0], ids[1], **data)
        if method and len(ids) == 3:
            return getattr(resource, method)(ids[0], ids[1], ids[2], **data)
    if method == 'update':
        if method and len(ids) == 0:
            print('update...')
            if isUpsertable(cls) and type(data) != list:
                data = [data]
            print(data)
            return resource.update(data)
        if method and len(ids) == 1:
            return getattr(resource, 'get')(ids[0]).update(**data)
        if method and len(ids) == 2:
            return getattr(resource, 'get')(ids[0], ids[1]).update(**data)
        if method and len(ids) == 3:
            return getattr(resource, 'get')(ids[0], ids[1], ids[2]).update(**data)
    if method == 'all' or method == 'iterall' or method == 'get':
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
            return
        if method and len(ids) == 0:
            return resource.delete_all()
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

def handleBigCommerceClientRequestException(e):
    print('bigcommerce.exception.ClientRequestException:\n')
    print(e)
    if 'response' in vars(e) and 'url' in vars(e.response):
        print('\nFull URL: ' + e.response.url + '\n')  

def dot_env_path():
    return "{}{}{}".format(tmp_path(), "/", '.env')

def tmp_path(hash=None):
    if hash:
        return tmp_path() + '/' + hash
    return str(Path.home()) + '/.bigcli'

def make_tmp_dirs_if_not_exist(hash=None):
    if not tmp_path_exists(hash):
        os.mkdir(tmp_path(hash))

def tmp_path_exists(hash=None):
    if hash:
        return os.path.exists(tmp_path() + '/' + hash)
    return os.path.exists(tmp_path())

def list_files():
    for file in os.listdir(tmp_path()):
        print("{}/{}".format(tmp_path(), file))
        
def open_env():
    open_files_using_default_editor('.env')

def open_files_using_default_editor(files='*'):
    editor = os.getenv('EDITOR')
    path = "{}{}{}".format(tmp_path(), "/", files)
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

def isUpsertable(cls):
    if issubclass(cls, CollectionUpdateableApiResource):
        return True

def isCreatable(cls):
    if issubclass(cls, CreateableApiResource):
        return True

def isUpdateable(cls):
    if issubclass(cls, UpdateableApiResource):
        return True

def islistable(cls):
    if issubclass(cls, ListableApiResource):
        return True
    if issubclass(cls, ListableApiSubResource):
        return True
    if issubclass(cls, ListableApiSubSubResource):
        return True

def tryParseInt(s, base=10, val=None):
    try:
        return int(s, base)
    except ValueError:
        return s 

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
        domain = api.Store.get().domain
        domainColor = color(domain, 'blue')
        action = color('DELETE', 'red')
        if len(ids) > 0:
            id = color(ids[-1], 'red')
            print("\n[bigcli]: {} {} {} on {}?".format(action, resource_str, id, domainColor))
            check = 'delete it now'
            confirmed = input("[bigcli]: type '{}' to confirm: ".format(check)) == check
            if not confirmed:
                print('\n[bigcli]: Delete aborted.')
            return confirmed
        else:
            print("\n[bigcli]: {} {} {} on {}?".format(action, 'ALL', resource_str, domainColor))
            check = "delete all {} on {}".format(resource_str, domain)
            check = "{}".format(check)
            confirmed = input("[bigcli]: type '{}' to confirm: ".format(check)) == check
            if not confirmed:
                print('[bigcli]: Delete aborted.\n')
            return confirmed

def iterall(g):
    l = []
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
    elif args.env:
        s = args.env.upper()
        store_hash = get_cwd_dot_env_value_for('BIGCLI_STORE_HASH_{}'.format(s))
        if not store_hash:
            store_hash = get_tmp_dir_env_value_for('BIGCLI_STORE_HASH_{}'.format(s))
        if not store_hash:
            store_hash = os.environ.get("BIGCLI_STORE_HASH_{}".format(s))
        if not store_hash or len(store_hash) < 4:
            store_hash = getpass.getpass(prompt='[bigcli] Enter Store Hash:')
    else:
        store_hash = get_cwd_dot_env_value_for('BIGCLI_STORE_HASH_{}'.format(s))
        if not store_hash:
            store_hash = get_tmp_dir_env_value_for('BIGCLI_STORE_HASH_{}'.format(s))
        if not store_hash:
            store_hash = os.environ.get("BIGCLI_STORE_HASH_{}".format(s))
    return store_hash

def get_auth_token(args, prompt=True):
    if args.prompt_for_creds:
        access_token = input('X-Auth-Token:')
    elif args.env:
        s = args.env.upper()
        access_token = get_cwd_dot_env_value_for('BIGCLI_AUTH_TOKEN_{}'.format(s))
        if not access_token:
            access_token = get_tmp_dir_env_value_for('BIGCLI_AUTH_TOKEN_{}'.format(s))
        if not access_token:
            access_token = os.environ.get("BIGCLI_AUTH_TOKEN_{}".format(s))
    else:
        access_token = get_cwd_dot_env_value_for('BIGCLI_AUTH_TOKEN_{}'.format(s))
        if not access_token:
            access_token = get_tmp_dir_env_value_for('BIGCLI_AUTH_TOKEN_{}'.format(s))
        if not access_token:
            access_token = os.environ.get("BIGCLI_AUTH_TOKEN_{}".format(s))
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
    """For printing request and rate limit info when iterating over API resources"""
    if resource.resource_version == 'v3':
        try:
            meta = resource._connection._last_response.json()['meta']
            total = meta['pagination']['total']
            if total > 0 and total / 250 > 0:
                return
            rl = resource._connection.rate_limit
            flush_print_rows([
                row,
                f"Requests remaining: {rl['requests_remaining']} / {rl['requests_quota']}",
                f"Ms until reset:     {rl['ms_until_reset']}",
                f"{resource_str} scanned:   {i} / {meta['pagination']['total']}"
            ])
        except KeyError:
            return
        except TypeError:
            return

def flush_print_rows(rows):
    cursor_up = '\x1b[1A'
    for r in rows:
        print(r, sep='', end='\n', flush=True)
    print(cursor_up*(len(rows)+1))

class Resources():

    def map_resources(all, type=ApiResource):
        l = [k for k,v in all.items() if isclass(v) and issubclass(v, type)]
        return [i for i in l if not i.startswith("_") and 'Resource' not in i and 'Mapping' not in i]

    def map_classes(all, type=ApiResource):
        l = [v for k,v in all.items() if isclass(v) and issubclass(v, type)]
        return [i for i in l if not i.__name__.startswith("_") and 'Resource' not in i.__name__ and 'Mapping' not in i.__name__]

    all = vars(bigcommerce.bigcommerce.resources.v2)
    all.update(vars(bigcommerce.bigcommerce.resources.v3))
    all_dict = all
    classes = map_classes(all, ApiResource)
    all = map_resources(all, ApiResource)
    all.sort()

if __name__ == '__main__':
    main()
    