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
use DBI;
use Email::Valid;
use CGI qw(param);
use CGI::Cookie;
use CGI::Carp qw(fatalsToBrowser);
use Crypt::Argon2 qw(argon2id_verify);
use File::Path qw(mkpath rmtree);
use File::stat;
use String::Random;

delete @ENV{qw(IFS PATH CDPATH BASH_ENV)};
$ENV{'PATH'}     = q{bin_path_goes_here};
my $rIP          = $ENV{REMOTE_ADDR};
my $uagent       = $ENV{HTTP_USER_AGENT};
my %text_strings = (
    addr                   => 'Address', 
    addr_ok                => 'is valid!', 
    addr_nok               => 'is not valid !',
    addr_unknown           => 'Unknown',
    create_link_btn        => 'Create link',
    create_invite_btn      => 'Create invite',
    cookie_problems        =>'You got a cookie problem.<br> <b>Clean them and log in again</b>',
    delete_link_btn_text   => 'Delete',
    delete_links_btn_text  => 'Delete all links',
    disconnect_btn_text    => 'Disconnect',
    here                   => 'here',
    landingpage_title      => 'GPIGEON - Log in',
    logout_btn_text        => 'Logout',
    loginbtn               => 'Log in',
    link_asker_field_label => "Asker's mail :",
    link_del_ok            => 'Successful removal !',
    link_legend_textarea   =>'Type your message below :',
    link_ok_for            => 'Generated a link for',
    link_del_failed        => 'Deletion failed and here is why : ',
    link_generated_ok      => "Here's the link",
    mailto_body            => 'Your link is ',
    mailto_subject         => 'Link to your one time GPG messaging form',
    incorrect_ids          => 'Username/password combination<br> is incorrect.<br>Try again.',
    password_label         => 'Password',
    refresh_btn            => 'Refresh',
    theader_link           => 'Link', 
    theader_for            => 'For', 
    theader_deletion       => 'Deletion',
    theader_cdate          => 'Created on',
    username_label         => 'Username',
    web_title              => 'GPIGEON.CGI - Main', 
    web_greet_msg          => 'Hi and welcome. What will you do today ?', 
);


sub DbGetLine {
    my ($dbh, $query) = @_;
    my $prep          = $dbh->prepare( $query );
    my $exec          = $prep->execute() or die $DBI::errstr;

    if ($exec < 0){
        print $DBI::errstr;
    }

    while (my @rows = $prep->fetchrow_array()) {
        my $row = $rows[0];
        return $row;
    }
}

sub GetFileTable {
    my ($dir ,$hidden_loginfield) = @_;
    my @table                     = ();
    opendir my $dir_hnd, "$dir" or die "[GetFileTable function] Can't open $dir: $!";
    while (readdir $dir_hnd) {
        if ($_ ne '.' and $_ ne '..'){
            my $linkfile_fn = $_;
            my $linkstats   = stat("$dir/$linkfile_fn"); 
            my $mtime       = scalar localtime $linkstats->mtime;
            my $link_asker  = undef;
            if (open my $f_hnd , '<', "$dir/$linkfile_fn"){
                for (1..2){
                    $link_asker = readline $f_hnd;
                    $link_asker =~ s/q\{(.*?)\}//i;
                    $link_asker = $1;
                }
                close $linkfile_handle;
                my $for_field_body = qq{<a href="mailto:$link_asker?subject=$text_strings{mailto_subject}&body=$text_strings{mailto_body} http://$ENV{SERVER_NAME}/cgi-bin/$dir/$linkfile_fn">$link_asker</a>};

                if (not defined $link_asker){
                    $for_field_body = $text_strings{addr_unknown};
                }
                #create links table html
                push @table,
                qq{<tr>
                <td><a title="This link has been created on $mtime" href="/cgi-bin/$dir/$linkfile_fn" target="_blank" rel="noopener noreferrer nofollow">ici</a></td>
                <td>$for_field_body</td>
                <td>
                <form method="POST">
                $hidden_loginfield
                <input type="hidden" name="adminpan" value="1">
                <input type="hidden" name="supprlien" value="$dir/$linkfile_fn">
                <input id="deletelinkbtn" type="submit" value="$text_strings{delete_link_btn_text}">
                </form>
                </td>
                </tr>};

            }
            else {
                close $linkfile_handle;
                die "[GetFileTable function] Error: Can't open $linkfile_fn: $!";
            }
        }
    }
    closedir $dir_hnd;
    return @table;
}

