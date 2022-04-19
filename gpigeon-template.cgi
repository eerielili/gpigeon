#! /usr/bin/perl -T
# gpigeon.cgi: generate links for someone to send you GPG encrypted messages via a one time form.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Copyright (c) 2020-2022, Miquel Lionel <lionel@les-miquelots.net>

use warnings;
use strict;
use Email::Valid;
use String::Random;
use DBI;
use CGI qw(param);
use CGI::Cookie;
use CGI::Carp qw(fatalsToBrowser);
use Crypt::Argon2 qw(argon2id_verify);
use File::Path qw(mkpath rmtree);
use File::stat;

delete @ENV{qw(IFS PATH CDPATH BASH_ENV)};
$ENV{'PATH'} = q{/usr/bin};
my $hostname = $ENV{'SERVER_NAME'};	
my $remoteIP = $ENV{REMOTE_ADDR};
my $userAgent  = $ENV{HTTP_USER_AGENT};
my %textStrings = (
    addr                          => 'Address', 
    addr_ok                       => 'is valid!', 
    addr_nok                      => 'is not valid !',
    addr_unknown                  => 'Unknown',
    create_link_btn               => 'Create link',
    create_invite_btn             => 'Create invite',
    cookie_problems               => 'You got a cookie problem.<br> <b>Clean them and log in again</b>',
    checkbox_admin_user           => 'User will be an admin',
    checkbox_notiflinkbymail      => 'Notify the user by mail about the link',
    checkbox_invite_mailnotif     => 'Send login details via an encrypted mail once the form is completed',
    checkbox_mailinvite           => 'Send mail about the invite',
    optmail                       => '(Optional) Mail :',
    delete_link_btn_text          => 'Delete',
    delete_links_btn_text         => 'Delete all links',
    delete_invites_btn_text       => 'Delete all invites',
    disconnect_btn_text           => 'Disconnect',
    logout_btn_text               => 'Logout',
    here                          => 'here',
    landingpage_title             => 'GPIGEON - Log in',
    loginbtn                      => 'Log in',
    linkAsker_field_label         => "Asker's mail :",
    link_del_ok                   => 'Successful removal !',
    link_legend_textarea          => 'Type your message below :',
    link_ok_for                   => 'Generated a link for',
    link_del_failed               => 'Deletion failed and here is why : ',
    link_generated_ok             => "Success! Here's the link",
    mailto_body                   => 'Your link is ',
    mailto_subject                => 'Link to your one time GPG messaging form',
    incorrect_ids                 => 'Username/password combination<br> is incorrect.<br>Try again.',
    password_label                => 'Password :',
    refresh_btn                   => 'Refresh',
    theader_link                  => 'Link', 
    theader_for                   => 'For', 
    theader_deletion              => 'Deletion',
    theader_creationdate          => 'Created on',
    username_label                => 'Username :',
    web_title                     => 'GPIGEON - Main', 
    web_greet_msg                 => 'Hi and welcome. What will you do today ?', 
);

