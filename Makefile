.POSIX:

BOLD=\033[01m
RED=\033[31m
STOP=\033[0m
include config.mk

gpigeon: gpigeon-template.cgi link-tmpl-template.cgi
	$(MAKE) gpigeonctl;
	
	@if test -n '$(LINK_TEMPLATE_PATH)'; then \
		printf "\nLink template is at ${BOLD}$(LINK_TEMPLATE_PATH)${STOP}\n"; \
	else \
		printf "\n${RED}The path for the link template wasn't set in your config.mk. Fix that.${STOP}" ;\
		exit 1;\
	fi
	@if test -n '$(UPLOAD_TMPDIR)'; then \
	    printf "\nUploaded files will be temporary stored at ${BOLD}$(UPLOAD_TMPDIR)${STOP}"; \
	else \
	    printf "\n${RED}The temporary directory for uploaded files wasn't set in your config.mk. Fix that.${STOP}" ;\
	    exit 1;\
	fi
	
	@if test -n '$(MSG_FORM_CHAR_LIMIT)'; then \
       	printf "\nMessage form will have a message limit of ${BOLD}$(MSG_FORM_CHAR_LIMIT) characters${STOP}\n"; \
   	else \
	    printf "${RED}No character limits were defined in your config.mk. Fix that.${STOP}\n" ;\
	    $(MAKE) clean ;\
     	exit 1;\
	fi
	@if test -n '$(MAILSENDER)'; then \
		printf "Encrypted mails will be sent from ${BOLD}$(MAILSENDER)${STOP}\n"; \
	else \
		printf "${RED}No mail sender adress configured in your config.mk. Fix this.${STOP}\n" ; \
		$(MAKE) clean ; \
		exit 1; \
	fi
	@sed -e 's|bin_path_goes_here|$(BINPREFIX)|g' gpigeon-template.cgi > gpigeon.cgi;
	@sed -e 's|db_path_goes_here|$(DB_PATH)|g' -i gpigeon.cgi;
	@sed -e 's|link_template_path_goes_here|$(LINK_TEMPLATE_PATH)|g' -i gpigeon.cgi; 
	@sed -e 's|cookies_dir_goes_here|$(COOKIES_DIR)|g' -i gpigeon.cgi;
	@sed -e 's|bin_path_goes_here|$(BINPREFIX)|g' link-tmpl-template.cgi > link-tmpl.cgi;
	@sed -e "s|msg_char_limit_goes_here|$(MSG_FORM_CHAR_LIMIT)|g" -i link-tmpl.cgi;
	@sed -e 's|has_mailserver_goes_here|$(HAS_MAILSERVER)|g' -i link-tmpl.cgi;
	@sed -e 's|sender_addr_goes_here|$(MAILSENDER)|g' -i link-tmpl.cgi;
	@sed -e 's|gpg_homedir_goes_here|$(_GPG_HOMEDIR)|g' -i link-tmpl.cgi;
	@sed -e 's|tmp_dir_goes_here|$(UPLOAD_TMPDIR)|g' -i link-tmpl.cgi; \
	
	@if [ '${HAS_MAILSERVER}' == '1' ]; then \
		printf "Local mail server setup. ${BOLD}Mail::Sendmail module will be used to send the mails${STOP}.\n"; \
	else \
		printf "External mail server setup. ${BOLD}Net::SMTPS module will be used to send the mails${STOP}.\n"; \
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
	@if test -n '$(WWWDOMAIN)' && test -n '$(WWWPREFIX)'; then\
		$(MAKE) nginxconf;\
		printf "Done generating $(WWWDOMAIN).conf for nginx.";\
	fi
	
	@printf "\nDone preparing files. You can now type\n\t$$ sudo make install\nin your terminal.\n"

gpigeonctl: gpigeonctl.def.pl
	@$(MAKE) check_cookiesdir;
	@$(MAKE) check_dbpath;
	@$(MAKE) check_prefixes;
	@$(MAKE) check_gpghomedir;
	@if test -n '$(WWWUSER)'; then \
	    printf "The following UNIX user will be used for chowning and gpigeonctl: ${BOLD}$(WWWUSER)${STOP}\n"; \
	else \
	    printf "\t${RED}No user configured. Check your config.mk${STOP}.\n"; \
	    $(MAKE) clean ; \
	    exit 1; \
	fi
	@if test -n '$(WWWGROUP)'; then \
	    printf "The following UNIX group will be used for chowning: ${BOLD}$(WWWGROUP)${STOP}\n"; \
	else \
	    printf "\t${RED}No group configured. Check your config.mk${STOP}.\n"; \
	    $(MAKE) clean ; \
	    exit 1; \
	fi
	@sed -e 's|gpgdir_goes_here|$(_GPG_HOMEDIR)|g' gpigeonctl.def.pl > gpigeonctl;
	@sed -e 's|cookies_dir_goes_here|$(COOKIES_DIR)|g' -i gpigeonctl ;
	@sed -e 's|db_path_goes_here|$(DB_PATH)|g' -i gpigeonctl;
	@sed -e 's|web_user_goes_here|$(WWWUSER)|g' -i gpigeonctl;
	@sed -e 's|web_dir_goes_here|$(WWWDIR)|g' -i gpigeonctl;
	@sed -e 's|bin_path_goes_here|$(BINPREFIX)|g' -i gpigeonctl;
	@chmod +x gpigeonctl;

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
	chown $(WWWUSER):$(WWWGROUP) -R $(DESTDIR)$(GPIGEON_DIR)
	@printf "Done. Now execute `gpigeonctl init' to initialize the database.\n"

nginxconf: nginx-example.conf
	@sed -e 's|wwwpath_goes_here|$(WWWPREFIX)|g;s|domain_goes_here|$(WWWDOMAIN)|g' nginx-example.conf > $(WWWDOMAIN).conf ;\
	
	
uninstall:
	rm -f $(DESTDIR)$(BINPREFIX)/gpigeonctl
	rm -rf $(DESTDIR)$(GPIGEON_DIR)
	rm -rf $(DESTDIR)$(WWWDIR)
	
clean:
	rm -f genpass.txt gpg.txt link-tmpl.cgi gpigeon.cgi $(WWWDOMAIN).conf the.db gpigeonctl

check_cookiesdir:
	@if test -n '$(COOKIES_DIR)'; then \
	    printf "\nThe cookies will be stored in ${BOLD}$(COOKIES_DIR)${STOP}"; \
	else \
	    printf "\n${RED}No cookie directory configured. Check your config.def.mk for the defaults and fix that.${STOP}" ;\
	    exit 1; \
	fi

check_dbpath:
	@if test -z '$(DB_PATH)'; then\
		printf "\n${RED}No database path defined in config.mk. Check your config.def.mk for the defaults and fix that in your config.mk$(STOP)";\
		exit 1; \
	else \
		printf "\nThe path to the SQLite database is $(BOLD)$(DB_PATH)$(STOP)";\
	fi

check_prefixes:
	@if test -z '$(PREFIX)'; then \
		printf "\n$(RED)No \u0024PREFIX variable defined in config.mk.\n";\
		printf "Look into config.def.mk for the defaults and fix that in your config.mk.$(STOP)\n";\
		exit 1;\
	else \
		printf "\n\u0024PREFIX var is set to $(BOLD)$(PREFIX)$(STOP)";\
	fi
	@if test -z '$(BINPREFIX)'; then \
		printf "\n$(RED)No \u0024BINPREFIX variable defined in config.mk.\n";\
		printf "Look into config.def.mk for the defaults and fix that in your config.mk.$(STOP)\n";\
		exit 1;\
	else \
		printf "\n\u0024BINPREFIX var is set to $(BOLD)$(BINPREFIX)$(STOP)";\
	fi
	@if test -z '$(WWWPREFIX)'; then\
		printf "\n${RED}No web directory defined in config.mk. Check your config.def.mk for the defaults and fix that in your config.mk.${STOP}";\
		exit 1; \
	else \
		printf "\nThe WWW directory is $(BOLD)$(WWWDIR)$(STOP)";\
	fi

check_gpghomedir:
	@if test -n '$(_GPG_HOMEDIR)'; then \
		printf "\nThe home directory for GPG will be ${BOLD}$(_GPG_HOMEDIR)${STOP}" ;\
	else \
	        printf "\n${RED}The GPG home directory for gpigeon wasn't set in config.mk . Fix that.${STOP}" ;\
	        $(MAKE) clean ;\
        	exit 1;\
	fi

.PHONY: clean install uninstall