sub LoginOk {
    my ($dbh, $username, $pass, $userid,
    $magic_cookie, $uid_cookie, 
    $cookiesdir)     = @_;
    my $loginsuccess = PasswdLogin($dbh, $username, $pass);
    if (not defined $loginsuccess){
        $loginsuccess = CookieLogin($userid, $magic_cookie, $uid_cookie, $cookiesdir);
    }
    return $loginsuccess;
}

sub CookieLogin {
    my ($userid, $magic_cookie, $uid_cookie, $cookiesdir) = @_;
    if (not $userid =~ /^([0-9]+)$/){
        return;
    }

    if (not defined $magic_cookie or not defined $uid_cookie){
        return;
    }

    my ($rip_line, $ua_line, $id_line, $uid_line) = undef;
    my $filename = $magic_cookie->value;
    if ($filename =~ /^([\w]+)$/){
        $filename = $1;
    }
    else{
        return;
    }

    my $login_cookiefile = "$cookiesdir/$userid/$filename.txt";
    if (-e $login_cookiefile){
        open my $in, '<', $login_cookiefile or die "[CookieLogin function] can't read file: $!";
        $rip_line = readline $in;
        $ua_line  = readline $in;
        $id_line  = readline $in;
        $uid_line = readline $in;
        close $in;
        chomp ($rip_line, $ua_line, $id_line); # chomp the \n
    }
    else{
        return;
    }

    my %id_line_cookie  = CGI::Cookie->parse($id_line);
    my %uid_line_cookie = CGI::Cookie->parse($uid_line);
    my $id_value        = $id_line_cookie{'id'}->value;
    my $uid_value       = $uid_line_cookie{'uid'}->value;

    my $ip_match        = $rip_line cmp $rIP;
    my $ua_match        = $ua_line cmp $uagent;
    my $uid_match       = $uid_cookie->value cmp $uid_value;
    my $id_match        = $magic_cookie->value cmp $id_value;

    if ($ip_match == 0 and $ua_match == 0 and $uid_match == 0 and $id_match == 0){
        return $userid;
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
	my ($hash, $userid) = undef;	
	my $selecthash = qq{SELECT pass from users where mail='$username' or name='$username';};
	$hash = DbGetLine($dbh, $selecthash);
	if (defined $hash and length($hash) > 1){
		if(argon2id_verify($hash,$pass)){
			my $selectuserid = qq{SELECT userid from users where pass='$hash';};
			$userid = DbGetLine($dbh, $selectuserid);
			if ($userid =~ /^([0-9]+)$/){
				$userid = $1;
			}
			else {
				return;
			}
			return $userid; # as an userid is always > 0, we can use it as return value
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
    my ($userid, $magic_cookie, $cookiesdir) = @_;
    if (not defined $magic_cookie){
        my $str_rand_obj = String::Random->new;
        my $val = $str_rand_obj->randregex('\w{64}');
        if (not -d "$cookiesdir/$userid"){
            mkpath("$cookiesdir/$userid");
        }
        my $cookiefile = "$cookiesdir/$userid/$val.txt";
        my $new_magic_cookie = CGI::Cookie->new(
            -name  => 'id',
            -value => $val, 
            -expires => '+1y',
            '-max-age' => '+1y',
            -domain => ".$ENV{'SERVER_NAME'}",
            -path      => '/',
            -secure   => 1,
            -httponly => 1,
            -samesite => 'Strict',
        ) or die "Can't create cookie $!";
        my $new_userid_cookie = CGI::Cookie->new(
            -name  => 'uid',
            -value => $userid, 
            -expires => '+1y',
            '-max-age' => '+1y',
            -domain => ".$ENV{'SERVER_NAME'}",
            -path      => '/',
            -secure   => 1,
            -httponly => 1,
            -samesite => 'Strict',
       ) or die "Can't create cookie $!";
       open my $out, '>', $cookiefile or die "Can't write to $cookiefile: $!";
           print $out "$rIP\n$uagent\n$new_magic_cookie\n$new_userid_cookie";
       close $out;
       print "Set-Cookie: $new_magic_cookie\n";
       print "Set-Cookie: $new_userid_cookie\n";
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

my $hostname = $ENV{'SERVER_NAME'};	

my $db_path                             = q{db_path_goes_here};
my $cookiesdir                          = q{cookies_dir_goes_here};
my $link_template_path                  = q{link_template_path_goes_here};
my $invites_template_path               = q{invite_template_goes_here};

my $cgi_query_get                       = CGI->new;
my $username                            = $cgi_query_get->param('username');
my $pass                                = $cgi_query_get->param('password');
my $disconnect                          = $cgi_query_get->param('disconnect');
my ( $checkedornot, $hidden_loginfield, $magic_cookie, 
    $uid_cookie, $idval, $refresh_form, 
    $userid)                            = undef;
my $linkgen_notif                       = my $mailisok_notif = my $deletion_notif = my $login_notif = '<!-- undef notif -->';
my @created_links                       = ();
my %cur_cookies                         = CGI::Cookie->fetch;
$uid_cookie                             = $cur_cookies{'uid'};
$magic_cookie                           = $cur_cookies{'id'};
my $dbh                                 = DBI->connect("DBI:SQLite:dbname=$db_path", undef, undef, { RaiseError => 1})
                                            or die $DBI::errstr;

if ($adminpanselect){
	$adminpan_field = q{<input type="hidden" name="adminpan" value="1">};
}


if (not defined $magic_cookie){ # cookie is not set
    $hidden_loginfield = qq{<input type="hidden" name="username" value="$username"><input type="hidden" name="password" value="$pass">};

    $refresh_form = qq{<form method="POST">
                   $hidden_loginfield
		   $adminpan_field
                   <input id="refreshbtn" type="submit" value="$text_strings{refresh_btn}">
                </form>};
}else{
    $hidden_loginfield = qq{<!-- undef -->};
    $refresh_form = qq{<form method="GET">
		   $adminpan_field
                   <input id="refreshbtn" type="submit" value="$text_strings{refresh_btn}">
                </form>};
   $idval = $magic_cookie->value;
   if ($idval =~ /^([\w]+)$/){
	   $idval = $1;
   }

   $userid = $uid_cookie->value;
   if ($userid =~ /^([0-9]+)$/){
	   $userid = $1;
   }

}

if ($disconnect and defined $magic_cookie){ # if we disconnect and cookie is active
	   my $delete_id_cookie = CGI::Cookie->new(
		-name  => 'id',
		-value => $idval, 
		-expires => '-1d',
		'-max-age' => '-1d',
		-domain => ".$hostname",
		-path      => '/',
		-secure   => 1,
		-httponly => 1,
		-samesite => 'Strict',
	   );
	   my $delete_uid_cookie = CGI::Cookie->new(
		-name  => 'uid',
		-value => $userid, 
		-expires => '-1d',
		'-max-age' => '-1d',
		-domain => ".$hostname",
		-path      => '/',
		-secure   => 1,
		-httponly => 1,
		-samesite => 'Strict',
	   );
	   my $f = "$cookiesdir/$userid/$idval.txt";
	   if (-e "$f"){
            unlink "$f" or die "cant delete cookie at $f :$!\n"; # delet it

       }       
       print "Set-Cookie: $delete_uid_cookie\n";
       print "Set-Cookie: $delete_id_cookie\n";
}



my $loginok = LoginOk($dbh, $username, $pass, $userid, $magic_cookie, $uid_cookie, $cookiesdir);
print "Cache-Control: no-store, must-revalidate\n";
if($loginok){

    $userid           = $loginok; 
    my $user_mailaddr = DbGetLine($dbh, qq{SELECT mail from users where userid='$userid';});
    my $nick          = DbGetLine($dbh, qq{SELECT name from users where userid='$userid';});
    my $isadmin       = DbGetLine($dbh, qq{SELECT isadmin from users where userid='$userid';});
    LoginCookieGen($userid, $magic_cookie, $cookiesdir);

    if ($isadmin){
        $adminbtn = qq{<form method="POST">
                $hidden_loginfield
                <input type="hidden" name="adminpan" value="1">
                <input id="adminpanbtn" type="submit" value="Admin panel">
            </form>};
        if (not -d "i/$userid"){
            mkpath("./i/$userid");
        }
    }

    if (not -d "./l/$userid"){
        mkpath("./l/$userid");
    }

    if (defined $cgi_query_get->param('supprlien')){
        my $pending_deletion = $cgi_query_get->param('supprlien');

        #make sure a form file deletion POST request don't go deleting other things
        if ($pending_deletion =~ /^l\/$userid\/([\w]+)\.cgi$/ or $pending_deletion =~ /^i\/$userid\/([\w]+)\.cgi$/) {
            if (unlink UntaintCGIFilename($pending_deletion)){ 
                $deletion_notif = qq{<span id="success">$text_strings{link_del_ok}</span>};
            }
            else {
                $deletion_notif = qq{<span id="failure">$text_strings{link_del_failed} $pending_deletion: $!</span>};
            }
        }
    }

    if (defined $cgi_query_get->param('supprtout')){
        rmtree("./l/$userid", {keep_root=>1, safe=>1});
        $deletion_notif = qq{<span id="success">$text_strings{link_del_ok}</span>};
    }
    
    if (defined $cgi_query_get->param('delallinvites')){
        rmtree("./i/$userid", {keep_root=>1, safe=>1});
        $deletion_notif = qq{<span id="success">$text_strings{link_del_ok}</span>};
    }

    if (defined $cgi_query_get->param('geninv')){
        my $invite_asker      = scalar $cgi_query_get->param('opt-mail');
        $mailisok_notif       = qq{<span id="failure">$text_strings{addr} $invite_asker $text_strings{addr_nok}</span>};
        my $str_rand_obj      = String::Random->new;
        my $random_fn         = $str_rand_obj->randregex('\w{64}');
        my $NEW_FORM_FILENAME = "$random_fn.cgi";
        my $HREF_LINK   	  = "https://$hostname/cgi-bin/i/$userid/$NEW_FORM_FILENAME";
        my $INVITES_PATH 	  =  "./i/$userid/$NEW_FORM_FILENAME";

        open my $in, '<', $invites_template_path or die "Can't read link template file: $!";
        open my $out, '>', $INVITES_PATH or die "Can't write to link file: $!";
        while( <$in> ) {
            if ( Email::Valid->address($invite_asker) ){
                $mailisok_notif = qq{<span id="success">$text_strings{addr} $invite_asker $text_strings{addr_ok}</span>};
                s/mail = undef;/mail = q{$invite_asker};/g;
                s/{mailfield_goes_here}/{<input type="text" name="mailaddr" value="$invite_asker" disabled>}/g;
            }
            s/{mailfield_goes_here}/{<input type="text" name="mailaddr" placeholder="Your mail address used for GPG" required autofocus>}/g;

            if (defined $cgi_query_get->param('mailnotif') ){
                s/EMAIL_NOTIF = q{0}/EMAIL_NOTIF = q{1}/g	
            }

            if (defined $cgi_query_get->param('adminprom') ){
                s/is_admin_goes_here/1/g	
            }
            else{
                s/is_admin_goes_here/0/g	
            }

            s/{user_mailaddr_goes_here}/{$user_mailaddr}/g;
            print $out $_;
        }

        close $in or die;
        chmod(0755,$INVITES_PATH) or die;
        close $out or die;

        $linkgen_notif = qq{<span id="success">$text_strings{link_generated_ok}: <br><a target="_blank" rel="noopener noreferrer nofollow" href="$HREF_LINK">$HREF_LINK</a></span>};          
    }
    
    if (defined $cgi_query_get->param('mail')){
        my $link_asker = scalar $cgi_query_get->param('mail');

        if ( Email::Valid->address($link_asker) ){
            $mailisok_notif             = qq{<span id="success">$text_strings{addr} $link_asker $text_strings{addr_ok}</span>};
            my $str_rand_obj            = String::Random->new;
            my $random_fn               = $str_rand_obj->randregex('\w{64}');
            my $NEW_FORM_FILENAME = "$random_fn.cgi";
            my $HREF_LINK   	        = "https://$hostname/cgi-bin/l/$userid/$NEW_FORM_FILENAME";
            my $LINK_PATH 	            =  "./l/$userid/$NEW_FORM_FILENAME";

            open my $in, '<', $link_template_path or die "Can't read link template file: $!";
            open my $out, '>', $LINK_PATH or die "Can't write to link file: $!";
            while( <$in> ) {
                s/{link_user}/{$link_asker}/g;
                s/{user_mailaddr_goes_here}/{$user_mailaddr}/g;
                print $out $_;
            }
            close $in or die;
            chmod(0755,$LINK_PATH) or die;
            close $out or die;

            $linkgen_notif  = qq{<span id="success">$text_strings{link_generated_ok}: <br><a target="_blank" rel="noopener noreferrer nofollow" href="$HREF_LINK">$HREF_LINK</a></span>};          
        }
        else{
            $mailisok_notif = qq{<span id="failure">$text_strings{addr} $link_asker $text_strings{addr_nok}</span>};
        }
    }
    
    my @links_table   = GetFileTable("l/$userid", $hidden_loginfield, $adminpan_field); 

    print 'Content-type: text/html',"\n\n";
    if ($adminpanselect and $isadmin){
        my @invites_table = GetFileTable("i/$userid", $hidden_loginfield, $adminpan_field);


        print qq{<!DOCTYPE html>
            <html> 
                <head> 
                    <link rel="icon" sizes="48x48" type="image/ico" href="/favicon.ico">
                    <link rel="stylesheet" type="text/css" href="/styles.css">
                    <meta http-equiv="content-type" content="text/html;charset=UTF-8">
                    <meta charset="UTF-8">
                    <title>$text_strings{web_title}</title>
                </head>
                <body>
            <h1>GPIGEON - Admin panel</h1>
                <p>Welcome to the admin panel. Here, you can view and generate account invites and also search and delete users.</p>
            <form method="GET">
                $hidden_loginfield
                <input id="adminpanbtn" type="submit" value="Main panel">
            </form>
                    <form method="GET">
                        <input type="hidden" name="disconnect" value="1">
                        <input id="logoutbtn" type="submit" value="$text_strings{disconnect_btn_text}">
                    </form>
            $refresh_form
            <hr>
            <form method="POST">
                $hidden_loginfield
                $adminpan_field
                        <label for="opt-mail">
                (Optional) Mail :
                    <input tabindex="1" id="mailfield" type="text" name="opt-mail">
                </label>
                <input name="geninv" type="submit" id="geninvbtn" value="$text_strings{create_invite_btn}">
                <label id="mailnotif" for="mailnotif">
                Notify by mail after successful account creation
                    <input id="mailnotif-check" type="checkbox" name="mailnotif" value="1">
                </label>
                <label id="adminprom" for="adminprom">
                Make admin
                    <input id="adminprom-check" type="checkbox" name="adminprom" value="1">
                </label>
                <input name="geninv" type="submit" id="geninvbtn-mob" value="$text_strings{create_invite_btn}"><br>
            </form>
            <hr>

            <form method="POST">
                        $hidden_loginfield
            $adminpan_field
                        <input id="deleteallbtn" type="submit" name="delallinvites" value="$text_strings{delete_invites_btn_text}">
                    </form>
                    $deletion_notif
                    <table id="linkstable">
                        <tr>
                            <th>&#x1f517; $text_strings{theader_link}</th>
                            <th>&#x1f4e7; $text_strings{theader_for} </th>
                            <th>&#10060; $text_strings{theader_deletion}</th>
                        </tr>
                <tbody>
                @invites_table
                </tbody>
                    </table>
            </body>
            </html>};
    }
    else {
    print qq{<!DOCTYPE html>
        <html> 
            <head> 
                <link rel="icon" sizes="48x48" type="image/ico" href="/favicon.ico">
                <link rel="stylesheet" type="text/css" href="/styles.css">
                <meta http-equiv="content-type" content="text/html;charset=UTF-8">
                <meta charset="UTF-8">
                <title>$text_strings{web_title}</title>
            </head>
            <body>
	    	<h1>$text_strings{web_title}</h1>
                <p>$text_strings{web_greet_msg}</p>
		$adminbtn
                <form method="GET">
                    <input type="hidden" name="disconnect" value="1">
		            <input id="logoutbtn" type="submit" value="$text_strings{disconnect_btn_text}">
                </form>
		$refresh_form
                <hr>
                <br>
                <form method="POST">
                    $hidden_loginfield
                    Mail de la personne:<br>
                    <input id="mailfield" tabindex="1" placeholder="Link user mail address" type="text" name="mail">
                    <input id="genlinkbtn" tabindex="2" type="submit" value="$text_strings{create_link_btn}">
                </form>
                $mailisok_notif
                <br>
                $linkgen_notif
                <hr>
                <form method="POST">
                    $hidden_loginfield
                    <input id="deleteallbtn" name="supprtout" type="submit" value="$text_strings{delete_links_btn_text}">
                </form>
                $deletion_notif
                <table id="linkstable">
                    <tr>
                        <th>&#x1f517; $text_strings{theader_link}</th>
                        <th>&#x1f4e7; $text_strings{theader_for} </th>
                        <th>&#10060; $text_strings{theader_deletion}</th>
                    </tr>
		    <tbody>
			    @links_table
		    </tbody>
                </table>
            </body>
        </html>};
	}
}
else{
    $dbh->disconnect;
    if (not $disconnect and defined $magic_cookie){
        $login_notif = qq{<span id="failure">$text_strings{cookie_problems}</span>};
    }
    if (length($pass) > 0 or length($username) > 0){
        $login_notif = qq{<span id="failure">$text_strings{incorrect_ids}</span>};
    }
    
    print "Content-type: text/html\n\n",
qq{<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<link rel="icon" type="image/x-icon" href="/favicon.ico">
<link rel="stylesheet" type="text/css" href="/styles.css">
<title>$text_strings{landingpage_title}</title>
</head>
<body>
<h1>$text_strings{landingpage_title}</h1>
<form action="/cgi-bin/gpigeon.cgi" method="POST">
<table id="loginbox">
<tbody>
 <tr>
   <td id="labels">$text_strings{username_label}</td>
   <td><input type="text" name="username" autofocus tabindex=1></td>
 </tr>
 <tr>
   <td id="labels">$text_strings{password_label}</td>
   <td><input type="password" name="password" tabindex=2></td>
 </tr>
      <tr>
            <td></td>
            <td id="loginerr">$login_notif</td>
      </tr>
 <tr id="authbtn">
   <td></td>
   <td><input id="loginbtn" type="submit" value="$text_strings{loginbtn}" tabindex=3></td>
 </tr>
</tbody>
</table>
</form>

<p><a href="http://git.les-miquelots.net/gpigeon"
    title="gpigeon download link">Source code here.</a> It is similar to <a target="_blank" rel="nofollow noopener noreferrer" href="https://hawkpost.co/">hawkpost.co</a>.

</body>
</html>};
}
