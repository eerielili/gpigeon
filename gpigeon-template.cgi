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
use Crypt::Argon2 qw(argon2id_verify);
use Email::Valid;
use String::Random;
use CGI qw(param);
use CGI::Cookie;
use CGI::Carp qw(fatalsToBrowser);

delete @ENV{qw(IFS PATH CDPATH BASH_ENV)};
$ENV{'PATH'} = q{bin_path_goes_here};
my $uagent = $ENV{HTTP_USER_AGENT};
my $rIP = $ENV{REMOTE_ADDR};
my $hostname = $ENV{'SERVER_NAME'};

sub ValidCookie {
    my $client_login_cookie = shift;
    if (not defined $client_login_cookie){
        return;
    }
    my $dir = shift;
    my $filename = $client_login_cookie->value;
    my $login_cookiefile = "$dir/$filename.txt";

    if ($filename =~ /^([\w]+)$/){
	    $filename = $1;
    }
    else{
	    return;
    }

    if (-e $login_cookiefile){ 
        open my $in, '<', $login_cookiefile or die "can't read file: $!";
        my $rip_line = readline $in;
        my $ua_line = readline $in;
        my $cookie_line = readline $in;
        close $in;
        chomp ($rip_line, $ua_line);
        if (not defined $cookie_line){
            return;
        }
        my %magic_cookie = CGI::Cookie->parse($cookie_line) or die "$!";
        my $magic_cookie_val = $magic_cookie{'id'}->value;
   
        my $rip_match = $rip_line cmp $rIP;
        my $ua_match = $ua_line cmp $uagent;
        my $magic_match = $magic_cookie_val cmp $client_login_cookie->value; 

        if ($rip_match == 0 and $ua_match == 0 and $magic_match == 0){
            return 1;
        }
    }
    else{
        return;
    }
    return;
}

