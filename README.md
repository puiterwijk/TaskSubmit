# What is this

This is a very simple Flask tool to allow people to submit tasks to your Inthe.AM task list.
I hacked this together for myself in a few minutes, and it uses OpenID authentication against the Fedora account system to prevent spam.


# Development setup

1. Create a my_key file containing "export API_KEY="inthe.AM API key"
2. Run python setup.py develop
3. Run ./start.sh


# Setting up

1. Create an OpenShift app (or other mod_wsgi host)
2. Set environment variable API_KEY="inthe.AM API key", for openshift: "rhc set-env -a tasksubmit API_KEY='username:key'
3. Enjoy
