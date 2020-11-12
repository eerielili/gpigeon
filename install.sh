# !/bin/sh
THIS_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
emailre=".\+@.\+\\..\+"
GPIGEON_SCRIPT=$THIS_SCRIPT_DIR/cgi-bin/gpigeon.cgi
GPG_DATA_DIR='/usr/share/www-data'
SCRIPT_USER='www-data'
SCRIPT_GROUP=$SCRIPT_USER
GPIGEON_ROOT_DIR='/var/www/gpigeon'


command -V gpg >/dev/null 2>&1 && GPG="gpg" || GPG="gpg2"
printf "Welcome to the gpigeon.cgi installer. We will first install the
dependencies.\n"

#apt install perl gcc make cpanminus libnet-ssleay-perl || exit 1
#cpanm Digest::SHA Email::Valid String::Random HTML::Entities CGI CGI::Carp Net::SMTP Net::SMTPS GPG || ( printf "\nInstallation of dependencies failed\n" && exit 1 )




interact() {

    if [ $INSTALLING eq 1 ]; then
        echo "already installing !"
        exit 1
    fi

    printf "Choose a password for the gpigeon web application: \n"
    read -r -s _APP_PASSWORD

    while [[ $_APP_PASSWORD_VERIFICATION != $_APP_PASSWORD ]]; do
        printf "\nRepeat password: "
        read -r -s _APP_PASSWORD_VERIFICATION
    done

    # prevent obscure errors with q{} from perl
    _APP_PASSWORD="$(echo $_APP_PASSWORD | sed s/{/\\\\{/g | sed s/}/\\\\}/g)"
    HASHED_PASSWORD=`perl -e "use Digest::SHA qw(sha256_hex);print sha256_hex(q{$_APP_PASSWORD});"`
    printf "\nPassword matches. The SHA256 hash of it is: \033[32m$HASHED_PASSWORD\033[0m\n"

    printf "\nWhat is your email address: "
    read -r _YOUR_EMAIL
    while ! echo "$_YOUR_EMAIL" | grep "$emailre" >/dev/null; do
        printf "\nYour email address is not a valid one. Type it again: "
        read -r _YOUR_EMAIL
    done
    printf "\033[32m$_YOUR_EMAIL\033[0m seems a valid e-mail address."

    while [[ -z $_YOUR_EMAIL_PASSWORD ]]; do
        printf "\nPassword for your email account: "
        read -r -s _YOUR_EMAIL_PASSWORD
    done

    while [[ $_YOUR_EMAIL_PASSWORD_VERIFICATION != $_YOUR_EMAIL_PASSWORD ]]; do
        printf "\nAgain for confirmation: "
        read -r -s _YOUR_EMAIL_PASSWORD_VERIFICATION
    done

    _YOUR_EMAIL_PASSWORD_VERIFICATION=$(printf '%s\n' "$_YOUR_EMAIL_PASSWORD" | sed -e 's/[]\/$*.^[]/\\&/g');


    domain="$(echo "$_YOUR_EMAIL" | sed "s/.*@//")"
    serverinfo="$(grep "^$domain" "domains.csv" 2>/dev/null)"
    if [ -z "$serverinfo" ]; then
        printf "\nAh. Your email domain isn't listed in the domains.csv file. Don't
        worry, you can find info relating to that easily on the domain website /
        the Internet, and type it in here."
        while ! echo "$smtp" | grep -Eo "[.[:alnum:]]"; do
            printf "\nWhat is the SMTP server address of your domain (typically like this: smtp.domain.net)? "
            read -r smtp
        done

        while ! echo "$sport" | grep -Eo "[0-9]{1,5}"; do
            printf "\nWhat is the SMTP server port (typically 465 or 587) ? "
            read -r sport
        done
    else
        print "Yay! Your email domain seems to be listed in domains.csv, so you don't
        have to manually type the smtp server address and port manually."
        IFS=, read service imap iport smtp sport <<EOF
        $serverinfo
EOF
        # smtp and sport variable are the only useful variable for our use case
    fi
    gpgidlong="$($GPG -k --with-colons $_YOUR_EMAIL| awk -F: '/^pub:/ {print $5}')"

    if [ -z gpgid ]; then
        printf "No GPG key pair are related to your email. Create one and launch
this script again."
        exit 0
    else
        printf "\nGPG keyid associated to $_YOUR_EMAIL : \033[32m0x$gpgidlong\033[0m."
    fi

    while ! echo "$SCRIPT_DIR" | grep -Eo "^/"; do
        printf "\nWhich directory you want the script to be in (defaults to
        /var/www/cgi-bin/) ? Please provide an absolute path: "
        read -r SCRIPT_DIR
    done

    printf "\nWhat user and group you want to use for the gpigeon CGI script
    (defaults to www-data for both):"
    printf "\nUser: "
    read -r SCRIPT_USER
    printf "\nGroup (leave blank for same as user): "
    read -r SCRIPT_GROUP

    if [ -z SCRIPT_USER ]; then
        SCRIPT_USER='www-data'
    else
        while ! id $SCRIPT_USER; do
            printf "\nThe user you typed doesn't seem to exist. Try again with a valid one: "
            read -r SCRIPT_USER
        done
    fi

    if [ -z SCRIPT_GROUP ]; then
        SCRIPT_GROUP=$SCRIPT_USER
    fi

    printf "\nWhere will be put the static files ? Defaults to /var/www/gpigeon."
    read -r GPIGEON_ROOT_DIR
}

