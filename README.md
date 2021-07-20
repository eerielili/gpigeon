GPIGEON
========

Gpigeon generate links for a GPG user to be sent to a non technical person (or
not a GPG user) so they can send you encrypted mail messages via a one-time
web link.
Feels of déjàvu ? I was inspired by [https://hawkpost.co](https://hawkpost.co) but wasn't really
interested in the multi-user perspective and managing a database.
I've recently added minimal support for multiple users, but adding them
is done via the command line, and you'll have to import public
GPG keys into your keyring first.
I plan on adding invites in the future, generated by command line
then directly from web interface.

Features
========

- One-time GPG form: after sending the encrypted message, the generated form
    self-destructs.
- Cookie based login. If you block cookies, it will switch back to
    hidden fields so you can still login.
- A table of the links generated is visible when you connect so you can
    keep track of what has been created. You can also delete link
    individually, or all at once.
- No javascript used for the moment.

Dependencies
============

You will need perl and the following modules and my perl version is **v5.34.0**, YMMV:

- CGI
- CGI::Carp
- CGI::Cookie
- Crypt::Argon2
- DBI
- DBD::SQLite
- Email::Valid
- Mail::GPG
- MIME::Entity
- File::Path and File::stat (available by default in recent perl installs)
- Net:SSLeay
- Net::SMTP
- Net::SMTPS
- String::Random 
- Term::ReadKey

Having a webserver with CGI support or a separate CGI engine is needed. I'm using
nginx and fcgiwrap.
A note on **Net::SMTP** and **Net:SMTPS** dependencies: if you have a well
configured mailserver on the same server you plan to install gpigeon on, you should set the `HAS_MAILSERVER`
variable in `config.mk` to 1.


Installation
============

Don't forget to copy `config.def.mk` into `config.mk` and tune
the variables to your liking. Then, you can run the good old:
```
make install
```

You should also look in the
[gpigeon-template.cgi](https://git.les-miquelots.net/gpigeon/plain/gpigeon-template.cgi)
and [link-tmpl-template.cgi](https://git.les-miquelots.net/gpigeon/plain/link-tmpl-template.cgi) source code, you should figure things out quickly.
**Hint**: look for variables values ending in _goes_here_.

Your nginx configuration should look like this:
```nginx
server {
    listen 80;
    server_name ggon.example.com;

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;

    root /var/www/gpigeon;
    server_name ggon.example.com;
    ssl_certificate /etc/letsencrypt/live/ggon.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ggon.example.com/privkey.pem;
    error_log /var/log/gpigeon.log;
    index index.html index.htm;

    location = / {
        return 301 /cgi-bin/gpigeon.cgi;
    }

    location = /cgi-bin/gpigeon.cgi {
        ssi off;
        gzip off;
        fastcgi_pass unix:/run/fcgiwrap.sock;
        include /etc/nginx/fastcgi_params;
    }

    location ~ ^/cgi-bin/l/(.*).cgi$ {
        ssi off;
        gzip off;
        fastcgi_pass unix:/run/fcgiwrap.sock;
        include /etc/nginx/fastcgi_params;
    }

    add_header Strict-Transport-Security "max-age=63072000; preload";
    add_header Content-Security-Policy "default-src 'self'";
    add_header X-Frame-Options DENY;
    add_header Access-Control-Allow-Origin https://$server_name;
    add_header Vary Origin; # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Access-Control-Allow-Origin#cors_and_caching
}
```
You can also tune the `WWWDOMAIN` and `NGINXCONFDIR` variable in your `config.mk` to have it generated for you when running `make`.


Managing the service
====================

Thanks to the `gpigeonctl` script, you can :
- Initialize the database with (`init`)
- Add an user (`adduser`)
- Delete an user (`deluser`)
- Clean cookies (`cleancookies`)
- Clean generated links (`cleanlinks`)

The script is mostly interactive, so no automatic adding of user
at the moment.
