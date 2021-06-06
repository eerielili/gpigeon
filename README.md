GPIGEON
========

Gpigeon generate links for a GPG user to be sent to a non technical person (or
not a GPG user) so they can send you encrypted mail messages via a one-time
web link.
Feels of déjàvu ? I was inspired by [https://hawkpost.co](https://hawpost.co) but wasn't really
interested in the multi-user perspective and managing a database.

Features
========

- Single user: no database required.
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

- HTML::Entities
- CGI
- CGI::Carp
- CGI::Cookies
- Crypt::Argon2
- GPG
- Net:SSLeay
- Net::SMTP
- Net::SMTPS
- Email::Valid 
- String::Random 

Having a webserver with CGI support or a separate CGI engine is needed. I'm using
nginx and fcgiwrap.
A note on **Net::SMTP** and **Net:SMTPS** dependencies: if you have a mailserver well
configured with SPF and OpenDKIM (so your chances to get your mail
treated as spam is greatly reduced) you should set the `HAS_MAILSERVER`
variable in
[link-tmpl.cgi](https://git.les-miquelots.net/gpigeon/plain/link-tmpl.cgi) to 1.


Installation
============

Don't forget to copy `config.def.mk` into `config.mk` and tune
the variable to your liking. Then, you can run the good old:
```
make
make install #you'll maybe need sudo though
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

    include errorpages.conf;
}
```