sub GetFileTable {
    my ($dir ,$hiddenLoginField, $adminPanelField) = @_;
    my @table = ();
    opendir my $linkDirHandle, "$dir" or die "Can't open $dir: $!";
    while (readdir $linkDirHandle) {
        if ($_ ne '.' and $_ ne '..'){
            my $pendingDeletion = $_;
	    my $linkFileStats= stat("$dir/$pendingDeletion"); 
	    my $time = scalar localtime $linkFileStats->mtime;
            my $linkAsker = undef;
            if (open my $linkFileHandle , '<', "$dir/$pendingDeletion"){
                for (1..2){
                    $linkAsker = readline $linkFileHandle;
                    $linkAsker =~ s/q\{(.*?)\}//i;
                    $linkAsker = $1;
                }
                close $linkFileHandle;
		my $forFieldBody = qq{<a href="mailto:$linkAsker?subject=$textStrings{mailto_subject}&body=$textStrings{mailto_body} http://$ENV{SERVER_NAME}/cgi-bin/$dir/$pendingDeletion">$linkAsker</a>};
                
		if (not defined $linkAsker){
		    $forFieldBody = $textStrings{addr_unknown};

                }
                #create links table html
                push @table,
                qq{<tr>
                    <td><a title="This link has been created on $time" href="/cgi-bin/$dir/$pendingDeletion" target="_blank" rel="noopener noreferrer nofollow">ici</a></td>
                    <td>$forFieldBody</td>
                    <td>
                        <form method="POST">
                    	    $hiddenLoginField
                            $adminPanelField
			    <input type="hidden" name="supprlien" value="$dir/$pendingDeletion">
                            <input id="deletelinkbtn" type="submit" value="$textStrings{delete_link_btn_text}">
                        </form>
                    </td>
                </tr>};

            }
            else {
                close $linkFileHandle;
                die 'Content-type: text/plain', "\n\n", "Error: Can't open $pendingDeletion: $!";
            }
        }
    }
    closedir $linkDirHandle;
    return @table;
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

sub LoginOk {
    my ($dbh, $username, $pass, $userID, $magicCookie, $UIDCookie, $cookiesDir) = @_;
    my $loginsuccess = PasswdLogin($dbh, $username, $pass);
    if (not defined $loginsuccess){
        $loginsuccess = CookieLogin($userID, $magicCookie, $UIDCookie, $cookiesDir);
    }
    return $loginsuccess;
}

sub ListUsers {
	my ($dbh) = shift;
	my @usersTable = ();
	my $prep = $dbh->prepare(q{SELECT name,mail from pigeons;} );
	my $exec = $prep->execute() or die $DBI::errstr;

	if ($exec < 0){
		print $DBI::errstr;
	}

	while (my @rows = $prep->fetchrow_array()) {
		#print "$rows[0]\t$rows[1]\n";
		push @usersTable,
		qq{<tr>
			<td>$rows[0]</td>
			<td>$rows[1]</td>
		</tr>};
	}
	return @usersTable;
}

sub CookieLogin {
    my ($userID, $magicCookie, $UIDCookie, $cookiesDir) = @_;
    if (not $userID =~ /^([0-9]+)$/){
        return;
    }

    if (not defined $magicCookie or not defined $UIDCookie){
        return;
    }

    my ($remoteIPLine, $UserAgentLine, $IDLine, $UIDLine) = undef;
    my $filename = $magicCookie->value;
    if ($filename =~ /^([\w]+)$/){
        $filename = $1;
    }
    else{
        return;
    }

    my $loginCookieFile = "$cookiesDir/$userID/$filename.txt";
    if (-e $loginCookieFile){
        open my $in, '<', $loginCookieFile or die "can't read file: $!";
        $remoteIPLine = readline $in;
        $UserAgentLine = readline $in;
        $IDLine = readline $in;
        $UIDLine = readline $in;
        close $in;
        chomp ($remoteIPLine, $UserAgentLine, $IDLine); # chomp the \n
    }
    else{
        return;
    }

    my %IDLineCookie = CGI::Cookie->parse($IDLine);
    my %UIDLineCookie = CGI::Cookie->parse($UIDLine);
    my $IDValue = $IDLineCookie{'id'}->value;
    my $UIDValue = $UIDLineCookie{'uid'}->value;

    my $IPMatch = $remoteIPLine cmp $remoteIP;
    my $UserAgentMatch = $UserAgentLine cmp $userAgent;
    my $UIDMatch = $UIDCookie->value cmp $UIDValue;
    my $IDMatch = $magicCookie->value cmp $IDValue;

    if ($IPMatch == 0 and $UserAgentMatch == 0 and $UIDMatch == 0 and $IDMatch == 0){
        return $userID;
    }
    return;
} 

sub PasswdLogin {
	
    my ($dbh, $username, $pass) = @_;
	if (not defined $username or not defined $pass){
	       return;
       }	       
	if (not Email::Valid->address($username)){
		if ($username =~ /^([-\w.]+)$/) {
			$username = $1;
		} else {
			return;
		}
	} 
	my ($hash, $userID) = undef;	
	my $selectHash = qq{SELECT pass from pigeons where mail='$username' or name='$username';};
	$hash = DbGetLine($dbh, $selectHash);
	if (defined $hash and length($hash) > 1){
		if(argon2id_verify($hash,$pass)){
			my $selectuserID = qq{SELECT userID from pigeons where pass='$hash';};
			$userID = DbGetLine($dbh, $selectuserID);
			if ($userID =~ /^([0-9]+)$/){
				$userID = $1;
			}
			else {
				return;
			}
			return $userID; # as an userID is always > 0, we can use it as return value
		} else {
			return;
		}
	} else {
		$dbh->disconnect;
		return;
	}
	$dbh->disconnect;
	return;
}

sub LoginCookieGen {
    my ($userID, $magicCookie, $cookiesDir) = @_;
    if (not defined $magicCookie){
        my $StrRandObj = String::Random->new;
        my $val = $StrRandObj->randregex('\w{64}');
        if (not -d "$cookiesDir/$userID"){
            mkpath("$cookiesDir/$userID");
        }
        my $cookieFile = "$cookiesDir/$userID/$val.txt";
        my $magicMagicCookie = CGI::Cookie->new(
            -name       => 'id',
            -value      => $val, 
            -expires    => '+1y',
            '-max-age'  => '+1y',
            -domain     => ".$ENV{'SERVER_NAME'}",
            -path       => '/',
            -secure     => 1,
            -httponly   => 1,
            -samesite   => 'Strict',
        ) or die "Can't create cookie $!";
        my $newUserIDCookie = CGI::Cookie->new(
            -name       => 'uid',
            -value      => $userID, 
            -expires    => '+1y',
            '-max-age'  => '+1y',
            -domain     => ".$ENV{'SERVER_NAME'}",
            -path       => '/',
            -secure     => 1,
            -httponly   => 1,
            -samesite   => 'Strict',
       ) or die "Can't create cookie $!";
       open my $out, '>', $cookieFile or die "Can't write to $cookieFile: $!";
           print $out "$remoteIP\n$userAgent\n$magicMagicCookie\n$newUserIDCookie";
       close $out;
       print "Set-Cookie: $magicMagicCookie\n";
       print "Set-Cookie: $newUserIDCookie\n";
    }
}

sub UntaintCGIFilename {
    my $filename = shift;
    if ($filename =~ /^([-\@\w.\/]+)$/) {
        $filename = $1;
    }
    else {
        die "$!";
    }
    chomp $filename;
    return $filename;
}

sub GetRFC822Date {
	# https://stackoverflow.com/a/40149475, Daniel VÃritÃ
	use POSIX qw(strftime locale_h);
	my $oldLocale = setlocale(LC_TIME, "C");
	my $date = strftime("%a, %d %b %Y %H:%M:%S %z", localtime(time()));
	setlocale(LC_TIME, $oldLocale);
	return $date;
}

sub SendGpigeonMail {
	my ($recipient, $title, $message) = @_;
	use Net::SMTP;
	use Net::SMTPS;
	use MIME::Entity;
	my $rfc822date = GetRFC822Date() or die;
	my $HasMailserver = 0;
    my $mailsender = q{sender_addr_goes_here};
    my $mailSenderSMTP = q{smtp_domain_goes_here};
    my $mailSenderPort = q{smtp_port_goes_here};
    my $mailSenderPassword = q{sender_pw_goes_here};
	my $smtp     = undef;
	if ($HasMailserver){
		$smtp = Net::SMTP->new(Host => 'localhost') or die; 
	}
	else {
		$smtp = Net::SMTPS->new($mailSenderSMTP, Port => $mailSenderPort, doSSL => 'ssl', Debug_SSL => 0); 
		$smtp->auth($mailsender, $mailSenderPassword) or die;
	}
	my $notifyLinkByMailData = MIME::Entity->build(
		Date => $rfc822date,
		From => $mailsender,
		To   => $recipient,
		Charset => 'utf-8',
		Subject => $title,
		Data => [$message]) or die;
	$smtp->mail($mailsender) or die "Net::SMTP module has broke: $!.";
	if ($smtp->to($recipient)){
	    $smtp->data($notifyLinkByMailData->stringify);
	    $smtp->dataend();
	    $smtp->quit();
	}
	else {
	    die $smtp->message();
	}
}


my $dbPath                             = q{dbPath_goes_here};
my $cookiesDir                          = q{cookiesDir_goes_here};
my $linkTemplatePath                  = q{linkTemplatePath_goes_here};
my $invitesTemplatePath               = q{invite_template_goes_here};

my $cgiQueryGet                       = CGI->new;
my $username                            = $cgiQueryGet->param('username');
my $pass                                = $cgiQueryGet->param('password');
my $disconnect                          = $cgiQueryGet->param('disconnect');
my $adminpanselect                      = $cgiQueryGet->param('adminpan');
my ( $checkedOrNot, $hiddenLoginField, $magicCookie, 
    $UIDCookie, $ID, $refreshForm, 
    $userID)                            = undef;
my $linkGenNotif                       = my $sentMailNotif = my $mailIsOkNotif = my $deletionNotif = my $loginNotif = my $adminPanelField = my $adminbtn = '<!-- undef notif -->';
my @createdLinks                       = ();
my %currentCookies                         = CGI::Cookie->fetch;
$UIDCookie                             = $currentCookies{'uid'};
$magicCookie                           = $currentCookies{'id'};
my $dbh                                 = DBI->connect("DBI:SQLite:dbname=$dbPath", undef, undef, { RaiseError => 1})
                                            or die $DBI::errstr;

if ($adminpanselect){
	$adminPanelField = q{<input type="hidden" name="adminpan" value="1">};
}


if (not defined $magicCookie){ # cookie is not set
    $hiddenLoginField = qq{<input type="hidden" name="username" value="$username"><input type="hidden" name="password" value="$pass">};

    $refreshForm = qq{<form method="POST">
                           $hiddenLoginField
                           $adminPanelField
                           <input id="refreshbtn" type="submit" value="$textStrings{refresh_btn}">
                       </form>};
}
else{
    $hiddenLoginField = qq{<!-- undef -->};
    $refreshForm = qq{<form method="GET">
                           $adminPanelField
                           <input id="refreshbtn" type="submit" value="$textStrings{refresh_btn}">
                       </form>};
   $ID = $magicCookie->value;
   if ($ID =~ /^([\w]+)$/){
	   $ID = $1;
   }

   $userID = $UIDCookie->value;
   if ($userID =~ /^([0-9]+)$/){
	   $userID = $1;
   }

}

if ($disconnect and defined $magicCookie){ # if we disconnect and cookie is active
    my $deleteIDCookie = CGI::Cookie->new(
        -name  => 'id',
        -value => $ID, 
        -expires => '-1d',
        '-max-age' => '-1d',
        -domain => ".$hostname",
        -path      => '/',
        -secure   => 1,
        -httponly => 1,
        -samesite => 'Strict',
    );
    my $deleteUIDCookie = CGI::Cookie->new(
        -name  => 'uid',
        -value => $userID, 
        -expires => '-1d',
        '-max-age' => '-1d',
        -domain => ".$hostname",
        -path      => '/',
        -secure   => 1,
        -httponly => 1,
        -samesite => 'Strict',
    );
    my $f = "$cookiesDir/$userID/$ID.txt";
    if (-e "$f"){
        unlink "$f" or die "cant delete cookie at $f :$!\n"; # delet it
    }       
    print "Set-Cookie: $deleteUIDCookie\n";
    print "Set-Cookie: $deleteIDCookie\n";
}



my $loginOK = LoginOk($dbh, $username, $pass, $userID, $magicCookie, $UIDCookie, $cookiesDir);
print "Cache-Control: no-store, must-revalidate\n";
if($loginOK){

    $userID           = $loginOK; 
    my $userMailAddr = DbGetLine($dbh, qq{SELECT mail from pigeons where userID='$userID';});
    my $nick          = DbGetLine($dbh, qq{SELECT name from pigeons where userID='$userID';});
    my $isAdmin       = DbGetLine($dbh, qq{SELECT isadmin from pigeons where userID='$userID';});
    LoginCookieGen($userID, $magicCookie, $cookiesDir);

    if ($isAdmin){
        $adminbtn = qq{<form method="POST">
                           $hiddenLoginField
                           <input type="hidden" name="adminpan" value="1">
                           <input id="adminpanbtn" type="submit" value="Admin panel">
                       </form>};
        if (not -d "i/$userID"){
            mkpath("./i/$userID");
        }
    }

    if (not -d "./l/$userID"){
        mkpath("./l/$userID");
    }

    if (defined $cgiQueryGet->param('supprlien')){
        my $pendingDeletion = $cgiQueryGet->param('supprlien');
        #make sure smart and malicious users don't go deleting other things
        if ($pendingDeletion =~ /^l\/$userID\/([\w]+)\.cgi$/ or $pendingDeletion =~ /^i\/$userID\/([\w]+)\.cgi$/) {
            if (unlink UntaintCGIFilename($pendingDeletion)){ 
                $deletionNotif=qq{<span id="success">$textStrings{link_del_ok}</span>};
            }
            else {
                $deletionNotif=qq{<span id="failure">$textStrings{link_del_failed} $pendingDeletion: $!</span>};
            }
        }
    }

    if (defined $cgiQueryGet->param('supprtout')){
        rmtree("./l/$userID", {keep_root=>1, safe=>1});
        $deletionNotif=qq{<span id="success">$textStrings{link_del_ok}</span>};
    }
    
    if (defined $cgiQueryGet->param('delallinvites')){
        rmtree("./i/$userID", {keep_root=>1, safe=>1});
        $deletionNotif=qq{<span id="success">$textStrings{link_del_ok}</span>};
    }

    if (defined $cgiQueryGet->param('geninv')){
        my $inviteAsker = scalar $cgiQueryGet->param('opt-mail');
        $mailIsOkNotif = qq{<span id="failure">$textStrings{addr} $inviteAsker $textStrings{addr_nok}</span>};
        my $StrRandObj = String::Random->new;
        my $randomFilename = $StrRandObj->randregex('\w{64}');
        my $generatedFormFilename = "$randomFilename.cgi";
        my $hrefLink   	 = "https://$hostname/cgi-bin/i/$userID/$generatedFormFilename";
        my $invitesPath 	 =  "./i/$userID/$generatedFormFilename";

        open my $in, '<', $invitesTemplatePath or die "Can't read link template file: $!";
        open my $out, '>', $invitesPath or die "Can't write to link file: $!";
        while( <$in> ) {
            if ( Email::Valid->address($inviteAsker) ){
                $mailIsOkNotif = qq{<span id="success">$textStrings{addr} $inviteAsker $textStrings{addr_ok}</span>};
                s/mail = undef;/mail = q{$inviteAsker};/g;
                s/{mailfield_goes_here}/{<input type="text" name="mailaddr" value="$inviteAsker" disabled>}/g;
            }

            s/{mailfield_goes_here}/{<input type="text" name="mailaddr" placeholder="Your mail address used for GPG" required>}/g;
            if (defined $cgiQueryGet->param('mailnotif') ){
                s/EMAIL_NOTIF = .*/EMAIL_NOTIF = q{1};/g	
            }

            if (defined $cgiQueryGet->param('adminprom') ){
                s/is_admin_goes_here/1/g	
            }
            else{
                s/is_admin_goes_here/0/g	
            }
            s/{userMailAddr_goes_here}/{$userMailAddr}/g;
            print $out $_;
        }

        close $in or die;
        chmod(0755,$invitesPath) or die;
        close $out or die;

        $linkGenNotif = qq{<span id="success">$textStrings{link_generated_ok}: <br><a target="_blank" rel="noopener noreferrer nofollow" href="$hrefLink">$hrefLink</a></span>};          
        if (defined $cgiQueryGet->param('invitemail') and Email::Valid->address($inviteAsker)){
            SendGpigeonMail($inviteAsker,"[GPIGEON](Do not reply) You have been invited to $hostname","Greetings,\n\n\tYou have been invited to create an GPIGEON account on $hostname.\n\tClick on the link below to fill in the form:\n\t$hrefLink\n\tIf you believe this mail is not meant for you, ignore it and mail the webmaster or admin\@les-miquelots.net about it.\n\nKind regards,\nGpigeon mailing system at $hostname.") or $sentMailNotif = "$!";
        }
    }
    
    if (defined $cgiQueryGet->param('mail')){
        my $linkAsker = scalar $cgiQueryGet->param('mail');

        if ( Email::Valid->address($linkAsker) ){
            $mailIsOkNotif = qq{<span id="success">$textStrings{addr} $linkAsker $textStrings{addr_ok}</span>};
            my $StrRandObj = String::Random->new;
            my $randomFilename = $StrRandObj->randregex('\w{64}');
            my $generatedFormFilename = "$randomFilename.cgi";
            my $hrefLink   	 = "https://$hostname/cgi-bin/l/$userID/$generatedFormFilename";
            my $linkPath 	 =  "./l/$userID/$generatedFormFilename";

            open my $in, '<', $linkTemplatePath or die "Can't read link template file: $!";
            open my $out, '>', $linkPath or die "Can't write to link file: $!";
            while( <$in> ) {
                s/{link_user}/{$linkAsker}/g;
                s/{userMailAddr_goes_here}/{$userMailAddr}/g;
                print $out $_;
            }
            close $in or die;
            chmod(0755,$linkPath) or die;
            close $out or die;

            $linkGenNotif = qq{<span id="success">$textStrings{link_generated_ok}: <br><a target="_blank" rel="noopener noreferrer nofollow" href="$hrefLink">$hrefLink</a></span>};          
            if (defined $cgiQueryGet->param('notiflinkbymail')){
                SendGpigeonMail($linkAsker,"[GPIGEON](Do not reply) Your encrypted form is ready","Greetings,\n\n\tAn encrypted form has been generated for you on $hostname.\n\tClick on the link below to fill in the form:\n\t$hrefLink\n\tIf you believe this mail is not meant for you, ignore it and mail the webmaster or admin\@les-miquelots.net about it.\n\nKind regards,\nGpigeon mailing system at $hostname.") or $sentMailNotif="$!" ;
            }
        }
        else{
            $mailIsOkNotif = qq{<span id="failure">$textStrings{addr} $linkAsker $textStrings{addr_nok}</span>};
        }
    }
    
    my @linksTable = GetFileTable("l/$userID", $hiddenLoginField, $adminPanelField); 

    print 'Content-type: text/html',"\n\n";
    if ($adminpanselect and $isAdmin){
        my @invitesTable = GetFileTable("i/$userID", $hiddenLoginField, $adminPanelField);


        print qq{<!DOCTYPE html>
            <html> 
                <head> 
                    <meta name="viewport" content="width=device-width">
                    <link rel="icon" sizes="48x48" type="image/ico" href="/favicon.ico">
                    <link rel="stylesheet" type="text/css" href="/styles.css">
                    <meta http-equiv="content-type" content="text/html;charset=UTF-8">
                    <meta charset="UTF-8">
                    <title>$textStrings{web_title}</title>
                </head>
                <body>
                    <h1>GPIGEON - Admin panel</h1>
                    <p>Welcome to the admin panel. Here, you can view and generate account invites and also search and delete users.</p>
                    <form method="GET">
                        $hiddenLoginField
                        <input id="adminpanbtn" type="submit" value="Main panel">
                    </form>
                    <form method="GET">
                        <input type="hidden" name="disconnect" value="1">
                        <input id="logoutbtn" type="submit" value="$textStrings{disconnect_btn_text}">
                    </form>
                    $refreshForm
                <hr>
                <form method="POST">
                    $hiddenLoginField
                    $adminPanelField
                    <label for="opt-mail">
                        $textStrings{optmail}
                        <input tabindex="1" id="mailfield" type="text" name="opt-mail">
                    </label>
                    <input name="geninv" type="submit" id="geninvbtn" value="$textStrings{create_invite_btn}">
                    <label id="mailnotif" for="mailnotif">
                        $textStrings{checkbox_invite_mailnotif}
                        <input id="mailnotif-check" type="checkbox" name="mailnotif" value="1">
                    </label>

                    <label id="invitemail" for="invitemail">
                        <input id="invitemail-check" type="checkbox" name="invitemail" value="1">$textStrings{checkbox_mailinvite}
                    </label>

                    <label id="adminprom" for="adminprom">
                        $textStrings{checkbox_admin_user}
                        <input id="adminprom-check" type="checkbox" name="adminprom" value="1">
                    </label>

                    <input name="geninv" type="submit" id="geninvbtn-mob" value="$textStrings{create_invite_btn}"><br>
                $mailIsOkNotif
                <br>
                $linkGenNotif
                <br>
                $sentMailNotif
                </form>
                <hr>
                        <form method="POST">
                            $hiddenLoginField
                $adminPanelField
                            <input id="deleteallbtn" type="submit" name="delallinvites" value="$textStrings{delete_invites_btn_text}">
                        </form>
                        $deletionNotif
                        <table id="linkstable">
                            <tr>
                                <th>&#x1f517; $textStrings{theader_link}</th>
                                <th>&#x1f4e7; $textStrings{theader_for} </th>
                                <th>&#10060; $textStrings{theader_deletion}</th>
                            </tr>
                            <tbody>
                            @invitesTable
                            </tbody>
                        </table>
            </body>
            </html>
        };
    }
    else {
        print qq{<!DOCTYPE html>
            <html> 
                <head> 
                    <meta name="viewport" content="width=device-width">
                    <link rel="icon" sizes="48x48" type="image/ico" href="/favicon.ico">
                    <link rel="stylesheet" type="text/css" href="/styles.css">
                    <meta http-equiv="content-type" content="text/html;charset=UTF-8">
                    <meta charset="UTF-8">
                    <title>$textStrings{web_title}</title>
                </head>
                <body>
                <h1>$textStrings{web_title}</h1>
                    <p>$textStrings{web_greet_msg}</p>
            $adminbtn
                    <form method="GET">
                        <input type="hidden" name="disconnect" value="1">
                        <input id="logoutbtn" type="submit" value="$textStrings{disconnect_btn_text}">
                    </form>
            $refreshForm
                    <hr>
                    <br>
                    <form method="POST">
                        $hiddenLoginField
                        Mail:<br>
                        <input id="mailfield" tabindex="1" placeholder="Link user mail address" type="text" name="mail">
                        <input id="genlinkbtn" tabindex="2" type="submit" value="$textStrings{create_link_btn}">
                        <label id="notiflinkbymail" for="notiflinkbymail">
                        $textStrings{checkbox_notiflinkbymail}
                            <input id="notiflinkbymail-check" type="checkbox" name="notiflinkbymail" value="1">
                        </label>
                    </form>
                    $mailIsOkNotif
                    <br>
                    $linkGenNotif
                    <br>
                    $sentMailNotif
                    <hr>
                    <form method="POST">
                        $hiddenLoginField
                        <input id="deleteallbtn" name="supprtout" type="submit" value="$textStrings{delete_links_btn_text}">
                    </form>
                    $deletionNotif
                    <table id="linkstable">
                        <tr>
                            <th>&#x1f517; $textStrings{theader_link}</th>
                            <th>&#x1f4e7; $textStrings{theader_for} </th>
                            <th>&#10060; $textStrings{theader_deletion}</th>
                        </tr>
                        <tbody>
                            @linksTable
                        </tbody>
                    </table>
                </body>
            </html>};
	}
}
else{
    $dbh->disconnect;
    if (not $disconnect and defined $magicCookie){
        $loginNotif = qq{<span id="failure">$textStrings{cookie_problems}</span>};
    }
    if (length($pass) > 0 or length($username) > 0){
        $loginNotif = qq{<span id="failure">$textStrings{incorrect_ids}</span>};
    }
    
    print "Content-type: text/html\n\n",
qq{<!DOCTYPE html>
   <html lang="fr">
       <head>
           <meta name="viewport" content="width=device-width">
           <meta charset="utf-8">
           <link rel="icon" type="image/x-icon" href="/favicon.ico">
           <link rel="stylesheet" type="text/css" href="/styles.css">
           <title>$textStrings{landingpage_title}</title>
       </head>
       <body>
           <h1>$textStrings{landingpage_title}</h1>
           <form action="/cgi-bin/gpigeon.cgi" method="POST">
               <table id="loginbox">
                   <tbody>
                       <tr>
                           <td id="labels">$textStrings{username_label}</td>
                           <td><input size="30" type="text" name="username" autofocus tabindex=1></td>
                       </tr>
                       <tr>
                           <td id="labels">$textStrings{password_label}</td>
                           <td><input size="30"  type="password" name="password" tabindex=2></td>
                       </tr>
                       <tr>
                            <td></td>
                            <td id="loginerr">$loginNotif</td>
                       </tr>
                       <tr id="authbtn">
                           <td></td>
                           <td><input id="loginbtn" type="submit" value="$textStrings{loginbtn}" tabindex=3></td>
                       </tr>
                   </tbody>
           </table>
           </form>

           <p><a href="http://git.les-miquelots.net/gpigeon"
        title="gpigeon download link">Source code here.</a> It is similar to <a target="_blank" rel="nofollow noopener noreferrer" href="https://hawkpost.co/">hawkpost.co</a>.

       </body>
   </html>};
}
