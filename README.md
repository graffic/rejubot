# Development

* Run bot: `pdm run telegram`
* Run web `pdm run web`

## With docker

* Build image: `docker build -f docker/Dockerfile . -t rejubot`
* Run: `docker run --rm -it -v $PWD/config/:/project/config/ -p 8080:8080 rejubot`

## SQL Alchemy

### First migration
Useful just for a while

1. Delete the sql database and the old first migration
  * The deletion of the database is not 100% needed but then you will have an inconsistent state with the ORM
2. Run `pdm run alembic revision --autogenerate -m "First version"`
3. Run `pdm run alembic upgrade head`


## Admin

### Import data

* Use Telegram Desktop to export data
* filter the export with:
```
jq '[.messages[] | select(any(.text_entities[]; .type == "link")) ]|reverse' result.json > all.urls.json
```
* The exported timestamps are in the timezone of the client. In this case UTC+1


# Next steps

* `ddinstagram` links with videos do not have a full url in the video url.