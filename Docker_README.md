Running with Docker
===

Sample Run command
-----
```bash
docker run -d --name ytsm -p 80:8000 --volume /media/ytsm/data:/usr/src/ytsm/data --volume /media/ytsm/config:/usr/src/ytsm/config chibicitiberiu/ytsm:latest
```
### Quick Rundown:
- `--expose 80:8000` maps the Host OS port 80 to the container port 80
- `--volume /media/ytsm/data:/usr/src/app/data` maps the data folder on the host to the container folder `data`
- `--volume /media/ytsm/coinfig:/usr/src/app/config` maps the config folder on the host to the container folder `config`
- `chibicitiberiu/ytsm:latest` tells Docker which image to run the container with (in this case, the latest version)


Environment variables
-----
- YTSM_DATABASE_ENGINE
- YTSM_DATABASE_NAME
- YTSM_YOUTUBE_API_KEY


Volumes
-----
- /data
- /config
- /downloads


Notes
----
If you experience any issues with the app running, make sure to run the following command to apply Django migrations to the database

### When using just the Dockerfile/Image
- `docker exec ytsm python manage.py migrate`

### When using the docker-compose file
- `docker exec ytsm_web_1 python manage.py migrate`
