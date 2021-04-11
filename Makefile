.POSIX:

include config.mk

install:
	mkdir -p $(DESTDIR)$(PREFIX)/cookies
	mkdir -p $(DESTDIR)$(_GPG_HOMEDIR)
	chmod 700 $(DESTDIR)$(_GPG_HOMEDIR)
	mkdir -p $(DESTDIR)$(WWWPREFIX)/cgi-bin/l
	cp -f gpigeon-template.cgi $(DESTDIR)$(WWWPREFIX)/cgi-bin/gpigeon.cgi
	chmod 700 $(DESTDIR)$(WWWPREFIX)/cgi-bin/gpigeon.cgi
	if test -z '$(ARGON2ID_HASH)'; then \
		perl genpass.pl > genpass.txt; \
		ARGON2ID_HASH="`tail -1 genpass.txt`"; \
	fi
	sed -e 's|argon2id_hash_goes_here|$(ARGON2ID_HASH)|g' -i $(DESTDIR)$(WWWPREFIX)/cgi-bin/gpigeon.cgi
	sed -e "s|cookies_dir_goes_here|$(COOKIES_DIR)|g" -i $(DESTDIR)$(WWWPREFIX)/cgi-bin/gpigeon.cgi
	sed -e "s|link_template_path_goes_here|$(LINK_TEMPLATE_PATH)|g" -i $(DESTDIR)$(WWWPREFIX)/cgi-bin/gpigeon.cgi
	sed -e "s|msg_char_limit_goes_here|$(MSG_FORM_CHAR_LIMIT)|g" -i $(DESTDIR)$(LINK_TEMPLATE_PATH)
	cp -f link-tmpl.cgi $(DESTDIR)$(LINK_TEMPLATE_PATH)
	chmod 600 $(DESTDIR)$(LINK_TEMPLATE_PATH)
	if test -n '$(MYMAIL_ADDR)'; then \
		sed -e "s|your_addr_goes_here|$(MYMAIL_ADDR)|g" -i $(DESTDIR)$(LINK_TEMPLATE_PATH); \
	fi
	if test -n '$(MYGPG_ID_0XLONG)'; then \
		sed -e "s|gpgid_goes_here|$(MYGPG_ID_0XLONG)|g" -i $(DESTDIR)$(LINK_TEMPLATE_PATH); \
		gpg --armor --export $(MYGPG_ID_0XLONG) > gpg.txt; \
		gpg --homedir "$(_GPG_HOMEDIR)" --import gpg.txt; \
	fi
	if test -n '$(MAILSENDER)'; then \
		sed -e "s|sender_addr_goes_here|$(MAILSENDER)|g" -i $(DESTDIR)$(LINK_TEMPLATE_PATH); \
	fi
	if test -n '$(SMTP_DOMAIN)'; then \
		sed -e "s|smtp_domain_goes_here|$(SMTP_DOMAIN)|g" -i $(DESTDIR)$(LINK_TEMPLATE_PATH); \
	fi
	if test -n '$(SMTP_PORT)'; then \
		sed -e "s|smtp_port_goes_here|$(SMTP_PORT)|g" -i $(DESTDIR)$(LINK_TEMPLATE_PATH); \
	fi
	if test -n '$(MAILSENDER_PW)'; then \
		sed -e "s|sender_pw_goes_here|$(MAILSENDER_PW)|g" -i $(DESTDIR)$(LINK_TEMPLATE_PATH); \
	fi
	sed -e "s|has_mailserver_goes_here|$(HAS_MAILSERVER)|g" -i $(DESTDIR)$(LINK_TEMPLATE_PATH)
	sed -e "s|gpg_homedir_goes_here|$(_GPG_HOMEDIR)|g" -i $(DESTDIR)$(LINK_TEMPLATE_PATH)
	cp -f styles.css $(DESTDIR)$(WWWPREFIX)
	chmod 644 $(DESTDIR)$(WWWPREFIX)/styles.css
	cp -f favicon.ico $(DESTDIR)$(WWWPREFIX)
	chmod 644 $(DESTDIR)$(WWWPREFIX)/favicon.ico
	cp -rf merci $(DESTDIR)$(PREFIX)
	chmod 755 -R $(DESTDIR)$(PREFIX)
	if test -e 'genpass.txt'; then \
	    printf "\n\nThe variable ARGON2ID_HASH wasn't declared thus a password and its argon2id hash as been generated (look into genpass.txt)."; \
	    printf "\nYour password is:\n`head -1 genpass.txt`\n\n\n"; \
	    rm -rf genpass.txt; \
	fi

uninstall:
	rm -rf $(DESTDIR)$(PREFIX)
	rm -rf $(DESTDIR)$(WWWPREFIX)
	
clean:
	rm -f genpass.txt gpg.txt

.PHONY: clean install uninstall
