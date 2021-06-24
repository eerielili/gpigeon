# Customize below to fit your system

# prefixes
BINPREFIX = /usr/local/bin
PREFIX = /usr/share
WWWPREFIX = /var/www

# system stuff
WWWUSER = 'www-data'

# paths
COOKIES_DIR = $(PREFIX)/gpigeon/cookies
_GPG_HOMEDIR = $(PREFIX)/gpigeon/gnupg
WWWDIR = $(WWWPREFIX)/gpigeon
LINK_TEMPLATE_PATH = $(PREFIX)/gpigeon/link-tmpl.cgi
GPIGEON_PATH = $(WWWDIR)/cgi-bin/gpigeon.cgi
DB_PATH=$(PREFIX)/gpigeon/the.db

# one time gpg form tuning
MSG_FORM_CHAR_LIMIT = 3000

# gpg and email vars
HAS_MAILSERVER = 0# choose 0 if you'll use an external mail server, 1 if local mail server installed.

# you don't need to set these variables 
# below if you got a local mailserver.
MAILSENDER =# the mailer address that'll send you the encrypted mails
MAILSENDER_PW =# password for the mailer address
SMTP_DOMAIN =# smtp domain pour the mailer
SMTP_PORT =# smtp port for the mailer

#optional, domain to generate nginx config for
#and where to put the config
WWWDOMAIN=
NGINXCONFDIR=/etc/nginx/sites-enabled
