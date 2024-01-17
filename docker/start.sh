#!/bin/ash

alembic upgrade head

exec /usr/bin/supervisord -c /etc/supervisord.conf