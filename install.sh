# !/bin/sh

set -o errexit
#set -o pipefail
#set -o nounset
#set -o xtrace

BOLD='\033[01m'
UNDL='\033[04m'
GREEN='\033[32m'
RED='\033[31m'
STYLE_END='\033[0m'
command -V gpg >/dev/null 2>&1 && GPG="gpg" || GPG="gpg2"
self_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
self_fullpath="$self_dir/$0"
emailre=".\+@.\+\\..\+"

### VARIABLES TO EDIT ###
HAS_MAILSERVER=0 # 0 is the default, it'll use an external smtp server (your gmail
# account /ISP subscriber mail address for example). Change to 1 if you have a local mail
# server.
# TODO: implement the sed trickery to disable and enable portions of perl code
YOUR_EMAIL=0
GPG_XLONG='0x0000000000000000' # running 'gpg -k --keyid-format 0xlong yourmail@example.com' will
# help you there.
SMTP=0
SMTP_P=465
MAIL_PW=0
SCRIPT="$self_dir/gpigeon.cgi"
GPG_DATA_DIR='/usr/share/www-data'
SCRIPT_USER='www-data'
SCRIPT_GROUP="$SCRIPT_USER"
ROOT_DIR='/var/www/gpigeon'
CGI_DIR="$ROOT_DIR/cgi-bin"
LINKS_DIR="$CGI_DIR/l"
APP_PW=0
### END VARIABLES TO EDIT ###

self_abort() {
    printf "\n${BOLD}${RED}Aborting...${STYLE_END}\n"
    exit 1
}

list_setupvars() {
    printf "\nThis is what has been configured so far:"
    printf "\nGpigeon root directory: %s" "$ROOT_DIR"
    printf "\nCGI script directory: %s" "$CGI_DIR"
    printf "\nGpigeon ownership: %s:%s" "$SCRIPT_USER" "$SCRIPT_GROUP"
    printf "\nGpigeon links folder: %s" "$LINKS_DIR"
    printf "\nGpigeon GPG homedir: %s" "$GPG_DATA_DIR"
    printf "\nGPG public key id: %s" "$GPG_XLONG"
    printf "\nLocal mailserver method: "   
    if [ $HAS_MAILSERVER -eq 0 ]; then
        printf "${RED}no${STYLE_END}\nMail address: %s\nMail password: %s\nExternal SMTP server and port: %s:%s\n" "$YOUR_EMAIL" "$MAIL_PW" "$SMTP" "$SMTP_P"
    else
        printf "${GREEN}yes${STYLE_END}\n"
    fi
    printf "App password: %s\n" "$APP_PW"
    printf "\n"

    printf "\nPress any key to continue (CTRL+C to abort)..."
    read
}

__check_setupvars() {
    if ! $GPG -k "$GPG_HEX" 2>/dev/null >/dev/null; then
        printf "No GPG key pair are related to your email. Create one and launch
    this script again."
        self_abort
    fi

    if ! id $SCRIPT_USER; then
        printf "\nThe user ${BOLD}$SCRIPT_USER${STYLE_END} doesn't exist. Edit
    ${UNDL}$self_fullpath${STYLE_END} and search
    for the ${BOLD}SCRIPT_USER${STYLE_END} variable.\n\n"
        self_abort
    fi

    if ! getent group $SCRIPT_GROUP; then
        echo "The ${BOLD}$SCRIPT_GROUP${END_STYLE} group doesn't exist. Edit $self_fullpath then modify
    the SCRIPT_GROUP variable value."
        self_abort
    fi

    if [ "$APP_PW" -eq "0" ] || [ -z $APP_PW ] ; then
        echo "Please edit $0 with a text editor ($EDITOR I guess?) and change the
        APP_PW variable."
        self_abort
    else
        PW_LENGTH=$(echo $APP_PW | wc -L)
        if [ $PW_LENGTH -le 8 ]; then
            echo "Your password is too short, make it lengthier than 8 characters."
            self_abort
        fi
    fi

    # prevent obscure errors with q{$APP_PW} in perl script
    APP_PW_SANE="$(echo $APP_PW | sed s/{/\\\\{/g | sed s/}/\\\\}/g)"

    # password checksum'd so no plaintext
    HASHED_PASSWORD=$(printf "%s" "$APP_PW" | sha256sum | cut -d' ' -f1)

    if ! echo "$YOUR_EMAIL" | grep "$emailre" >/dev/null; then
        printf "\nYour email address is not a valid one. Edit $self_fullpath and
        modify the value of the YOUR_EMAIL variable."
    fi
}

