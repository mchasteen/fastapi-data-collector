#!/bin/bash

VERSION=$1
DOCKERREPO='harbor.home.local'
PROJECT='fastapi'
docker login $DOCKERREPO
docker build -t $DOCKERREPO/$PROJECT/fastapi-data-collector:$VERSION -t fastapi-data-collector:$VERSION -t fastapi-data-collector:latest .
docker push $DOCKERREPO/$PROJECT/fastapi-data-collector:$VERSION
docker tag $DOCKERREPO/$PROJECT/fastapi-data-collector:$VERSION $DOCKERREPO/$PROJECT/fastapi-data-collector:latest
docker push $DOCKERREPO/$PROJECT/fastapi-data-collector:latest
