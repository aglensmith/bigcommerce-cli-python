# Bigcli (Alpha)

Interact with [BigCommerce](https://www.bigcommerce.com/) stores via command line.

## Table of contents

* Quick start
  * [Install](#install)
  * [Usage](#usage)
  * [Why this is cool](#why-this-is-cool)
* Commands
  * local env 
    * [env](#env)
    * [files](#files)
  * store resources
    * [api](#api)
    * [settings](#settings)
    * [task](#task)
    * [themes](#themes)
    * [widgets](#widgets)
* Options
  * [data](#data)
  * [input](#input)
  * [output](#output)
* Contributing
  * [Adding tasks](#adding-tasks)
  * [Adding api resource](#adding-api-resource)

## Install
Install `bigcli` into isolated python environment using [`pipx`](https://pypa.github.io/pipx/).

```bash
brew install pipx
pipx ensurepath
pipx install git+https://github.com/aglensmith/bigcommerce-cli-python@main
```

Run `bigcli env` to create and open the `~/.bigcli/.env` file.

```bash
$ bigcli env
```

Replace `hash` and `token` in `~/.bigcli.env` with your credentials.

```bash
BIGCLI_STORE_HASH_DEV="hash"  
BIGCLI_AUTH_TOKEN_DEV="token"
```

Save, and run your first command.

```bash
$ bigcli api Products
```

## Usage

```
usage: bigcli [-h]
              {api,a,env,e,files,f,settings,s,task,t,themes,th,widgets,w} ...

Interact with BigCommerce stores via command line

optional arguments:
  -h, --help            show this help message and exit

Commands:
  {api,a,env,e,files,f,settings,s,task,t,themes,th,widgets,w}
    api (a)             make API requests for any resource
    env (e)             create or open ~/.bigcli/.env file
    files (f)           list all ~/.bigcli/ files
    settings (s)        interact with store settings
    task (t)            run miscellaneous tasks
    themes (th)         interact with store themes
    widgets (w)         interact with store widgets
```

#### Get products and save output to a csv

```bash
$ bigcli a Products -p include_fields=sku,name,price limit=10 -o csv
```

#### Delete all inactive themes

```bash
$ bigcli themes cleanup # prompts for confirmation
```



## Why this is cool

```
$ biglci a Products -o
$ bigcli files -o
```

## Configuring credentials

You can specify an arbitrary number of API keys in `~/.bigcli/.env` or a `.env` in your current working directory.

```bash
# used by default
BIGCLI_STORE_HASH_DEV="hash"  
BIGCLI_AUTH_TOKEN_DEV="token"

# used when -e foo specified
BIGCLI_STORE_HASH_FOO="hash"
BIGCLI_AUTH_TOKEN_FOO="token"

# used when -e bar specified
BIGCLI_STORE_HASH_BAR="hash"
BIGCLI_AUTH_TOKEN_BAR="token"
# ...
```

You can specify which credentials to use by passing in the suffix on the command line.

```bash
$ bigcli api Products -e FOO
```

## `api`

```
usage: bigcli api [resource] [method]

optional arguments:
  -h, --help            show this help message and exit
  -l, --list            list available api resources

input options:
  -d DATA               include json data for request body
  -in [path]            specify file path to request body json
  -p [params[params..]] specify params

output options:
  -m, --minify          minify json output
  -o [OUT]              specify outfile
  -a attribute          specify a single resource attribute to

credentials options:
  -c, --creds           get prompted for api credentials
  -e SUFFIX             specify .env suffix (ex: PROD)

request:
  resource              An API resource (run bigcli a -l to see all)
  method                get, all, update, or delete
  -i [id [id ...]]      specify resource IDs for path
  ```

```bash
# list available api resources
$ bigcli a -l

# get first page of products
$ bigcli a Products -p page=1

# get products on all pages
$ bigcli a Products iterall
```

## `settings`

```bash
$ bigcli settings -l
```

```bash
all                     list all store settings
logo                    List logo settings
profile                 List logo settings
email_statuses          List email status settings
# ...
```

## `themes`

Run `bigcli themes -l` to see a list of theme tasks.

```bash
$ bigcli themes -l
```

```bash
list                    List themes
cleanup                 delete all inactive themes
delete                  delete a single theme
# ...
```

## `widgets`

Run `bigcli widgets -l` to get a list of widget tasks.

```bash
$ bigcli widgets -l
```

```bash
templates               list widget templates by [uuid], name | Ex: bigcli t widget_templates
placements              list widget placements by [uuid], name | Ex: bigcli t widget_templates
regions                 list all widget regions (or specify filenames) Ex: bigcli widgets regions pages/home
```

## `env`

Use the `env` command to open the `~/.bigcli/.env` file. If one doesn't exist, `bigcli` will create it for you.

```bash
$ bigcli env
```

## `files`

```bash
usage: bigcli files [-h] [-o] [-e]

List all ~/.bigcli files

optional arguments:
  -h, --help  show this help message and exit
  -o          open all .bigcli files
```

Use `files` with no options to list all files in `~/.bigcli`.

```bash
$ bigcli files
```

```bash
~/.bigcli/_last.json                   # latest output will always be here
~/.bigcli/.env
~/.bigcli/h10wocxy6s-Products-get.json # get products for store h10wocxy6s
```

## `data`

Use `-d` to pass in request body json on the command line.

```bash
# update a page 
$ bigcli api Pages -i 8 -d '{"name": "Pages V3 Test", "type": "page"}'
```

## `input`

use `-in` to specify an infile for the request body. 

```bash
# update a page from a json file
$ bigcli api Pages update -i 8 -in data.json
```

## `output`

Use the `-o` option to save output to `~/.bigcli/`.

```bash
$ bigcli api Products -o
```

Use `bigcli files` to list the files in `~/.bigcli`.

```
$ bigcli files
```

```bash
~/.bigcli/_last.json                   # latest output will always be here
~/.bigcli/.env
~/.bigcli/h10wocxy6s-Products-get.json # get products for store h10wocxy6s
```

You can also specify a specific file path.

```bash
$ bigcli a Store -o ~/Desktop/store.json
```

And even save json responses as a csv.


```bash
$ bigcli a Products -p include_fields=sku,name,price limit=10 -o csv
```

## `task`

```
usage: bigcli task [task]

task options:
  -h, --help            show this help message and exit
  -l, --list            list available tasks
  -D, --dry-run         test a task without making changes

input options:
  -d DATA               include json data for request body
  -in [path]            specify file path to request body json
  -p [params[params..]] specify params

output options:
  -m, --minify          minify json output
  -o [OUT]              specify outfile

credentials options:
  -c, --creds           get prompted for api credentials
  -e SUFFIX             specify .env suffix (ex: PROD)
```

## Contributing

```bash
# clone repo
git clone git@github.com:aglensmith/bigcommerce-cli-python.git

# install with pip in editable mode
pip install -e ./bigcommerce-cli-python/bigcli

# code changes will be reflected when running bigcli in terminal
```

### Adding tasks

Add tasks by adding a function to the `Tasks` class in [bigcli/cli.py](https://github.com/aglensmith/bigcommerce-cli-python/blob/main/bigcli/cli.py).

```python
class Tasks():

    # ...

    def widget_templates(args, api):
        """
        list widget templates by [uuid], name
        Ex: bigcli t widget_templates
        """
        templates = api.WidgetTemplates.iterall()
        return {t['uuid']:t['name'] for t in templates}
```

The function name becomes a CLI argument automatically (ex: `bigcli t widget_templates`).  `bigcli t -l` prints the docstring.

```bash
widget_templates

        list widget templates by [uuid], name
        Ex: bigcli t widget_templates
```

### Adding API resources

`bigcli` uses [a fork of `bigcommerce-api-python`](https://github.com/aglensmith/bigcommerce-api-python/tree/bigcli) to generate the arguments for the `bigcli a` command and to interact with the BigComerce API. Add or edit resources in `bigcommerce/resources/v3` and make a pull request to the `bigcli` branch of [the fork](https://github.com/aglensmith/bigcommerce-api-python/tree/bigcli).
