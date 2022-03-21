# BigCommerce CLI Python

A BigCommerce CLI tool written in python. 

## Installation

Install into isolated python environment using [`pipx`](https://pypa.github.io/pipx/) (recommended).

```bash
# install pipx if you don't have it.
brew install pipx
pipx ensurepath
pipx install git+https://github.com/aglensmith/bigcommerce-cli-python@main
```

Or, install with `pip`.

```bash
pip install git+https://github.com/aglensmith/bigcommerce-cli-python@main
```

## Usage

`bigcli` will attempt to load API credentials from the `.env` file in the current working directory

```bash
# used by default
BIGCLI_STORE_HASH_DEV="dev_hash"
BIGCLI_AUTH_TOKEN_DEV="dev_token"

# used when -PROD flag used
BIGCLI_STORE_HASH_PROD="prod_hash"
BIGCLI_AUTH_TOKEN_PROD="prod_token"
```

If they're not found, it'll try to load them from `~/.bigcli/.env`. If they're still found, it'll attempt to load them from your system's environment. If they're still not found, you'll be prompted to enter credentials. 

### Examples

```bash
# list available api resources
bigcli a -l

# get first page of products
bigcli a Products

# get products on all pages
bigcli a Products all

# update a page 
bigcli a Pages -i 8 -d '{"name": "Pages V3 Test", "type": "page"}'

# update a page from a json file
bigcli a Pages update -i 8 -in data.json

# output to ~/.bigcli/ as json
bigcli a Products -o

# output as csv
bigcli a Products -o csv

# list files in ~/.bigcli/
bigcli f

# open all files in ~/.bigcli/
bigcli f -o

# save to a specific directory
bigcli a Store -o /var/tmp/bigcli.json

# list available tasks
bigcli t -l

# use task to get list of widget templates
bigcli t widget_templates

# output
{
    "2ff24732-6848-47ba-9a7f-c8b1d444f270": "PayPal Credit Banner - Cart Page (728x90)",
    "3002bf5b-5eca-4ac2-8f1f-5240c2b74712": "PayPal Credit Banner - Home Page (728x90)",
    "7c541473-855d-4b62-a7bf-6ef3199f914c": "PayPal Credit Banner - Product Details Page (234x60)",
}

# get a widget template template's schema
bigcli t widget_template_schema 2ff24732-6848-47ba-9a7f-c8b1d444f270

# get a widget template's schema, get prompted for uuid first
bigcli t widget_template_schema

# use map task to print list of page ids mapped to name
bigcli t map Products id name

# get a list of non-existent categories
bigcli t non_existent_categories 
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
