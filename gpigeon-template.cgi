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

# Copyright (c) 2020-2021, Miquel Lionel <lionel@les-miquelots.net>

use warnings;
use strict;
use File::Path qw(mkpath rmtree);
use File::stat;
use Email::Valid;
use String::Random;
use Crypt::Argon2 qw(argon2id_verify);
use CGI qw(param);
use CGI::Cookie;
use CGI::Carp qw(fatalsToBrowser);

delete @ENV{qw(IFS PATH CDPATH BASH_ENV)};
$ENV{'PATH'} = q{bin_path_goes_here};
my $userAgent = $ENV{HTTP_USER_AGENT};
my $remoteIP = $ENV{REMOTE_ADDR};
my $hostname = $ENV{'SERVER_NAME'};

sub ValidCookie {
    my $clientLoginCookie = shift;
    if (not defined $clientLoginCookie){
        return;
    }
    my $dir = shift;
    my $filename = $clientLoginCookie->value;
    my $loginCookieFile = "$dir/$filename.txt";

    if ($filename =~ /^([\w]+)$/){
	    $filename = $1;
    }
    else{
	    return;
    }

    if (-e $loginCookieFile){ 
        open my $in, '<', $loginCookieFile or die "can't read file: $!";
        my $remoteIPLine = readline $in;
        my $userAgentLine = readline $in;
        my $cookieLine = readline $in;
        close $in;
        chomp ($remoteIPLine, $userAgentLine);
        if (not defined $cookieLine){
            return;
        }
        my %magicCookie = CGI::Cookie->parse($cookieLine) or die "$!";
        my $magicCookieValue = $magicCookie{'id'}->value;
   
        my $remoteIPMatch = $remoteIPLine cmp $remoteIP;
        my $userAgentMatch = $userAgentLine cmp $userAgent;
        my $magicCookieMatch = $magicCookieValue cmp $clientLoginCookie->value; 

        if ($remoteIPMatch == 0 and $userAgentMatch == 0 and $magicCookieMatch == 0){
            return 1;
        }
    }
    else{
        return;
    }
    return;
}

