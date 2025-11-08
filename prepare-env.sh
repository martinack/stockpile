#!/bin/bash

docker compose build

docker save -o stockpile-frontend.tar stockpile-frontend:latest
docker save -o stockpile-backend.tar stockpile-backend:latest

scp stockpile-frontend.tar pi@192.168.182.23:/home/pi/
scp stockpile-backend.tar pi@192.168.182.23:/home/pi/
