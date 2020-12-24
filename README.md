GPIGEON
========

Gpigeon generate links for a GPG user to be sent to a non technical person (or
not a GPG user) so they can send you encrypted mail messages via a one-time
web link.
Feels of déjàvu ? I was inspired by https://hawkpost.co but wasn't really
interested in the multi-user perspective and managing a database.

Features
========

    * Single user: no database required.
    * One-time GPG form: after sending the encrypted message, the generated form
    self-destructs.
    * A table of the links generated is visible when you connect so you can
    keep track. You can also delete link individually or all at once.

Dependencies
============

You need perl and the following modules and my perl version is v5.32.0, YMMV:

    * Net:SSLeay
    * Digest::SHA 
    * Email::Valid 
    * String::Random 
    * HTML::Entities
    * CGI (I'm planning on removing it, I use it just for the
    convenient param function.) 
    * CGI::Carp (primarly for debugging, comment the line in
    gpigeon-template.cgi if you won't need it)
    * Net::SMTP
    * Net::SMTPS
    * GPG

Having a webserver with CGI support or a separate CGI engine is needed. I'm using
nginx and fcgiwrap.
A note on Net::SMTP and Net:SMTPS dependencies: if you have a mailserver well
configured with OpenDKIM and the likes (so your chances to get your mail
treated as spam is greatly reduced) you could replace these two deps with
Mail::Sendmail then comment and uncomment some lines in <gpigeon-template.cgi>.


Installation
============

I'm currently making a install script but frankly if you look around in
the <gpigeon-template.cgi> source code you should figure things out quickly (hint: look for variables
values ending in 'goes_here').
