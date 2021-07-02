# Customize below to fit your system

# paths
PREFIX = /usr/share/gpigeon
WWWPREFIX = /var/www
COOKIES_DIR = $(PREFIX)/cookies
_GPG_HOMEDIR = $(PREFIX)/gnupg
LINK_TEMPLATE_PATH = $(PREFIX)/link-tmpl.cgi
GPIGEON_PATH = $(WWWPREFIX)/cgi-bin/gpigeon.cgi

# system stuff
WEBUSER=www-data #it must match up with your nginx user. For ex. on arch it's 'http'

# form customization stuff
MSG_FORM_CHAR_LIMIT = 3000

# argon2id hash. generated by genpass.pl if empty when running make
ARGON2ID_HASH =

# email related
HAS_MAILSERVER = 0# choose 0 if you'll use an external mail server, 1 if local mail server installed.
MYMAIL_ADDR =# your mail address - required
MAILSENDER =# the mailer address that'll send you the encrypted mails - required
# you don't need to set the 3 last variables if you got a local mailserver.
MAILSENDER_PW =# password for the mailer address
SMTP_DOMAIN =# smtp domain pour the mailer
SMTP_PORT =# smtp port for the mailer

#optional, domain to generate nginx config for
#and where to put the config
WWWDOMAIN=
SITESENABLED=/etc/nginx/sites-enabled