setup_gpigeon() {
    cp $THIS_SCRIPT_DIR/gpigeon-template.cgi $GPIGEON_SCRIPT
    sed "s/password_hash_goes_here/$HASHED_PASSWORD/g" -i $GPIGEON_SCRIPT
    sed "s/your_mail_address_goes_here/$_YOUR_EMAIL/g" -i $GPIGEON_SCRIPT
    sed "s/your_mail_address_password_goes_here/$_YOUR_EMAIL_PASSWORD_VERIFICATION/g" -i $GPIGEON_SCRIPT
    sed "s/smtp_domain_goes_here/$smtp/g" -i $GPIGEON_SCRIPT
    sed "s/smtp_port_goes_here/$sport/g" -i $GPIGEON_SCRIPT
    sed "s/gpgid_goes_here/$gpgidlong/g" -i $GPIGEON_SCRIPT

    printf "\n\nCreating script directory at $SCRIPT_DIR ..."
    mkdir -p "$SCRIPT_DIR/l" || exit 1

    printf "\nCreating static files directory at $GPIGEON_ROOT_DIR"
    mkdir -p "$GPIGEON_ROOT_DIR" || exit 1

    printf "\nCopying personalized gpigeon.cgi script to $SCRIPT_DIR ..."
    cp $GPIGEON_SCRIPT $SCRIPT_DIR/ || exit 1

    printf "\nCopying static files to $GPIGEON_ROOT_DIR ..."

    cp $THIS_SCRIPT_DIR/{merci/,index.html,gpigeon.css,favicon.ico} $GPIGEON_ROOT_DIR || exit 1

    printf "\nSetting ownership as $SCRIPT_USER:$SCRIPT_GROUP for directory $SCRIPT_DIR ..."
    chown $SCRIPT_GROUP:$SCRIPT_USER $SCRIPT_DIR || exit 1

    printf "\nSetting ownership as $SCRIPT_USER:$SCRIPT_GROUP for static directory $GPIGEON_ROOT_DIR ..."
    chown $SCRIPT_GROUP:$SCRIPT_USER $GPIGEON_ROOT_DIR || exit 1

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
    printf "\n\033[32mCongrats, we are done! You should now configure your web server in
    order to execute the CGI scripts in the $SCRIPT_DIR folder. Manuals and
    official websites for these softwares should help you.\033[0m\n\n"
}

while getopts "iu:g:PAm" o; do
    case "${o}" in
        i)
            interact
            INSTALLING=1
            setup_gpigeon;;
        u)
            SCRIPT_USER="$OPTARG"
            echo user will be $SCRIPT_USER;;
            #exit 0
        g)
            SCRIPT_GROUP="$OPTARG"
            echo group will be $SCRIPT_GROUP;;

        P)
            echo kek;;
        A)
            echo kuk;;
        *)
            printf "\nlol fuck off\n";;
#            echo "$@"
#            echo $GETOPTS
    esac
    shift
done
