#!/bin/bash

gunicorn --bind=0.0.0.0:6380 --worker-class=gevent --workers=2 main:app
