.POSIX:

BOLD=\033[01m
RED=\033[31m
STOP=\033[0m
include config.mk

gpigeon: gpigeon-template.cgi link-tmpl-template.cgi
	@if test -z '$(BINPREFIX)'; then \
		printf "\n$(RED)No \u0024BINPREFIX variable defined in config.mk.\n";\
		printf "Look into config.def.mk for the defaults and fix that in your config.mk.$(STOP)\n";\
		exit 1;\
	else \
		printf "\n\u0024BINPREFIX var is set to $(BOLD)$(BINPREFIX)$(STOP)";\
	fi
	@if test -z '$(PREFIX)'; then \
		printf "\n$(RED)No \u0024PREFIX variable defined in config.mk.\n";\
		printf "Look into config.def.mk for the defaults and fix that in your config.mk.$(STOP)\n";\
		exit 1;\
	else \
		printf "\n\u0024PREFIX var is set to $(BOLD)$(PREFIX)$(STOP)";\
	fi
	@if test -z '$(WWWPREFIX)'; then\
		printf "\n${RED}No web directory defined in config.mk. Check your config.def.mk for the defaults and fix that in your config.mk.${STOP}";\
		exit 1; \
	else \
		printf "\nThe WWW directory is $(BOLD)$(WWWDIR)$(STOP)";\
	fi
	@if test -z '$(DB_PATH)'; then\
		printf "\n${RED}No database path defined in config.mk. Check your config.def.mk for the defaults and fix that in your config.mk$(STOP)";\
		exit 1; \
	else \
		printf "\nThe path to the SQLite database is $(BOLD)$(DB_PATH)$(STOP)";\
	    sed -e 's|db_path_goes_here|$(DB_PATH)|g' gpigeon-template.cgi > gpigeon.cgi;\
	fi
	
	@if test -n '$(_GPG_HOMEDIR)'; then \
		printf "\nThe home directory for GPG will be ${BOLD}$(_GPG_HOMEDIR)${STOP}" ;\
	else \
	        printf "\n${RED}The GPG home directory for gpigeon wasn't set in config.mk . Fix that.${STOP}" ;\
	        $(MAKE) clean ;\
        	exit 1;\
	fi
	
	@if test -n '$(LINK_TEMPLATE_PATH)'; then \
		printf "\nLink template is at ${BOLD}$(LINK_TEMPLATE_PATH)${STOP}\n"; \
		sed -e 's|link_template_path_goes_here|$(LINK_TEMPLATE_PATH)|g' -i gpigeon.cgi; \
	else \
		printf "\n${RED}The path for the link template wasn't set in your config.mk. Fix that.${STOP}" ;\
		exit 1;\
	fi
	
	@if test -n '$(MSG_FORM_CHAR_LIMIT)'; then \
       	printf "Message form will have a message limit of ${BOLD}$(MSG_FORM_CHAR_LIMIT) characters${STOP}\n"; \
		sed -e "s|msg_char_limit_goes_here|$(MSG_FORM_CHAR_LIMIT)|g" link-tmpl-template.cgi > link-tmpl.cgi;\
   	else \
	    printf "${RED}No character limits were defined in your config.mk. Fix that.${STOP}\n" ;\
	    $(MAKE) clean ;\
     	exit 1;\
	fi
	
	@if [ '${HAS_MAILSERVER}' == '1' ]; then \
		printf "Local mail server setup. ${BOLD}Mail::Sendmail module will be used to send the mails${STOP}.\n"; \
	else \
		printf "External mail server setup. ${BOLD}Net::SMTPS module will be used to send the mails${STOP}.\n"; \
		if test -n '$(MAILSENDER)'; then \
			printf "\tEncrypted mails will be sent from ${BOLD}$(MAILSENDER)${STOP}\n"; \
			sed -e 's|sender_addr_goes_here|$(MAILSENDER)|g' -i link-tmpl.cgi; \
		else \
			printf "\t${RED}No mail sender adress configured in your config.mk. Fix this.${STOP}\n" ; \
			$(MAKE) clean ; \
			exit 1; \
		fi; \
		if test -n '$(MAILSENDER_PW)'; then \
			printf "\tPassword for ${BOLD}${MAILSENDER}${STOP} is %s.\n" '${MAILSENDER_PW}'; \
			sed -e 's|sender_pw_goes_here|$(MAILSENDER_PW)|g' -i link-tmpl.cgi; \
		else\
			printf "\t${RED}Password for the sender address wasn't set in your config.mk. Fix this${STOP}.\n";\
			$(MAKE) clean ; \
			exit 1; \
		fi; \
		if test -n '$(SMTP_DOMAIN)'; then \
			printf "\tSMTP server: ${BOLD}$(SMTP_DOMAIN)${STOP}\n"; \
			sed -e 's|smtp_domain_goes_here|$(SMTP_DOMAIN)|g' -i link-tmpl.cgi; \
		else\
			printf "\t${RED}No SMTP server was configured in your config.mk. Fix this.${STOP}\n";\
			$(MAKE) clean ; \
			exit 1; \
		fi; \
		if test -n '$(SMTP_PORT)'; then \
			printf "\tSMTP port: ${BOLD}$(SMTP_PORT)${STOP}\n"; \
			sed -e 's|smtp_port_goes_here|$(SMTP_PORT)|g' -i link-tmpl.cgi; \
		else \
			printf "\t${RED}No SMTP port configured in your config.mk. Fix this${STOP}.\n"; \
			$(MAKE) clean ; \
			exit 1; \
		fi; \
	fi
	
	@sed -e 's|has_mailserver_goes_here|$(HAS_MAILSERVER)|g' -i link-tmpl.cgi;
	@sed -e 's|gpg_homedir_goes_here|$(_GPG_HOMEDIR)|g' -i link-tmpl.cgi;
	@if test -n '$(WWWDOMAIN)' && test -n '$(WWWPREFIX)'; then\
		$(MAKE) nginxconf;\
		printf "Done generating $(WWWDOMAIN).conf for nginx.";\
	fi
	@printf "\nDone preparing files. You can now type\n\t$$ sudo make install\nin your terminal.\n"

gpigeonctl: gpigeonctl.def.pl
	@sed -e 's|gpgdir_goes_here|$(_GPG_HOMEDIR)|g' gpigeonctl.def.pl > gpigeonctl;
	@sed -e 's|cookies_dir_goes_here|$(COOKIES_DIR)|g' -i gpigeonctl ;
	@sed -e 's|db_path_goes_here|$(DB_PATH)|g' -i gpigeonctl;
	@sed -e 's|web_user_goes_here|$(WWWUSER)|g' -i gpigeonctl;
	@sed -e 's|web_dir_goes_here|$(WWWDIR)|g' -i gpigeonctl;
	chmod +x gpigeonctl;

install:
	$(MAKE) gpigeon gpigeonctl;
	@if test -n "$(WWWDOMAIN)"; then\
	    $(MAKE) nginxconf;\
		printf "\nInstalling $(WWWDOMAIN).conf into $(NGINXCONFDIR)\n";\
		install -Dm644 $(WWWDOMAIN).conf -t $(DESTDIR)$(NGINXCONFDIR);\
	fi
	mkdir -p $(DESTDIR)$(COOKIES_DIR);
	mkdir -m700 -p $(DESTDIR)$(_GPG_HOMEDIR)
	mkdir -p $(DESTDIR)$(WWWDIR)/cgi-bin/l
	install -Dm700 gpigeon.cgi $(DESTDIR)$(GPIGEON_PATH)
	install -Dm600 link-tmpl.cgi $(DESTDIR)$(LINK_TEMPLATE_PATH)
	install -Dm644 index.html favicon.ico styles.css -t $(DESTDIR)$(WWWDIR)/
	install -Dm755 gpigeonctl -t $(DESTDIR)$(BINPREFIX)
	@printf "Done. Now execute `gpigeonctl init' to initialize the database.\n"

nginxconf: nginx-example.conf
	@sed -e 's|wwwpath_goes_here|$(WWWPREFIX)|g;s|domain_goes_here|$(WWWDOMAIN)|g' nginx-example.conf > $(WWWDOMAIN).conf ;\
	
	
uninstall:
	rm -f $(DESTDIR)$(BINPREFIX)/gpigeonctl
	rm -rf $(DESTDIR)$(PREFIX)/gpigeon
	rm -rf $(DESTDIR)$(WWWDIR)
	
clean:
	rm -f genpass.txt gpg.txt link-tmpl.cgi gpigeon.cgi $(WWWDOMAIN).conf the.db gpigeonctl

.PHONY: clean install uninstall