setup_gpigeon() {
    apt install perl gcc make cpanminus libnet-ssleay-perl || self_abort
    cpanm Digest::SHA Email::Valid String::Random HTML::Entities CGI CGI::Carp Net::SMTP Net::SMTPS GPG || ( printf "\nInstallation of dependencies failed\n" && self_abort )

    cp $self_dir/gpigeon-template.cgi $SCRIPT
    sed "s/password_hash_goes_here/$HASHED_PASSWORD/g" -i $SCRIPT
    sed "s/your_mail_address_goes_here/$YOUR_EMAIL/g" -i $SCRIPT
    sed "s/your_mail_address_password_goes_here/$YOUR_EMAIL_PW/g" -i $SCRIPT
    sed "s/smtp_domain_goes_here/$SMTP/g" -i $SCRIPT
    sed "s/smtp_port_goes_here/$SMTP_P/g" -i $SCRIPT
    sed "s/gpgid_goes_here/$gpgidlong/g" -i $SCRIPT

    printf "\nCreating static files directory at $ROOT_DIR"
    mkdir -p "$ROOT_DIR" || self_abort
    printf "\nCopying static files to $ROOT_DIR ..."
    cp -r $self_dir/{merci/,index.html,gpigeon.css,favicon.ico} $ROOT_DIR || self_abort

    printf "\n\nCreating script and links directory at $CGI_DIR ..."
    mkdir -p {"$CGI_DIR","$LINKS_DIR"} || self_abort

    printf "\nCopying personalized gpigeon.cgi script to $CGI_DIR ..."
    cp $SCRIPT $CGI_DIR/ || self_abort

    printf "\nSetting ownership as $SCRIPT_USER:$SCRIPT_GROUP for directory $CGI_DIR ..."
    chown $SCRIPT_GROUP:$SCRIPT_USER $CGI_DIR || self_abort

    printf "\nSetting ownership as $SCRIPT_USER:$SCRIPT_GROUP for static directory $ROOT_DIR ..."
    chown $SCRIPT_GROUP:$SCRIPT_USER $ROOT_DIR || self_abort

    printf "\nSetting up the GPG directory for the script ..."
    if [[ -z $GPG_DATA_DIR ]]; then
        mkdir -p /usr/share/www-data/.gnupg
        cp -r ~/.gnupg /usr/share/www-data/
        chown $SCRIPT_USER:$SCRIPT_GROUP /usr/share/www-data/.gnupg
        chmod 600 /usr/share/www-data/.gnupg
    else
        mkdir -p $GPG_DATA_DIR
        cp -r ~/.gnupg /usr/share/www-data/
        chown $SCRIPT_USER:$SCRIPT_GROUP $GPG_DATA_DIR
        chmod 600 $GPG_DATA_DIR
    fi
    printf "${BOLD}${GREEN}Congrats, we are done!${END_STYLE} You should now manually configure your web server to execute the CGI scripts in the $CGI_DIR folder. Manuals and
    official websites for these softwares should help you.\n\n"
    exit 0
}

_usage_(){
    printf "\n  -c    checks variables"
    printf "\n  -l    lists variables"
    printf "\n  -y    checks variables and attempts to install gpigeon"
    printf "\n  -s    install gpigeon"
    printf "\n  -h    print this help"
    printf "\n\n"
}

while getopts "clysh" o; do
   case "${o}" in
       c) __check_setupvars && exit 0;;
       l) list_setupvars && exit 0;;
       y) __check_vars && setup_gpigeon;;
       s) setup_gpigeon;;
       h) _usage_;;
       #i) interactive_setup;;
       *) __check_vars && list_setupvars && setup_gpigeon
   esac
done