sub LoginCookieGen {
    my $id_cookie = shift;
    my $dir = shift;
    if (not defined $id_cookie){
        if (not -d "$dir"){
            mkpath("$dir") or die "$!";
        }
        my $str_rand_obj = String::Random->new;
        my $val = $str_rand_obj->randregex('\w{64}');
        my $cookiefile = "$dir/$val.txt";
        my $new_login_cookie = CGI::Cookie->new(
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
       open my $out, '>', $cookiefile or die "Can't write to $cookiefile: $!";
       print $out "$rIP\n$uagent\n$new_login_cookie";
       close $out;
       print "Set-Cookie: $new_login_cookie\n";
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

my ( $link_asker, $checkedornot, $hidden_pwfield, $id_cookie, 
    $delete_id_cookie, $idval, $refresh_form) = undef;
my $linkgen_notif = my $mailisok_notif = my $deletion_notif = my $login_notif = '<!-- undef notif -->';
my @created_links = ();

my $argon2id_hash       = qq{argon2id_hash_goes_here};
my $cookies_dir         = q{cookies_dir_goes_here};
my $link_template_path  = q{link_template_path_goes_here};

my %text_strings = (
    addr => 'Address', 
    addr_ok => 'is valid!', 
    addr_nok => 'is not valid !',
    addr_unknown => 'Unknown',
    create_link_btn => 'Generate link', 
    delete_link_btn_text => 'Delete',
    delete_links_btn_text => 'Delete all links',
    here => 'here',
    landingpage_title => 'GPIGEON - Login',
    link_asker_field_label => q{Asker's mail :},
    link_del_ok => 'Successful removal !',
    link_ok_for => 'Generated a link for',
    link_del_failed => 'Deletion failed and here is why : ',
    loginbtn => 'Log in',
    logout_btn_text => 'Logout',
    mailto_body => 'Your link is ',
    mailto_subject => 'Link to your one time GPG messaging form',
    mainpage_title => 'GPIGEON - Main',
    notif_login_failure => 'Cannot login. Check if your username and password match.',
    refresh_btn_text => 'Refresh',
    theader_link => 'Link', 
    theader_for => 'For', 
    theader_deletion => 'Deletion', 
    web_greet_msg => 'Hi and welcome.', 
);
my $cgi_query_get = CGI->new;
my $pw = $cgi_query_get->param('password');
my $logout = $cgi_query_get->param('logout');
my %cur_cookies = CGI::Cookie->fetch;
$id_cookie = $cur_cookies{'id'};

if (not defined $id_cookie){
    $hidden_pwfield = qq{<input type="hidden" name="password" value="$pw">};
    $refresh_form = qq{<form method="POST">
                   $hidden_pwfield
                   <input id="refreshbtn" type="submit" value="$text_strings{refresh_btn_text}">
                </form>};
}
else{
    $hidden_pwfield = '<!-- undef -->';
    $refresh_form = qq{<form method="GET">
                   <input id="refreshbtn" type="submit" value="$text_strings{refresh_btn_text}">
                </form>};
    $idval = $id_cookie->value;

    if ($idval =~ /^([\w]+)$/){
        $idval = $1;
    }

    if ($logout){
        $delete_id_cookie = CGI::Cookie->new(
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
        my $f = "$cookies_dir/$idval.txt";
        if (-e "$f"){
            unlink "$f" or die "Can't delete file :$!";
        }
        print "Set-Cookie: $delete_id_cookie\n";
    }
}

print "Cache-Control: no-store, must-revalidate\n";
if (ValidCookie($id_cookie, $cookies_dir) or argon2id_verify($argon2id_hash,$pw)){
    
    LoginCookieGen($id_cookie, $cookies_dir);
    
    if (defined $cgi_query_get->param('supprlien')){
        my $pending_deletion = $cgi_query_get->param('supprlien');
        my $linkfile_fn = "./l/$pending_deletion";
        if (unlink UntaintCGIFilename($linkfile_fn)){ 
            $deletion_notif = qq{<span id="success">$text_strings{link_del_ok}</span>};
        }
        else {
            $deletion_notif = qq{<span id="failure">$text_strings{link_del_failed} $linkfile_fn : $!</span>};
        }
    }

    if (defined $cgi_query_get->param('supprtout')){
        rmtree('./l', {keep_root => 1, safe => 1});
        $deletion_notif = qq{<span id="success">$text_strings{link_del_ok}</span>};
    }

    if (defined $cgi_query_get->param('mail')){
        $link_asker = scalar $cgi_query_get->param('mail');

        if ( Email::Valid->address($link_asker) ){
            $mailisok_notif = qq{<span id="success">$text_strings{addr} $link_asker $text_strings{addr_ok}</span>};
            my $str_rand_obj = String::Random->new;
            my $generated_form_filename = $str_rand_obj->randregex('\w{64}') . '.cgi';
            my $href = "https://$hostname/cgi-bin/l/$generated_form_filename";
            my $link_path 	 =  "./l/$generated_form_filename";

            open my $in, '<', $link_template_path or die "Can't read link template file: $!";
            open my $out, '>', $link_path or die "Can't write to link file: $!";
            while( <$in> ) {
                s/{link_user}/{$link_asker}/g;
                print $out $_;
            }
            close $in or die;
            chmod(0755,$link_path) or die;
            close $out or die;
            $linkgen_notif = qq{<span id="success">$text_strings{link_ok_for} $link_asker: </span><br><a target="_blank" rel="noopener noreferrer nofollow" href="$href">$href</a>};          
        }
        else{
            $mailisok_notif = qq{<span id="failure">$text_strings{addr} $link_asker $text_strings{addr_nok}.</span>};
        }
    }

    opendir my $link_dir_handle, './l' or die "Can't open ./l: $!";
    while (readdir $link_dir_handle) {
        if ($_ ne '.' and $_ ne '..'){
            my $linkfile_fn = $_;
            if (open my $linkfile_handle , '<', "./l/$linkfile_fn"){
                for (1..2){
                    $link_asker = readline $linkfile_handle;
                    $link_asker =~ s/q\{(.*?)\}//i;
                    $link_asker = $1;
                }
                close $linkfile_handle;
                
                if (Email::Valid->address($link_asker)){
                    push @created_links,
                    qq{<tr>
                        <td><a target="_blank" rel="noopener noreferrer nofollow" href="/cgi-bin/l/$linkfile_fn">$text_strings{here}</a></td>
                        <td><a href="mailto:$link_asker?subject=$text_strings{mailto_subject}&body=$text_strings{mailto_body} http://$hostname/cgi-bin/l/$linkfile_fn">$link_asker</a></td>
                        <td>
                            <form method="POST">
                                $hidden_pwfield
                                <input type="hidden" name="supprlien" value="$linkfile_fn">
                                <input id="deletelinkbtn" type="submit" value="$text_strings{delete_link_btn_text}">
                            </form>
                        </td>
                    </tr>};
                }
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
                <title>$text_strings{mainpage_title}</title>
            </head>
            <body>
                <h1>$text_strings{mainpage_title}</h1>
                <p>$text_strings{web_greet_msg}</p>
                <form method="GET">
                    <input type="hidden" name="logout" value="1">
                    <input id="logoutbtn" type="submit" value="$text_strings{logout_btn_text}">
                </form>
                $refresh_form
                <hr>
                <br>
                <form method="POST">
                    $hidden_pwfield
                    $text_strings{link_asker_field_label}<br>
                    <input id="mailfield" tabindex="1" type="text" name="mail">
                    <input id="genlinkbtn" tabindex="2" type="submit" value="$text_strings{create_link_btn}">
                </form>
                $mailisok_notif
                <br>
                $linkgen_notif
                <hr>
                <form method="POST">
                    $hidden_pwfield
                    <input type="hidden" name="supprtout">
                     <input id="deleteallbtn" type="submit" value="$text_strings{delete_links_btn_text}">
                </form>
                $deletion_notif
                <table>
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
    if (not $logout and defined $id_cookie){
        $login_notif = q{<span id="failure">You got a cookie problem.<br>
        <b>Clean them and log again</b></span>};
    }
    if (length($pw) > 0){
        $login_notif = q{<span id="failure">Your typed password seems<br>
        to be incorrect.<br>Try again.</span>};
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
			  <td>Password :</td> 		  
			  <td><input type="password" name="password"></td>
		  </tr>
          <tr>
                <td></td>
                <td id="loginerr">$login_notif</td>
          </tr>
		  <tr id="authbtn">
			  <td></td>
			  <td><input type="submit" value="$text_strings{loginbtn}"></td>
		  </tr>
	  </tbody>
  </table>
 </form>

<p><a href="http://git.les-miquelots.net/gpigeon"
	   title="gpigeon download link">Source code here.</a> It is similar to <a href="https://hawkpost.co/">hawkpost.co</a>.</p>

</body>
</html>};
}
