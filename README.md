# OSCARD
Create, Resize and Delete instance operations generator for OpenStack's Nova APIs

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