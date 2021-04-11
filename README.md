GPIGEON
========

Gpigeon generate links for a non technical person or someone not familiar
with GPG, so they can send you encrypted mails via a one-time
web form.
Feels of déjàvu ? I was inspired by https://hawkpost.co but wasn't really
interested in the multi-user perspective and managing a database.

Overview
========

    * Single user.
    * One-time GPG form: after sending the encrypted message, the generated form
    self-destructs.
    * Cookie based login. If you block cookies, it will switch back to
    hidden fields so you can still login, manage and create links.
    * A table of the links generated is visible after connecting so you can
    keep track of what has been created. You can also delete links
    individually, or all at once.
    * No javascript used for the moment.

Dependencies
============

You will need perl and the following modules and my perl version is v5.32.0, YMMV:

    * HTML::Entities
    * CGI
    * CGI::Carp
    * CGI::Cookies
    * Crypt::Argon2
    * GPG
    * Net:SSLeay
    * Net::SMTP
    * Net::SMTPS
    * Email::Valid 
    * String::Random 

Having a webserver with CGI support or a separate CGI engine is needed. I'm using
nginx and fcgiwrap.
A note on Net::SMTP and Net:SMTPS dependencies: if you have a mailserver well
configured with SPF and OpenDKIM (so your chances to get your mail
treated as spam is greatly reduced) you should set the `HAS_MAILSERVER`
variable to 1 in the config.mk file.


Installation
============

Edit the config.mk file to customize the installation to your needs, and then
execute:
`sudo make`

You should also look in the
[gpigeon-template.cgi](https://git.les-miquelots.net/gpigeon/plain/gpigeon-template.cgi)
and [link-tmpl.cgi](https://git.les-miquelots.net/gpigeon/plain/link-tmpl.cgi) source code, you should figure things out quickly.
**Hint**: look for variables values ending in _goes_here_.
