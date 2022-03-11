# BigCommerce CLI Python

A BigCommerce CLI tool written in python. 

Install using [pipx](https://pypa.github.io/pipx/).

```bash
# install pipx if you don't have it.
brew install pipx
pipx ensurepath

# install the cli
pipx install git+https://github.com/aglensmith/bigcommerce-cli-python@main
```

## Usage

```bash
usage: bigcli api [-h] [-i [IDS [IDS ...]]] [-c] [-cne] [-pp] [--PROD]
                  [-o [OUT]]
                  ResourceName

positional arguments:
  ResourceName        An API resource (bigcli -l to see all)

optional arguments:
  -h, --help          show this help message and exit
  -i [IDS [IDS ...]]  specify resource IDs for path
  -c                  prompt for api credentials
  -cne                prompt for api credentials no tty echo
  -pp                 pretty print output
  --PROD              use prod credentials
  -o [OUT]            outfile path
```

## Contributing

## Directory structure

```
.
├── bin               
├── docs                 
├── lib
    └── bigcommerce-api-python      
├── 
├──             
├── 
└──         
```

## TODO

* Make bigcommerce-api-python a submodule
    * https://pypa.github.io/pipx/
    * https://matiascodesal.com/blog/how-use-git-repository-pip-dependency/
    * https://softwareengineering.stackexchange.com/questions/365579/how-do-i-deal-with-projects-within-projects-in-python
    * https://stackoverflow.com/questions/37132317/workflow-to-work-on-a-github-fork-of-a-python-library
    * prevents pip installing cli breaking bigcommerce-api-python previously installled
    * How to make sure submodules are installed and accessible to cli? 
* PUT requests
* POST requests
* DELETE requests
* README & Usage examples
* make channel aware

```
# Use a branch called "GreetingArg"
pip install git+https://github.com/matiascodesal/git-for-pip-example.git@GreetingArg#egg=git-for-pip-example

# What that should look like in your requirements.txt
packageA==1.2.3
-e https://github.com/matiascodesal/git-for-pip-example.git@v1.0.0#egg=my-git-package
packageB==4.5.6
```

> When you pip install with editable mode, pip only sets up a link from your environment to wherever the source code is. So, you can clone your GitHub fork into a convenient directory like ~/projects/libraryX, then do pip install -e ~/projects/libraryX, and keep editing the code at ~/projects/libraryX while your changes are immediately reflected in the environment where you installed it.