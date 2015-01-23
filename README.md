# OSCARD
Create, Resize and Delete instance operations generator for OpenStack's Nova APIs

### Install (not Dockerized)

```
	$ git clone https://github.com/affear/oscard.git
	$ cd oscard
	$ mkdir logs
	$ sudo apt-get install -y python-virtualenv python-dev libffi-dev libssl-dev
	$ virtualenv venv
	$ source oscardrc
	$ pip install -r requirements.txt
```

### Build

```
	$ docker build -t affear/oscard:ok .
```

### Run

```
	$ docker run -ti -p 80:3000 affear/oscard:ok
```

While developing:

```
	$ docker run -v $(pwd):/oscard --name oscard -p 3000:3000 --rm affear/oscard:ok
```

### WARNING
Before running the simulation, remeber to update quotas for the tenant in use.  
If not you will cause exceptions while spawning lots of intances!  
So, from the controller:

```
	$ export BIGNUM=100000000
	$ nova quota-class-update --instances $BIGNUM default
	$ nova quota-class-update --cores $BIGNUM default
	$ nova quota-class-update --ram $BIGNUM default
```