sub LoginCookieGen {
    my $IDCookie = shift;
    my $dir = shift;
    if (not defined $IDCookie){
        if (not -d "$dir"){
            mkpath("$dir") or die "$!";
        }
        my $StrRandObj = String::Random->new;
        my $val = $StrRandObj->randregex('\w{64}');
        my $cookieFile = "$dir/$val.txt";
        my $newLoginCookie = CGI::Cookie->new(
            -name  => 'id',
            -value => $val, 
            -expires => '+1y',
            '-max-age' => '+1y',
            -domain => ".$hostname",
            -path      => '/',
            -secure   => 1,
            -httponly => 1,
            -samesite => 'Strict',
       ) or die "Can't create cookie: $!";
       open my $out, '>', $cookieFile or die "Can't write to $cookieFile: $!";
       print $out "$remoteIP\n$userAgent\n$newLoginCookie";
       close $out;
       print "Set-Cookie: $newLoginCookie\n";
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
	my $RFC822Date = GetRFC822Date() or die;
    my $HasMailserver = q{has_mailserver_goes_here};
    my $mailSender = q{sender_addr_goes_here};
    my $mailSenderSMTP = q{smtp_domain_goes_here};
    my $mailSenderPort = q{smtp_port_goes_here};
    my $mailSenderPassword = q{sender_pw_goes_here};
	my $smtp     = undef;
	if ($HasMailserver){
		$smtp = Net::SMTP->new(Host => 'localhost') or die; 
	}
	else {
		$smtp = Net::SMTPS->new($mailSenderSMTP, Port => $mailSenderPort, doSSL => 'ssl', Debug_SSL => 0); 
		$smtp->auth($mailSender, $mailSenderPassword) or die;
	}
	my $notifyLinkByMailData = MIME::Entity->build(
		Date => $RFC822Date,
		From => $mailSender,
		To   => $recipient,
		Charset => 'utf-8',
		Subject => $title,
		Data => [$message]
    ) or die;

	$smtp->mail($mailSender) or die "Net::SMTP module has broke: $!.";
	if ($smtp->to($recipient)){
	    $smtp->data($notifyLinkByMailData->stringify);
	    $smtp->dataend();
	    $smtp->quit();
	}
	else {
	    die $smtp->message();
	}
}

my ( $linkAsker, $checkedOrNot, $hiddenPasswordField, $IDCookie, 
    $deleteIDCookie, $IDCookieValue, $refreshForm) = undef;
my $linkGenNotif = my $mailIsOkNotif = my $deletionNotif = my $loginNotif = my $sentMailNotif = '<!-- undef notif -->';
my @createdLinks = ();

my $argon2idHash       = qq{argon2idHash_goes_here};
my $cookiesDir         = q{cookiesDir_goes_here};
my $linkTemplatePath  = q{linkTemplatePath_goes_here};

my %textStrings = (
    addr                       => 'Address', 
    addr_ok                    => 'is valid!', 
    addr_nok                   => 'is not valid !',
    addr_unknown               => 'Unknown',
    create_link_btn            => 'Generate link', 
    checkbox_notiflinkbymail   => 'Notify the user by mail about the link',
    delete_link_btn_text       => 'Delete',
    delete_links_btn_text      => 'Delete all links',
    here                       => 'here',
    landingpage_title          => 'GPIGEON - Login',
    linkAsker_field_label      => 'Mail :',
    link_del_ok                => 'Successful removal !',
    link_ok_for                => 'Generated a link for',
    link_del_failed            => 'Deletion failed and here is why : ',
    loginbtn                   => 'Log in',
    logout_btn_text            => 'Logout',
    mailto_body                => 'Your link is ',
    mailto_subject             => 'Link to your one time GPG messaging form',
    mainpage_title             => 'GPIGEON - Main',
    notif_login_failure        => 'Cannot login. Check if your username and password match.',
    refresh_btn_text           => 'Refresh',
    theader_link               => 'Link', 
    theader_for                => 'For', 
    theader_deletion           => 'Deletion', 
    theader_cdate              => 'Created on', 
    web_greet_msg              => 'Hi and welcome.', 
);
my $CGIQueryGet = CGI->new;
my $password = $CGIQueryGet->param('password');
my $logout = $CGIQueryGet->param('logout');
my %currentCookies = CGI::Cookie->fetch;
$IDCookie = $currentCookies{'id'};

if (not defined $IDCookie){
    $hiddenPasswordField = qq{<input type="hidden" name="password" value="$password">};
    $refreshForm = qq{<form method="POST">
                   $hiddenPasswordField
                   <input id="refreshbtn" type="submit" value="$textStrings{refresh_btn_text}">
                </form>};
}
else{
    $hiddenPasswordField = '<!-- undef -->';
    $refreshForm = qq{<form method="GET">
                   <input id="refreshbtn" type="submit" value="$textStrings{refresh_btn_text}">
                </form>};
    $IDCookieValue = $IDCookie->value;

    if ($IDCookieValue =~ /^([\w]+)$/){
        $IDCookieValue = $1;
    }

    if ($logout){
        $deleteIDCookie = CGI::Cookie->new(
            -name       => 'id',
            -value      => $IDCookieValue,
            -expires    => '-1d',
            '-max-age'  => '-1d',
            -domain     => ".$hostname",
            -path       => '/',
            -secure     => 1,
            -httponly   => 1,
            -samesite   => 'Strict',
        );
        my $f = "$cookiesDir/$IDCookieValue.txt";
        if (-e "$f"){
            unlink "$f" or die "Can't delete file :$!";
        }
        print "Set-Cookie: $deleteIDCookie\n";
    }
}

print "Cache-Control: no-store, must-revalidate\n";
if (ValidCookie($IDCookie, $cookiesDir) or argon2id_verify($argon2idHash,$password)){

    LoginCookieGen($IDCookie, $cookiesDir);

    if (defined $CGIQueryGet->param('supprlien')){
        my $pendingDeletion = $CGIQueryGet->param('supprlien');
        my $linkFileFilename = "./l/$pendingDeletion";
        if (unlink UntaintCGIFilename($linkFileFilename)){ 
            $deletionNotif = qq{<span id="success">$textStrings{link_del_ok}</span>};
        }
        else {
            $deletionNotif = qq{<span id="failure">$textStrings{link_del_failed} $linkFileFilename : $!</span>};
        }
    }

    if (defined $CGIQueryGet->param('supprtout')){
        rmtree('./l', {keep_root => 1, safe => 1});
        $deletionNotif = qq{<span id="success">$textStrings{link_del_ok}</span>};
    }

    if (defined $CGIQueryGet->param('mail')){
        $linkAsker = scalar $CGIQueryGet->param('mail');

        if ( Email::Valid->address($linkAsker) ){
            $mailIsOkNotif = qq{<span id="success">$textStrings{addr} $linkAsker $textStrings{addr_ok}</span>};
            my $StrRandObj = String::Random->new;
            my $generatedFormFilename = $StrRandObj->randregex('\w{64}') . '.cgi';
            my $hrefLink = "https://$hostname/cgi-bin/l/$generatedFormFilename";
            my $linkPath 	 =  "./l/$generatedFormFilename";

            open my $in, '<', $linkTemplatePath or die "Can't read link template file: $!";
            open my $out, '>', $linkPath or die "Can't write to link file: $!";
            while( <$in> ) {
                s/{link_user}/{$linkAsker}/g;
                print $out $_;
            }
            close $in or die;
            chmod(0755,$linkPath) or die;
            close $out or die;
            $linkGenNotif = qq{<span id="success">$textStrings{link_ok_for} $linkAsker: </span><br><a target="_blank" rel="noopener noreferrer nofollow" href="$href">$href</a>};          
            if (defined $CGIQueryGet->param('notiflinkbymail')){
                SendGpigeonMail($linkAsker,"[GPIGEON](Do not reply) Your encrypted form is ready","Greetings,\n\n\tAn encrypted form has been generated for you on $hostname.\n\tClick on the link below to fill in the form:\n\t$hrefLink\n\tIf you believe this mail is not meant for you, ignore it and mail the webmaster or admin about it.\n\nKind regards,\nGpigeon mailing system at $hostname.") or $sentMailNotif="$!" ;
            }
        }
        else{
            $mailIsOkNotif = qq{<span id="failure">$textStrings{addr} $linkAsker $textStrings{addr_nok}.</span>};
        }
    }

    opendir my $linkDirHandle, './l' or die "Can't open ./l: $!";
    while (readdir $linkDirHandle) {
        if ($_ ne '.' and $_ ne '..'){
            my $linkFileFilename = $_;
            my $linkFileStats = stat("./l/$linkFileFilename");
            my $linkCreationDate = scalar localtime $linkFileStats->mtime;
            if (open my $linkFileHandle , '<', "./l/$linkFileFilename"){
                for (1..2){
                    $linkAsker = readline $linkFileHandle;
                    $linkAsker =~ s/q\{(.*?)\}//i;
                    $linkAsker = $1;
                }
                close $linkFileHandle;
                
                if (Email::Valid->address($linkAsker)){
                    push @createdLinks,
                    qq{<tr>
                           <td><a target="_blank" rel="noopener noreferrer nofollow" href="/cgi-bin/l/$linkFileFilename">$textStrings{here}</a></td>
                           <td><a href="mailto:$linkAsker?subject=$textStrings{mailto_subject}&body=$textStrings{mailto_body} http://$hostname/cgi-bin/l/$linkFileFilename">$linkAsker</a></td>
                           <td>$linkCreationDate</td>
                           <td>
                               <form method="POST">
                                   $hiddenPasswordField
                                   <input type="hidden" name="supprlien" value="$linkFileFilename">
                                   <input id="deletelinkbtn" type="submit" value="$textStrings{delete_link_btn_text}">
                               </form>
                           </td>
                       </tr>};
                }
            }
            else {
                close $linkFileHandle;
                die 'Content-type: text/plain', "\n\n", "Error: Can't open $linkFileFilename: $!";
            }
        }
    }
    closedir $linkDirHandle;

    print 'Content-type: text/html',"\n\n",
    qq{<!DOCTYPE html>
        <html> 
            <head> 
                <link rel="icon" sizes="48x48" type="image/ico" href="/favicon.ico">
                <link rel="stylesheet" type="text/css" href="/styles.css">
                <meta http-equiv="content-type" content="text/html;charset=UTF-8">
                <meta name="viewport" content="width=device-width">
                <meta charset="UTF-8">
                <title>$textStrings{mainpage_title}</title>
            </head>
            <body>
                <h1>$textStrings{mainpage_title}</h1>
                <p>$textStrings{web_greet_msg}</p>
                <form method="GET">
                    <input type="hidden" name="logout" value="1">
                    <input id="logoutbtn" type="submit" value="$textStrings{logout_btn_text}">
                </form>
                $refreshForm
                <hr>
                <br>
                <form method="POST">
                    $hiddenPasswordField
                    $textStrings{linkAsker_field_label}<br>
                    <input id="mailfield" tabindex="1" type="text" name="mail" autofocus>
                    <input id="genlinkbtn" tabindex="2" type="submit" value="$textStrings{create_link_btn}">
                    <label id="notiflinkbymail" for="notiflinkbymail">
                        $textStrings{checkbox_notiflinkbymail}
                        <input id="notiflinkbymail-check" type="checkbox" name="notiflinkbymail" value="1">
                    </label>
                </form>
                $linkGenNotif
                <br>
                $sentMailNotif
                <hr>
                <form method="POST">
                    $hiddenPasswordField
                    <input type="hidden" name="supprtout">
                    <input id="deleteallbtn" type="submit" value="$textStrings{delete_links_btn_text}">
                </form>
                $deletionNotif
                <table id="linkstable">
                    <tr>
                        <th>&#x1f517; $textStrings{theader_link}</th>
                        <th>&#x1f4e7; $textStrings{theader_for}</th>
                        <th>&#x1f4c5; $textStrings{theader_cdate}</th>
                        <th>&#10060; $textStrings{theader_deletion}</th>
                    </tr>
                    @createdLinks
                </table>
            </body>
        </html>};
}
else{
    if (not $logout and defined $IDCookie){
        $loginNotif = q{<span id="failure">You got a cookie problem.<br>
        <b>Clean them and log again</b></span>};
    }
    if (length($password) > 0){
        $loginNotif = q{<span id="failure">Your typed password seems<br>
        to be incorrect.<br>Try again.</span>};
    }
    
    print "Content-type: text/html\n\n",
    qq{<!DOCTYPE html>
    <html lang="fr">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width">
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
                          <td>Password :</td> 		  
                          <td><input type="password" name="password" autofocus></td>
                      </tr>
                      <tr>
                            <td></td>
                            <td id="loginerr">$loginNotif</td>
                      </tr>
                      <tr id="authbtn">
                          <td></td>
                          <td><input type="submit" value="$textStrings{loginbtn}"></td>
                      </tr>
                  </tbody>
                </table>
            </form>

            <p><a href="http://git.les-miquelots.net/gpigeon"
               title="gpigeon download link">Source code here.</a> It is similar to <a target="_blank" rel="noopener nofollow noreferrer" href="https://hawkpost.co/">hawkpost.co</a>.</p>

        </body>
    </html>};
}
