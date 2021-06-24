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
use Crypt::Argon2 qw(argon2id_verify);
use Email::Valid;
use String::Random;
use DBI;
use CGI qw(param);
use CGI::Cookie;
use CGI::Carp qw(fatalsToBrowser);
use File::Path qw(mkpath rmtree);

my $rIP = $ENV{REMOTE_ADDR};
my $uagent  = $ENV{HTTP_USER_AGENT};

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
    my ($dbh, $username, $pass, $userid, $magic_cookie, $uid_cookie, $cookiesdir) = @_;
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
        open my $in, '<', $login_cookiefile or die "can't read file: $!";
        $rip_line = readline $in;
        $ua_line = readline $in;
        $id_line = readline $in;
        $uid_line = readline $in;
        close $in;
        chomp ($rip_line, $ua_line, $id_line); # chomp the \n
    }
    else{
        return;
    }

    my %id_line_cookie = CGI::Cookie->parse($id_line);
    my %uid_line_cookie = CGI::Cookie->parse($uid_line);
    my $id_value = $id_line_cookie{'id'}->value;
    my $uid_value = $uid_line_cookie{'uid'}->value;

    my $ip_match = $rip_line cmp $rIP;
    my $ua_match = $ua_line cmp $uagent;
    my $uid_match = $uid_cookie->value cmp $uid_value;
    my $id_match = $magic_cookie->value cmp $id_value;

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
	my $selecthash = qq{SELECT pass from pigeons where mail='$username' or name='$username';};
	$hash = DbGetLine($dbh, $selecthash);
	if (defined $hash and length($hash) > 1){
		if(argon2id_verify($hash,$pass)){
			my $selectuserid = qq{SELECT userid from pigeons where pass='$hash';};
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
           print $out "$rIP\n$ua\n$new_magic_cookie\n$new_userid_cookie";
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

sub NotifIfDefined{
    my $notif = shift;
    if (defined $notif){
        return $notif;
    }
    else{
        return '<!--undef notif-->';
    }
}

delete @ENV{qw(IFS PATH CDPATH BASH_ENV)};
$ENV{'PATH'} = '/usr/bin';
my $hostname = $ENV{'SERVER_NAME'};	

my $db_path             = q{db_path_goes_here};
my $argon2id_hash       = q{argon2id_hash_goes_here};
my $cookiesdir          = q{cookies_dir_goes_here};
my $link_template_path  = q{link_template_path_goes_here};

my %text_strings = (
    addr => 'Address', 
    addr_ok => 'is valid!', 
    addr_nok => 'is not valid !',
    addr_unknown => 'Unknown',
    create_link_btn => 'Generate link', 
    delete_link_btn_text => 'Delete',
    delete_links_btn_text => 'Delete all links',
    disconnect_btn_text => 'Disconnect',
    logout_btn_text => 'Logout',
    here => 'here',
    link_asker_field_label => "Asker's mail :",
    link_web_title => 'One time GPG messaging form',
    link_del_ok => 'Successful removal !',
    link_legend_textarea =>'Type your message below :',
    link_send_btn => 'Send',
    link_ok_for => 'Generated a link for',
    link_del_failed => 'Deletion failed and here is why : ',
    link_generated_ok => "Here's the link",
    mailto_body => 'Your link is ',
    mailto_subject => 'Link to your one time GPG messaging form',
    notif_login_failure => 'Cannot login. Check if your username and password match.',
    theader_link => 'Link', 
    theader_for => 'For', 
    theader_deletion => 'Deletion', 
    web_title => 'GPIGEON.CGI: generate one time GPG messaging links !', 
    web_greet_msg => 'Hi and welcome.', 
);

my $cgi_query_get = CGI->new;
my $username = $cgi_query_get->param('username');
my $pass = $cgi_query_get->param('password');
my $disconnect = $cgi_query_get->param('disconnect');
my ($linkgen_notif, $mailisok_notif, $deletion_notif, $checkedornot,
    $session, $hidden_loginfield, $magic_cookie, 
    $uid_cookie, $idval, $refresh_form, $userid) = undef;
my @created_links = ();
my %cur_cookies = CGI::Cookie->fetch;
$uid_cookie = $cur_cookies{'uid'};
$magic_cookie = $cur_cookies{'id'};
my $dbh = DBI->connect("DBI:SQLite:dbname=$db_path", undef, undef, { RaiseError => 1})
                or die $DBI::errstr;

if (not defined $magic_cookie){ # cookie is not set
    $hidden_loginfield = qq{<input type="hidden" name="username" value="$username"><input type="hidden" name="password" value="$pass">};

    $refresh_form = qq{<form method="POST">
                   $hidden_loginfield
                   <input id="refreshbtn" type="submit" value="$text_strings{refresh_btn_text}">
                </form>};
}else{
    $hidden_loginfield = qq{<!-- undef -->};
    $refresh_form = qq{<form method="GET">
                   <input id="refreshbtn" type="submit" value="$text_strings{refresh_btn_text}">
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

    $userid = $loginok; 
    LoginCookieGen($userid, $magic_cookie, $cookiesdir);
    my $user_mailaddr = DbGetLine($dbh, qq{SELECT mail from pigeons where userid='$userid';});
    my $gpgid = DbGetLine($dbh, qq{SELECT gpgfp from pigeons where userid='$userid';});
    my $nick = DbGetLine($dbh, qq{SELECT name from pigeons where userid='$userid';});
    if (not -d "./l/$userid"){
        mkpath("./l/$userid");
    }

    if (defined $cgi_query_get->param('supprlien')){
        my $pending_deletion = $cgi_query_get->param('supprlien');
        my $linkfile_fn = "./l/$userid/$pending_deletion";
        if (unlink UntaintCGIFilename($linkfile_fn)){ 
            $deletion_notif=qq{<span id="success">$text_strings{link_del_ok}</span>};
        }
        else {
            $deletion_notif=qq{<span id="failure">$text_strings{link_del_failed} $linkfile_fn : $!</span>};
        }
    }

    if (defined $cgi_query_get->param('supprtout')){
        rmtree("./l/$userid", {keep_root=>1, safe=>1});
        $deletion_notif=qq{<span id="success">$text_strings{link_del_ok}</span>};
    }

    if (defined $cgi_query_get->param('mail')){
        my $link_asker = scalar $cgi_query_get->param('mail');

        if ( Email::Valid->address($link_asker) ){
            $mailisok_notif = qq{<span id="success">$text_strings{addr} $link_asker $text_strings{addr_ok}</span>};
            my $str_rand_obj = String::Random->new;
            my $random_fn = $str_rand_obj->randregex('\w{64}');
            my $GENERATED_FORM_FILENAME = "$random_fn.cgi";
            my $HREF_LINK   	 = "https://$hostname/cgi-bin/l/$userid/$GENERATED_FORM_FILENAME";
            my $LINK_PATH 	 =  "./l/$userid/$GENERATED_FORM_FILENAME";

            open my $in, '<', $link_template_path or die "Can't read link template file: $!";
            open my $out, '>', $LINK_PATH or die "Can't write to link file: $!";
            while( <$in> ) {
                s/{link_user}/{$link_asker}/g;
                s/{gpgid_goes_here}/{$gpgid}/g;
                s/{link_filename}/{$GENERATED_FORM_FILENAME}/g;
		s/{user_mailaddr_goes_here}/{$user_mailaddr}/g;
                s/{msg_too_long}/$text_strings{msg_too_long}/g;
                s/{msg_empty}/$text_strings{msg_empty}/g;
                s/{link_web_title}/$text_strings{link_web_title}/g;
                s/{link_send_btn}/$text_strings{link_send_btn}/g;
                s/{type_msg_below}/$text_strings{type_msg_below}/g;
                print $out $_;
            }
            close $in or die;
            chmod(0755,$LINK_PATH) or die;
            close $out or die;

            $linkgen_notif = qq{<span id="success">$text_strings{link_generated_ok}: <br><a target="_blank" rel="noopener noreferrer nofollow" href="$HREF_LINK">$HREF_LINK</a></span>};          
        }
        else{
            $mailisok_notif = qq{<span id="failure">$text_strings{addr} $link_asker $text_strings{addr_nok}</span>};
        }
    }
   

    opendir my $link_dir_handle, "./l/$userid" or die "Can't open ./l: $!";
    while (readdir $link_dir_handle) {
        if ($_ ne '.' and $_ ne '..'){
            my $linkfile_fn = $_;
            my $link_asker = undef;
            if (open my $linkfile_handle , '<', "./l/$userid/$linkfile_fn"){
                for (1..2){
                    $link_asker = readline $linkfile_handle;
                    $link_asker =~ s/q\{(.*?)\}//i;
                    $link_asker = $1;
                }
                close $linkfile_handle;
                
                if (not defined $link_asker){
                    $link_asker = $text_strings{unknown};
                }
                #create links table html
                push @created_links,
                qq{<tr>
                    <td><a href="/cgi-bin/l/$userid/$linkfile_fn" target="_blank" rel="noopener noreferrer nofollow">ici</a></td>
                    <td><a href="mailto:$link_asker?subject=$text_strings{mailto_subject}&body=$text_strings{mailto_body} http://$hostname/cgi-bin/l/$userid/$linkfile_fn">$link_asker</a></td>
                    <td>
                        <form method="POST">
                    	    $hidden_loginfield
                            <input type="hidden" name="supprlien" value="$linkfile_fn">
                            <input id="deletelinkbtn" type="submit" value="$text_strings{delete_link_btn_text}">
                        </form>
                    </td>
                </tr>};

            }
            else {
                close $linkfile_handle;
                die 'Content-type: text/plain', "\n\n", "Error: Can't open $linkfile_fn: $!";
            }
        }
    }
    closedir $link_dir_handle;
    print 'Content-type: text/html',"\n\n",
    qq{<!DOCTYPE html>
        <html> 
            <head> 
                <link rel="icon" sizes="48x48" type="image/ico" href="/favicon.ico">
                <link rel="stylesheet" type="text/css" href="/styles.css">
                <meta http-equiv="content-type" content="text/html;charset=UTF-8">
                <meta charset="UTF-8">
                <title>$text_strings{web_title}</title>
            </head>
            <body>
                <p>$text_strings{web_greet_msg} <b>$nick</b></p>
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
                    <input id="mailfied" tabindex="1" type="text" name="mail">
                    <input id="genlinkbtn" tabindex="2" type="submit" value="$text_strings{create_link_btn}">
                </form>},
                NotifIfDefined($mailisok_notif),
                '<br>',
                NotifIfDefined($linkgen_notif),
                qq{<hr>
                <form method="POST">
                    $hidden_loginfield
                    <input type="hidden" name="supprtout">
                    <input id="deleteallbtn" type="submit" value="$text_strings{delete_links_btn_text}">
                </form>},
                NotifIfDefined($deletion_notif),
                qq{<table>
                    <tr>
                        <th>$text_strings{theader_link} &#128279;</th>
                        <th>$text_strings{theader_for} &#128231;</th>
                        <th>$text_strings{theader_deletion} &#128465;</th>
                    </tr>
                    @created_links
                </table>
            </body>
        </html>};
}
else{
    $dbh->disconnect;
    print "Location: /\n\n";
}
