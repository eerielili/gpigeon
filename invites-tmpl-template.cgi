#!/usr/bin/perl -T
my $mail = undef;
use warnings;
use strict;
use DBI;
use CGI qw/param/;
use CGI::Carp qw/fatalsToBrowser/;
use Crypt::Argon2 qw/argon2id_pass/;
use Email::Valid;
use Net::SMTP;
use Net::SMTPS;
use String::Random;
use File::Path qw/make_path rmtree/;
use Mail::GPG;

sub EscapeArobase {
        my $esc = shift;
        if ($esc =~ /^([-\@\w.]+)$/) {
            $esc = $1;                     # $data now untainted
	    $esc =~ s/@/\\@/;
	    return $esc;
        }
}

sub SetMail {
    print "Mail address: ";
    my $addr = <STDIN>;
    if (not Email::Valid->address($addr)){
        die "\nNot a valid email address.";
    }
    chomp $addr;
    return $addr;
}

sub DbGetLine {
    my ($dbh, $query) = @_;
    my $prep = $dbh->prepare( $query );
    my $exec = $prep->execute() or die $DBI::errstr;

    if ($exec < 0){
        print $DBI::errstr;
    }

    while (my @rows = $prep->fetchrow_array()) {
        my $row = $rows[0];
        return $row;
    }
}

sub MakeGPGDir {
	my $homedir = shift;
	make_path($homedir) unless -d $homedir;
	chmod(0700, $homedir);
	if(not -e "$homedir/gpg.conf"){
		open my $out, '>', "$homedir/gpg.conf" or die "[MakeGPGDir function] Can't open $homedir/gpg.conf: $!";
			print $out "use-agent\n";
			print $out "charset utf-8\n";
			print $out "no-escape-from-lines\n";
			print $out "trust-model always\n";
			print $out "personal-digest-preferences SHA512 SHA384 SHA256 SHA224\n";
			print $out "default-preference-list SHA512 SHA384 SHA256 SHA224 AES256 AES192 AES CAST5 BZIP2 ZLIB ZIP Uncompressed";
		close $out;
	}
}

sub GetRFC822Date {
	# https://stackoverflow.com/a/40149475, Daniel VÃritÃ
	use POSIX qw(strftime locale_h);
	my $old_locale = setlocale(LC_TIME, "C");
	my $date = strftime("%a, %d %b %Y %H:%M:%S %z", localtime(time()));
	setlocale(LC_TIME, $old_locale);
	return $date;
}

delete @ENV{qw(IFS PATH CDPATH BASH_ENV)};
$ENV{'PATH'} = q{bin_path_goes_here};

my $HAS_MAILSERVER = q{0};
my $EMAIL_NOTIF    = q{0};
my $cgi            = CGI->new;
if (not defined $mail){
	$mail          = scalar $cgi->param('mailaddr');
}
my $mailfield       = q{mailfield_goes_here};
my $mailsender      = q{sender_addr_goes_here};
my $mailsender_pw   = q{sender_pw_goes_here};
my $mailsender_smtp = q{smtp_domain_goes_here};
my $mailsender_port = q{smtp_port_goes_here};
my $isadmin         = q{is_admin_goes_here};
my $db_path         = q{db_path_goes_here};
my $GNUPGHOME       = q{gpg_homedir_goes_here};
my $TEST_GPGHOME    = q{test_gpgdir_goes_here};
my $dbh             = DBI->connect("DBI:SQLite:dbname=$db_path", undef, undef, { RaiseError => 1})
                or die $DBI::errstr;
chomp $mail;
my $nick    = $cgi->param('username');
chomp $nick;
my $pw      = $cgi->param('pw');
my $pw2     = $cgi->param('pw2');
my $gpgpubk = $cgi->param('gpgpubk');
$gpgpubk    =~ tr/\r//d;
my ($err, $smtp)     = undef;

my $pwmatch = $pw cmp $pw2;

