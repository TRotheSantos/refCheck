# “Automated checking of scientific references using Large Language Models”
![grafik](https://github.com/TRotheSantos/refCheck/assets/124930266/ffea4dc7-f66b-44f3-8c1f-d16485f5bdf8)

![grafik](https://github.com/TRotheSantos/refCheck/assets/124930266/cbb4cfb6-c33a-405f-8075-c495fb8181f9)


You can get started for development either by using the Docker configuration or running a local server using Python virtual environments. We assume Linux or macOS for the commands. If you use Windows, do yourself a favor and use the official Windows subsystem for linux to get a proper commandline, it will save you from headache. Anyways running the local server should work on Windows or through an IDE terminal too.

> **WARNING:**<br>
> The recursively used pytorch library does not support Python 2.x.<br>
> On Windows only **python v3.8-3.11** is supported ([PyTorch](https://pytorch.org/get-started/locally/#windows-python)).<br>
> On Linux 3.8.1+ or later is required (not completely sure about the cap, [GitHub](https://github.com/pytorch/pytorch#from-source)) 

# Docker

The Docker Configuration is made for development, therefore it  allows you to make changes in the code which are directly reflected (Django usually takes a few seconds to adapt) in the software running in the container. 
The prerequisits for using this Docker Configuration: install Docker for your Operating system. 
To get you started head over to your commandline and do:

```
mkdir ThisIsWhereWeCloneTo && cd ThisIsWhereWeCloneTo
git clone < repo Link >

cd into the cloned directory
docker-compose --build
docker-compose up -d
```
the output will end with something like:
                                                                                                            
    Container <Container_Name>  Started 

For the future, this is where it ends, everything is up and running. However
if you are starting the container for the first time, you won't see anything when you head over to to http://127.0.0.1:8000

This is because Django is not yet set up. To achieve this you need to execute a few commands within the Container. To connect to the Docker container take your terminal and 

    docker exec -it <Container_Name> bash

Now in the Container execute the following commands:

    python manage.py makemigrations
    python manage.py migrate
    python manage.py runserver 0.0.0.0:8000
    exit

now shut down the container:

    docker-compose down -v 

and fire it up again using

    docker-compose up -d

Now head over to http://127.0.0.1:8000 to check for the result, you should be good to go.
To be able to access the admin pages under http://127.0.0.1:8000/admin/ too, you should create a superuser.
You will need to configure an `OPENAI_API_KEY`. Also you will need to configure the API Keys for the APIs used to query for the bibliography entries. All this is done in the `.env.dev` file. Also if you want to use localAI instead of openAI, you can configure the `LOCALAI_API_BASE` and the `DEFAULT_MODEL`. Also if you uncomment `OPENAI_EMBEDDING_MODEL` (optionally you can also adjust that) you will automatically switch to using the embeddings that are configured in this environment varibale.


# Local Django server
## Using Python virtual environments
The prerequisits for getting started with python venvs are:
install python3.11 for your operating system. Keep in mid that sometimes the use of `python3` instead of `python` is required.
on your commandline do:

    mkdir ThisIsWhereWeCloneTo && cd ThisIsWhereWeCloneTo
    git clone < repo Link >
    (cd the/cloned/directory)
    python -m venv env  # creates virtual environment
    env/bin/activate  # activates venv
    pip install -r requirement.txt

#### A heads up in case you want to use the python virtual environments:
Some linux distributions and macOS versions default to a version of SQLite that predates the one required for the project. In case you get any errors like this: `Error: Your system has an unsupported version of sqlite3. Chroma requires sqlite3 >= 3.35.0` , use the Docker Configuration for development. The Distribution used as a base image comes with a version of SQLite that does cause such errors.

## Handling Django server

Now after setting up the project directory and installing the requirements, the Django project can be started and interacted with. For a complete overview see [django-admin](https://docs.djangoproject.com/en/5.0/ref/django-admin/) commandline interface.
Basically you start the manage.py with commands and options. There are different ways according to the docs but we recommend:

    python manage.py <command> [options]

Make sure the virtual environment is activated and you're in the correct directory `cd Where\We\Cloned\To`. Then the underlying database is configured by

    (.env) ~path/to/RefCheck> python manage.py makemigrations
    (.env) ~path/to/RefCheck> python manage.py migrate
This is always required if changes were made to the django models to keep conistancy with the database configuration.<br>
To actually start the server simply run

    (.env) ~path/to/RefCheck> python manage.py runserver <optionally specify port, eg. 9090>
Now head over to http://127.0.0.1:8000 to check for the result, you should be good to go.

To be able to access the admin pages under http://127.0.0.1:8000/admin/ too, you should create a superuser.
You will need to configure an `OPENAI_API_KEY`. Also you will need to configure the API Keys for the APIs used to query for the bibliography entries. All this is done in the `.env.dev` file. Also if you want to use localAI instead of openAI, you can configure the `LOCALAI_API_BASE` and the `DEFAULT_MODEL`. Also if you uncomment `OPENAI_EMBEDDING_MODEL` (optionally you can also adjust that) you will automatically switch to using the embeddings that are configured in this environment varibale.


# License
 Copyright 2024 Linus Ostermayer, Tom Fix, Maxime Maurer, Marie Oberst, David Paul Mark, Tillmann Rothe Santos, Joris Briegel
 
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
limitations under the License.
