.POSIX:

# you should comment this line @if non-GNU make
# and execute genpass.pl manually and edit config.mk
# with the resulting argon2id hash.
BOLD=\033[01m
RED=\033[31m
STOP=\033[0m
RANDOM_ARGON2 := $(shell perl genpass.pl > genpass.txt && tail -1 genpass.txt)
include config.mk

gpigeon: gpigeon-template.cgi link-tmpl-template.cgi
	@if test -z '$(PREFIX)'; then \
		printf "\n$(RED)No \u0024PREFIX variable defined in config.mk.\n";\
		printf "Look into config.def.mk for the defaults and fix that.$(STOP)\n";\
		exit 1;\
	else \
		printf "\n\u0024PREFIX var is set to $(BOLD)$(PREFIX)$(STOP)";\
	fi
	
	@if test -z '$(WWWPREFIX)'; then\
		printf "\n${RED}No web directory defined in config.mk. Check your config.def.mk for the defaults and fix that.${STOP}";\
		exit 1; \
	else \
		printf "\nThe WWW directory is $(BOLD)$(WWWPREFIX)$(STOP)";\
	fi
	
	@if test -n '$(COOKIES_DIR)'; then \
        	printf "\nThe cookies will be stored in ${BOLD}$(COOKIES_DIR)${STOP}"; \
		sed -e 's|cookies_dir_goes_here|$(COOKIES_DIR)|g;' gpigeon-template.cgi > gpigeon.cgi; \
    	else \
	        printf "\n${RED}No cookie directory configured. Check your config.def.mk for the defaults and fix that.${STOP}" ;\
        	exit 1; \
	fi
	@if test -n '$(_GPG_HOMEDIR)'; then \
		printf "\nThe home directory for GPG will be ${BOLD}$(_GPG_HOMEDIR)${STOP}" ;\
	else \
	        printf "\n${RED}The GPG home directory for gpigeon wasn't set in config.mk . Fix that.${STOP}" ;\
	        $(MAKE) clean ;\
        	exit 1;\
	fi
	@if test -n '$(LINK_TEMPLATE_PATH)'; then \
		printf "\nLink template is at ${BOLD}$(LINK_TEMPLATE_PATH)${STOP}"; \
		sed -e 's|link_template_path_goes_here|$(LINK_TEMPLATE_PATH)|g' gpigeon-template.cgi > gpigeon.cgi; \
	else \
		printf "\n${RED}The path for the link template wasn't set in your config.mk. Fix that.${STOP}" ;\
		exit 1;\
	fi
	
	@if test -n '$(ARGON2ID_HASH)'; then\
		printf "\nThe argon2id hash is ${BOLD}$(ARGON2ID_HASH)${STOP}"; \
		sed -e 's|argon2id_hash_goes_here|$(ARGON2ID_HASH)|g' gpigeon-template.cgi > gpigeon.cgi; \
 	else \
		sed -e 's|argon2id_hash_goes_here|$(RANDOM_ARGON2)|g' gpigeon-template.cgi > gpigeon.cgi; \
		printf "\nThe variable ARGON2ID_HASH wasn't declared in your config.mk thus a password \nand its argon2id hash as been generated (look into `pwd`/genpass.txt)."; \
		printf "\nYour password is:\n${BOLD}`head -1 genpass.txt`${STOP}"; \
		printf "\nAnd the hash is:\n${BOLD}%s${STOP}\n\n" '${RANDOM_ARGON2}'; \
		rm -f genpass.txt; \
	fi
	

	
	@if test -n '$(MYGPG_ID_0XLONG)'; then \
		printf "Mails will be encrypted to you with the ${BOLD}$(MYGPG_ID_0XLONG)${STOP} GPG key\n"; \
		sed -e 's|gpgid_goes_here|$(MYGPG_ID_0XLONG)|g' link-tmpl-template.cgi > link-tmpl.cgi; \
		gpg --armor --export $(MYGPG_ID_0XLONG) > gpg.txt; \
	else \
		printf "${RED}No GPG key found because the 0xlong fingerprint format wasn't set in config.mk. Fix this.${STOP}\n";\
		$(MAKE) clean;\
		exit 1 ;\
	fi

	@if test -n '$(MSG_FORM_CHAR_LIMIT)'; then \
        	printf "Message form will have a message limit of ${BOLD}$(MSG_FORM_CHAR_LIMIT) characters${STOP}\n"; \
		sed -e "s|msg_char_limit_goes_here|$(MSG_FORM_CHAR_LIMIT)|g" link-tmpl-template.cgi > link-tmpl.cgi;\
    	else \
	        printf "${RED}No character limits were defined in your config.mk. Fix that.${STOP}\n" ;\
	        $(MAKE) clean ;\
        	exit 1;\
	fi
	
	@if test -n '$(MYMAIL_ADDR)'; then \
        	printf "Your mail address is ${BOLD}$(MYMAIL_ADDR)${STOP}\n"; \
		sed -e 's|your_addr_goes_here|$(MYMAIL_ADDR)|g' link-tmpl-template.cgi > link-tmpl.cgi; \
    	else \
        	printf "There's no mail adress configured for gpigeon in your config.mk !\n" ; \
        	$(MAKE) clean ; \
        	exit 1; \
	fi
	
	
	
	@if [ '${HAS_MAILSERVER}' == '1' ]; then \
		printf "Local mail server setup. ${BOLD}Mail::Sendmail module will be used to send the mails${STOP}.\n"; \
	else \
		printf "External mail server setup. ${BOLD}Net::SMTPS module will be used to send the mails${STOP}.\n"; \
		if test -n '$(MAILSENDER)'; then \
			printf "\tEncrypted mails will be sent from ${BOLD}$(MAILSENDER)${STOP}\n"; \
			sed -e 's|sender_addr_goes_here|$(MAILSENDER)|g' link-tmpl-template.cgi > link-tmpl.cgi; \
		else \
			printf "\t${RED}No mail sender adress configured in your config.mk. Fix this.${STOP}\n" ; \
			$(MAKE) clean ; \
			exit 1; \
		fi; \
		if test -n '$(MAILSENDER_PW)'; then \
			printf "\tPassword for ${BOLD}${MAILSENDER}${STOP} is %s.\n" '${MAILSENDER_PW}'; \
			sed -e 's|sender_pw_goes_here|$(MAILSENDER_PW)|g' link-tmpl-template.cgi > link-tmpl.cgi; \
		else\
			printf "\t${RED}Password for the sender address wasn't set in your config.mk. Fix this${STOP}.\n";\
			$(MAKE) clean ; \
			exit 1; \
		fi; \
		if test -n '$(SMTP_DOMAIN)'; then \
			printf "\tSMTP server: ${BOLD}$(SMTP_DOMAIN)${STOP}\n"; \
			sed -e 's|smtp_domain_goes_here|$(SMTP_DOMAIN)|g' link-tmpl-template.cgi > link-tmpl.cgi; \
		else\
			printf "\t${RED}No SMTP server was configured in your config.mk. Fix this.${STOP}\n";\
			$(MAKE) clean ; \
			exit 1; \
		fi; \
		if test -n '$(SMTP_PORT)'; then \
			printf "\tSMTP port: ${BOLD}$(SMTP_PORT)${STOP}\n"; \
			sed -e 's|smtp_port_goes_here|$(SMTP_PORT)|g' link-tmpl-template.cgi > link-tmpl.cgi; \
		else \
			printf "\t${RED}No SMTP port configured in your config.mk. Fix this${STOP}.\n"; \
			$(MAKE) clean ; \
			exit 1; \
		fi; \
	fi
	@sed -e 's|has_mailserver_goes_here|$(HAS_MAILSERVER)|g' link-tmpl-template.cgi > link-tmpl.cgi 
	@sed -e 's|gpg_homedir_goes_here|$(_GPG_HOMEDIR)|g' link-tmpl-template.cgi > link-tmpl.cgi
	@if test -n '$(WWWDOMAIN)' && test -n '$(WWWPREFIX)'; then\
		$(MAKE) nginxconf;\
		printf "Done generating $(WWWDOMAIN).conf for nginx.";\
	fi
	@printf "\nDone preparing files. You can now type\nsudo make install\nin your terminal.\n"
		
install:
	$(MAKE) gpigeon;
	mkdir -p $(DESTDIR)$(COOKIES_DIR);
	mkdir -m700 -p $(DESTDIR)$(_GPG_HOMEDIR);
	GNUPGHOME="$(DESTDIR)$(_GPG_HOMEDIR)" gpg --import gpg.txt; \
	mkdir -p $(DESTDIR)$(WWWPREFIX)/cgi-bin/l
	install -Dm700 gpigeon.cgi $(DESTDIR)$(GPIGEON_PATH)
	install -Dm600 link-tmpl.cgi $(DESTDIR)$(LINK_TEMPLATE_PATH)
	install -Dm644 index.html favicon.ico styles.css -t $(DESTDIR)$(WWWPREFIX)/gpigeon/
	install -Dm755 merci/* -t $(DESTDIR)$(PREFIX)/merci/
	@if test -e '$(WWWDOMAIN).conf'; then\
		printf "\nInstalling $(WWWDOMAIN).conf into $(NGINXCONFDIR)\n";\
		install -Dm644 $(WWWDOMAIN).conf -t $(DESTDIR)$(NGINXCONFDIR);\
	fi
	chown $(WWWUSER):$(WWWUSER) -R $(DESTDIR)$(PREFIX)/gpigeon || exit 1;
	chown $(WWWUSER):$(WWWUSER) -R $(DESTDIR)$(WWWPREFIX)/gpigeon || exit 1;

nginxconf: nginx-example.conf
	@sed -e 's|wwwpath_goes_here|$(WWWPREFIX)|g;s|domain_goes_here|$(WWWDOMAIN)|g' nginx-example.conf > $(WWWDOMAIN).conf ;\
	
	
uninstall:
	rm -rf $(DESTDIR)$(PREFIX)/gpigeon
	rm -rf $(DESTDIR)$(WWWPREFIX)/gpigeon
	
clean:
	rm -f genpass.txt gpg.txt link-tmpl.cgi gpigeon.cgi $(WWWDOMAIN).conf

.PHONY: clean install uninstall
