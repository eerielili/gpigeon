# Customize below to fit your system

# prefixes
PREFIX = /usr/share
BINPREFIX = /usr/bin
WWWPREFIX = /var/www

# system stuff
WWWUSER = 'www-data'
WWWGROUP = 'www-data'

# paths
GPIGEON_DIR=$(PREFIX)/gpigeon
COOKIES_DIR = $(GPIGEON_DIR)/cookies
UPLOAD_TMPDIR = $(GPIGEON_DIR)/tmp/
LINK_TEMPLATE_PATH = $(GPIGEON_DIR)/link-tmpl.cgi
DB_PATH=$(GPIGEON_DIR)/the.db
_GPG_HOMEDIR = $(GPIGEON_DIR)/gnupg
GPIGEON_PATH = $(WWWDIR)/cgi-bin/gpigeon.cgi
WWWDIR = $(WWWPREFIX)/gpigeon

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
