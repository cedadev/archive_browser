# Archive Browser

This is an simple django application which uses javascript AJAX requests to pull content from elaticsearch and display it on the page. The navigation is handled by this application but any download links won't work without pydap being configured alongside.

## Setting up the development environment locally

Clone the repository

`git clone https://github.com/cedadev/archive_browser.git`

Set up a python3 virtual environment

`python3 -m venv venv`

Activate the virutualenv

`. venv/bin/activate`

Install requirements
`pip install -r archive_browser/requirements.txt`

### Running the development server

Make sure you have your python 3 environment active then run:
`python manage.py runserver`

The site can then be accessed on [http://localhost:8000](http://localhost:8000)


## Setting up the development environment using vagrant

Create a directory to put project into

Enter directory and clone repository

`git clone https://github.com/cedadev/archive_browser.git`

Copy vagrant file to outer directory

`cp archive_browser/Vagrantfile .`

Initialise machine

`vagrant up`

### Running the development server

Activate environment and runserver

`vagrant ssh`

`cd vagrant_data`

`. archive_venv/bin/activate`

`python manage.py runserver 0.0.0.0:8000`

The site can then be accessed on [http://localhost:8080](http://localhost:8080)