if ($ENV{REQUEST_METHOD} eq 'POST'){
    if (length($gpgpubk) eq 0){
        $err = q{<span id="failure">No public GPG key text found !</span>}; 
    }

    if (not $pwmatch eq 0){
        $err = q{<span id="failure">Passwords don't match</span>};
    }
    
    if (length($pw) eq 0 or length($pw) < 10){
        $err = q{<span id="failure">Password can't be empty or less than 10 characters !</span>};
    }

    if(length($nick) < 0){
        $nick = $mail;	
    }
    else{
	    if(length($nick) > 255){
		    $err = q{<span id="failure">Username is too long (more than 255 characters).</span>};
	    }

	    if(length($nick) > 0 and length($nick) < 255){
		    #we need to check if duplicate username in db
		    if($nick =~ /^([\w\'\s_]+)$/){
		       $nick = $1;
		       my $dbnick = DbGetLine($dbh, qq{SELECT name from pigeons where name="$nick";});
		       chomp $dbnick;
		       my $samenick = $nick cmp $dbnick;
		       if($samenick == 0){
			    $err = q{<span id="failure">Username is already taken.</span>};
		       }
		    }
		    else{
		       $err = q{<span id="failure">Username must be left blank or contains alphanumeric characters, space(s) and single quotes.</span>};
		    }
	    }
    }

    if (not Email::Valid->address($mail)){
        $err = q{<span id="failure">Invalid mail address !</span>};
    }
    else {
        my $dbmail = DbGetLine($dbh, qq{SELECT mail from pigeons where mail='$mail';});
        chomp $dbmail;
        my $samemail = $dbmail cmp $mail;
        if ($samemail == 0){
            $err = q{<span id="failure">Mail is already taken.</span>};
        }
    }

    if (not defined $err){
        my $str_rand_obj = String::Random->new;
        my $val = $str_rand_obj->randregex('\w{64}');
        MakeGPGDir($TEST_GPGHOME);
        my $pubkfile="$TEST_GPGHOME/$val-public.key.asc";
        open my $out, '>', $pubkfile or die "$!";
            print $out $gpgpubk;
        close $out;
        `gpg --homedir $TEST_GPGHOME --import $pubkfile`;
        my $gpgmail = Mail::GPG->new(
            gnupg_hash_init => {homedir=>$TEST_GPGHOME},
            debug => 0,
            no_strict_7bit_encoding =>1,
        );
        my $escaddr = EscapeArobase($mail);
        my $keyid = `gpg --homedir $TEST_GPGHOME --with-colons -k $escaddr | grep "pub:" | cut -d':' -f5`;
        if ($keyid =~ /([\w]+)/ and length($keyid) eq 16){
            $keyid = $1;
        }
        
        if (not defined $keyid){
            $err = q{<span id="failure">Email and the public GPG key text doesn't match.</span>};
        }
        else{ # this is where we can begin to insert data in db
            MakeGPGDir($GNUPGHOME);
            `gpg --homedir $GNUPGHOME --import $pubkfile`,
            my $gpgmail = Mail::GPG->new(
                gnupg_hash_init => {homedir => $GNUPGHOME},
                no_strict_7bit_encoding => 1,
                debug => 0,
            ) or die "$!";

            my $rfc822date = GetRFC822Date();
            my $mimentity = MIME::Entity->build(
                Date => $rfc822date,
                From => $mailsender,
                To   => $mail,
                Charset => 'utf-8',
                Subject => "Your GPIGEON Account registration was successful !",
                Data => ["Hello,\n\tYour GPIGEON account has been successfully created.\n\tHere's your account details:\n\n\t\tUsername: $mail\n\t\tNickname: $nick\n\t\tPassword: $pw\t\nYou can connect through our website, https://$ENV{HOSTNAME}.\n\nThank you,\nGPIGEON Mailer"]);
            my $encrypted_mime_blob = $gpgmail->mime_encrypt(entity => $mimentity, recipients => [$keyid]) or die;
            my $encrypted_mime = $encrypted_mime_blob->as_string; 
            my $salt = `openssl rand 16`;
            my $hash = argon2id_pass($pw, $salt, 3, '32M', 1, 32);
            $dbh->do(qq{INSERT INTO pigeons VALUES( ?, '$mail', '$nick', '$hash', '$keyid', $adminflag)}) or die $DBI::errstr;
            $dbh->disconnect;
                
            if ($EMAIL_NOTIF){	
                use Net::SMTP;
                use Net::SMTPS;
                if ($HAS_MAILSERVER){
                    $smtp = Net::SMTP->new(Host => 'localhost'); 
                }
                else {
                    $smtp = Net::SMTPS->new($mailsender_smtp, Port => $mailsender_port, doSSL => 'ssl', Debug_SSL => 0); 
                    $smtp->auth($mailsender, $mailsender_pw) or die "$!";
                }

                $smtp->mail($mailsender) or die "Net::SMTP module has broke: $!";
                if ($smtp->to($mail)){
                    $smtp->data($encrypted_mime);
                    $smtp->dataend();
                    $smtp->quit();
                }
                else {
                    die $smtp->message();
                }
            }

        }
        rmtree($TEST_GPGHOME, {keep_root=>1, safe=>1});
    }
}

print 'Content-Type: text/html; charset=utf-8',"\n\n",
qq{<!DOCTYPE HTML>
<html>
<head>
    <link rel="icon" sizes="48x48" type="image/ico" href="/favicon.ico">
    <meta charset="utf-8">
    <meta http-equiv="Content-Type" content="text/html;charset=UTF-8">
    <meta name="viewport" content="width=device-width">
    <title>GPIGEON - Registration form</title>
    <link rel="stylesheet" href="/styles.css">
</head>
<body>
    <h1>GPIGEON - Registration form</h1>
    <hr>
    <form method="POST">
        <table id="inviteform">
            <tbody>
                <tr>
                    <td id="labels">Mail adress:</td>
                    <td>$mailfield</td>
                </tr>
                <tr>
                    <td id="labels">(Optional) Username:</td>
                    <td><input placeholder="Choose an username" type="text" name="username"></td>
                </tr>
                <tr>
                    <td id="labels">Password:</td>
                    <td><input placeholder="Type a password" type="password" name="pw" required></td>
                </tr>
                <tr>
                    <td id="labels">Password (confirmation):</td>
                    <td><input placeholder="Type again your password" type="password" name="pw2" required></td>
                </tr>

                <br>

                <tr>
                    <td id="gpgpklabel">GPG public key:</td>
                    <td><textarea placeholder="Paste here the result of the command:\ngpg -a --export your\@mailaddre.ss" id="gpgpubk" wrap="off" name="gpgpubk" required></textarea></td>
                </tr>
                <tr>
                    <td></td>
                    <td id="loginerr">$err</td>
                <tr id="createaccbtn">
                    <td></td>
                    <td><input id="accbtn" type="submit" value="Create account"></td>
                </tr>
            </tbody>
        </table>
        <hr>
    </form>
</body>
</html>};
