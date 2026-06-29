# A simple dashboard for e-mission

Issues: Since this repository is part of a larger project, all issues are tracked in the central docs repository. If you have a question, as suggested by the open source guide, please file an issue instead of sending an email. Since issues are public, other contributors can try to answer the question and benefit from the answer.

## Development

We use docker images for the software dependencies since we will not be modifying them here.

So the steps are:

#### Launch dev environment

```
$ docker-compose -f docker-compose.dev.yml  up
Creating network "em-public-dashboard_emission" with the default driver
Creating em-public-dashboard_db_1 ... done
Creating em-public-dashboard_plot-gen_1  ... done
Creating em-public-dashboard_dashboard_1 ... done
...
dashboard_1  | Starting up http-server, serving ./
dashboard_1  | Available on:
dashboard_1  |   http://127.0.0.1:8080
dashboard_1  |   http://172.25.0.3:8080
dashboard_1  | Hit CTRL-C to stop the server
...
notebook-server_1  |
notebook-server_1  |     To access the notebook, open this file in a browser:
notebook-server_1  |         file:///root/.local/share/jupyter/runtime/nbserver-22-open.html
notebook-server_1  |     Or copy and paste one of these URLs:
notebook-server_1  |         http://f8317197efaf:8888/?token=5cfd541b7461a47310c9c8aaa4114f921457a6f17b8ca159
notebook-server_1  |      or http://127.0.0.1:8888/?token=5cfd541b7461a47310c9c8aaa4114f921457a6f17b8ca159
...
```

#### Test the frontend install

Go to http://localhost:3274/ to see the front-end. Note that the port is *3274*
instead of the *8080* in the logs, since we remap it as part of the docker-compose.

#### Test the notebook install

Use the notebook URL from the console but change `8888` to `47962`

```
http://127.0.0.1:8888/?token=<token>
```

becomes

```
http://127.0.0.1:47962/?token=<token>
```

#### Load some data

https://github.com/e-mission/e-mission-server/#quick-start

There are multiple sources listed there, or you can use the mongodump from:
https://github.com/asiripanich/emdash#loading-test-data

#### Loading data from a mongodump

We have a helper script to load data directly from a mongodump.

```
$ bash viz_scripts/docker/load_mongodump.sh <mongodump_file>
```

Note that this expects a standard setup with:
- this repository checked out under the `em-public-dashboard` directory, which makes the database name `em-public-dashboard_db_1`
- the incoming mongodump is in tar gz format. This should be true of all canbikeco dumps, you may need to change the `tar xvf` to `unzip` otherwise.  The mongo container typically doesn't have zip installed, so using tar is more portable.

## Working with `docker compose` and `.gitignore`

### Using `docker compose`

When working with `docker compose`, it's generally recommended to avoid committing changes to the `docker-compose.dev.yml` file, especially if you're running the `./load_mongodump <dump tar>` script. This file is typically configured to work in a specific way for your development environment, and changes might not be applicable or useful for others working on the same project.

### `.gitignore` Configuration

To streamline your workflow, we have added the `docker-compose.dev.yml` file to the `.gitignore` file. This means that by default, changes to `docker-compose.dev.yml` will not be tracked by Git. This setup helps to avoid unnecessary commits and ensures that your `docker-compose.dev.yml` remains consistent with the intended configuration for the project.

### Committing Changes to `docker-compose.dev.yml`

If you do need to make changes to `docker-compose.dev.yml` and want to commit those changes, you can override the ignore settings by using the following Git command:

```bash
git add -f docker-compose.dev.yml
```

**If you have a non-standard setup, please use your expertise to change the script appropriately.**

#### Happy visualizations!

Look at the existing notebooks for examples on how to start.
In particular, before you check in, please make sure that you are reading
inputs correctly, because otherwise, no metrics will be generated.

### Design decisions

Dashboards! They are fairly essential for user acceptance, but there are many options to build them.
And the choice of the technology stack for them is particularly fraught.
And for community projects, especially outside computer stack, choosing a technology stack ensures that half your collaborators cannot access it.
For example, choosing python will cause R users to balk and vice versa.
And there is although contributors can write some javascript, picking a charting library again steepens the learning curve.

So we are going to use a simple and stupid dashboard.
This will consist of a reactive grid layout
(e.g. https://strml.github.io/react-grid-layout/examples/15-drag-from-outside.html)
served by a simple static express server following the instructions at
https://www.thoughts-in-motion.com/articles/creating-a-static-web-server-with-node-js-and-express/

The grid layout will display static, pre-generated images using whatever program the user wishes.
The program should take the time range as input and generate a static image shared with the express server.
We have included python examples using ipython notebook and simple python scripts for the following metrics:

- mode share (notebook)
- purpose share (notebook)
- total number of trips per day (python)

In order to get the prototype out, there are a lot of shortcuts. We can revisit
this later if there is sufficient interest/funding.

- Using gridster (https://github.com/dsmorse/gridster.js/) and bootstrap instead of react
- Use a pre-built node image with an install of http-server instead of express
- Using a mounted volume instead of building a custom docker image to make deployment easier
- Using the e-mission server codebase to generate graphs instead of a REST API

The one part where we are NOT cutting corners is in the parts where we expect
contributions from others. We are going to build in automated tests for that
part to ensure non-bitrotted code.

## Trobleshooting Tips

Please be sure you are running analysis notebooks through the notebook server, not another avenue such as VScode, this is to prevent dependency issues. 

You may need to increase the resources avaliable to Docker if:
- the dataset is large
- you believe you've loaded the data but there is none when running the notebooks
- the notebook can't connect to the database
- when you try and start the container for the database it exits with code 14

## Large Dataset Workaround

This is not the standard method of loading data, and we are not reccomending this method or promising that it will work, but the following has worked for us in order to cut down on resources required in order to work with a large dataset in a pinch.

1. unpack the zipped files in your local file system
2. copy the `stage_analysis`, `stage_profiles`, and `stage_uuids` files into the mongo docker container
3. place the files in a `tmp/dump/Stage_database` folder
4. from the command line in `tmp`, run a `mongorestore`

This process restores the most basic files, reducing size, but also the analysis that will be possible. Using the script to restore all of the data is the reccomended method. These steps may be helpful if the dataset is larger than your machine can handle. 
