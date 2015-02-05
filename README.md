# OSCARD
Create, Resize and Delete instance operations generator for OpenStack's Nova APIs.

This repo contains a Dockerized service that runs simulations against a Dockerized OpenStack controller (see [affear/fakestack](https://github.com/affear/fakestack)).

A simulation is composed of `t` steps.  
At each step a command is randomly chosen (among _create_, _resize_ and _destroy_).  
_Every execution is a blocking call_, so, the next execution won't start until the previous is completed.  
The simulation, in this way, is totally _serial_.  
Every command is executed by _the same OpenStack user and tenant_ (set in `oscard.conf`).  
At each step, the chosen command is executed on each of the hosts set in `oscard.conf` (for a complete reference of settings, see `oscard.sample.conf`).

Oscard stores a snapshot of the system (and other useful information) at each step on a [Firebase](https://www.firebase.com/) backend.  
If you want to store your simulation results, create an application on Firebase (set its url in `fb_backend` in configuration file) with no authentication policy (not implemented yet).

When run, Oscard, exposes an api which allows to:

* create an instance (`/create POST`);
* resize an instance(`/resize POST`);
* delete an instance (`/destroy POST`);
* get the current snapshot of the system (`/snapshot GET`);
* get the ID of the current simulation (useful if you want to init a random number generator) (`/seed GET`);
* get the current architecture of the system (`/architecture GET`);

Every endpoint doesn't accept any argument.  
So every resize and delete will _randomly_ apply to one of the instances active on compute nodes.

#### WARNING
If you run a 3000-step simulation your user/tenant will probably create around 1800 instances. For this reason, it is important to enlarge quotas for that tenant.
From the (maybe dockerized) controller:

```
	$ export BIGNUM=100000000
	$ nova quota-class-update --instances $BIGNUM default
	$ nova quota-class-update --cores $BIGNUM default
	$ nova quota-class-update --ram $BIGNUM default
```

### Install (not Dockerized)
If you want to install Oscard on your system without starting a Docker container, you can follow these commands:

```
	$ git clone https://github.com/affear/oscard.git
	$ cd oscard
	$ mkdir logs
	$ sudo apt-get install -y python-virtualenv python-dev libffi-dev libssl-dev
	$ virtualenv venv
	$ source oscardrc
	$ pip install -r requirements.txt
```

If you do this for developing reason remeber that you can set `fake=True` in configuration file. In this way, no OpenStack controller will be involved.

### Docker Build

```
	$ docker build -t affear/oscard:alpha .
```

### Docker Run

```
	$ docker run -ti -p 3000:3000 --rm --name oscard affear/oscard:alpha
```

If you are developing and you want to avoid continuously rebuilding Oscard:

```
	$ docker run -v $(pwd):/oscard --name oscard -p 3000:3000 --rm affear/oscard:alpha
```

### Improving execution speed
If you run a long simulation on real OpenStack nodes, it will take some seconds for each command to be executed and some additional seconds to store results on the Firebase backend.  

To increase speed of execution, you can make db calls concurrent using Celery.

On the machine on which you execute `./bin/run_sim`, in another shell, run these commands:

```
	$ sudo service rabbitmq-server start
	$ source oscardrc
	$ start_celery_worker
```