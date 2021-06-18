# Customize below to fit your system

# paths
PREFIX = /usr/share/gpigeon
COOKIES_DIR = $(PREFIX)/cookies
_GPG_HOMEDIR = $(PREFIX)/gnupg
LINK_TEMPLATE_PATH = $(PREFIX)/link-tmpl.cgi
WWWPREFIX = /var/www/gpigeon
GPIGEON_PATH = $(WWWPREFIX)/cgi-bin/gpigeon.cgi

# CGI tuning stuff
MSG_FORM_CHAR_LIMIT = 3000

# argon2id hash. generated by genpass.pl if empty when running make
ARGON2ID_HASH =

# gpg and email vars
HAS_MAILSERVER = 0# choose 0 if you'll use an external mail server, 1 if local mail server installed.
# you don't need to set the 3 last variables if you got a local mailserver.
MYGPG_ID_0XLONG =# the 0xlong format of your gpg key. - required
MYMAIL_ADDR =# your mail address - required
MAILSENDER =# the mailer address that'll send you the encrypted mails - required
MAILSENDER_PW =# password for the mailer address
SMTP_DOMAIN =# smtp domain pour the mailer
SMTP_PORT =# smtp port for the mailer

#optional, domain to generate nginx config for
#and where to put the config
WWWDOMAIN=
NGINXCONFDIR=/etc/nginx/sites-enabled
