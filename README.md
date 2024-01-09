# Development

* Run bot: `pdm run telegram`
* Run web `pdm run web`

## SQL Alchemy

### First migration
Useful just for a while

1. Delete the sql database and the old first migration
  * The deletion of the database is not 100% needed but then you will have an inconsistent state with the ORM
2. Run `pdm run alembic revision --autogenerate -m "First version"`
3. Run `pdm run alembic upgrade head`

# Next steps

* Try the dynamic load of urls, per day