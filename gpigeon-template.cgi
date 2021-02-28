#! /usr/bin/perl -wT

use warnings;
use strict;
use Crypt::Argon2 qw(argon2id_verify);
use Email::Valid;
use String::Random;
use CGI qw(param);
use CGI::Carp qw(fatalsToBrowser);

sub untaint_cgi_filename {
    my $filename = shift;
    if ($filename =~ /^([-\@\w.\/]+)$/) {
        #data untainted
        $filename = $1;
    }
    else {
        die "$!";
    }
    chomp $filename;
    return $filename;
}

sub notif_if_defined{
    my $notif = shift;
    if (defined $notif){
        return $notif;
    }
    else{
        return '<!-- undef -->';
    }
}

delete @ENV{qw(IFS PATH CDPATH BASH_ENV)};
$ENV{'PATH'} = '/usr/bin';
my $HOSTNAME = $ENV{'SERVER_NAME'};	
my $LINK_TEMPLATE_PATH='/usr/share/webapps/gpigeon/link-template.pl'; # this is the file where the SMTP and mail address values goes
my $msg_form_char_limit = 3000;
my $PASSWD_HASH = q{password_hash_goes_here}; #argon2id hash format
my %text_strings = (link_del_ok => 'Successful removal !',
    addr => 'Address', 
    here => 'here',
    addr_ok => 'is valid!', 
    addr_nok => 'is not valid !',
    addr_unknown => 'Unknown',
    link_web_title => 'One time GPG messaging form',
    link_legend_textarea =>'Type your message below :',
    link_send_btn => 'Send',
    link_generated_ok => 'Generated a link for',
    mailto_body => 'Your link is ',
    mailto_subject => 'Link to your one time GPG messaging form',
    delete_link_btn_text => 'Delete',
    delete_links_btn_text => 'Delete all links',
    create_link_btn => 'Generate link', 
    web_title => 'GPIGEON.CGI: generate one time GPG messaging links !', 
    web_greet_msg => 'Hi and welcome.', 
    disconnect_btn_text => 'Disconnect',
    refresh_btn_text => 'Refresh',
    type_msg_below => 'Type your message below',
    theader_link => 'Link', 
    theader_for => 'For', 
    theader_deletion => 'Deletion', 
    link_del_failed => 'Deletion failed and here is why : ',
    msg_too_long => 'Cannot send message : message length must be under ' .$msg_form_char_limit . ' characters.',
    msg_empty => 'Cannot send message : message is empty. You can type up to ' . $msg_form_char_limit . ' characters.',
    notif_login_failure => 'Cannot login. Check if your username and password match.'
);
my $cgi_query_get = CGI->new;
my $PASSWD = $cgi_query_get->param('password');
my ($linkgen_notif, $mailisok_notif, $deletion_notif) = undef;
my @created_links = ();


if (argon2id_verify($PASSWD_HASH,$PASSWD)){

    my $hidden_pwfield = '<input type="hidden" name="password" value="' . $PASSWD . '">';
    if (defined $cgi_query_get->param('supprlien')){
        my $pending_deletion = $cgi_query_get->param('supprlien');
        my $linkfile_fn = "./l/$pending_deletion";
        if (unlink untaint_cgi_filename($linkfile_fn)){ 
            $deletion_notif=qq{<span style="color:green">$text_strings{link_del_ok}</span>};
        }
        else {
            $deletion_notif=qq{<span style="color:red">$text_strings{link_del_failed} $linkfile_fn : $!</span>};
        }
    }

    if (defined $cgi_query_get->param('supprtout')){
        opendir my $link_dir_handle, './l' or die "Can't open ./l: $!";
        while (readdir $link_dir_handle) {
            if ($_ ne '.' and $_ ne '..'){
                my $linkfile_fn = "./l/$_";
                unlink untaint_cgi_filename($linkfile_fn) or die "$!";
                $deletion_notif=qq{<span style="color:green">$text_strings{link_del_ok}</span>};
            }
        }
        closedir $link_dir_handle;
    }

    if (defined $cgi_query_get->param('mail')){
        my $link_asker = scalar $cgi_query_get->param('mail');

        if ( Email::Valid->address($link_asker) ){
            $mailisok_notif = qq{<span style="color:green">$text_strings{addr} $link_asker $text_strings{addr_ok}</span>};
            my $escaped_link_asker = escape_arobase($link_asker);
            my $str_rand_obj = String::Random->new;
            my $random_fn = $str_rand_obj->randregex('\w{64}');
            my $GENERATED_FORM_FILENAME = "$random_fn.cgi";
            my $HREF_LINK   	 = "https://$HOSTNAME/cgi-bin/l/$GENERATED_FORM_FILENAME";
            my $LINK_FILENAME 	 =  "./l/$GENERATED_FORM_FILENAME";

            open my $in, '<', $LINK_TEMPLATE_PATH or die "Can't read link template file: $!";
            open my $out, '>', $LINK_FILENAME or die "Can't write to link file: $!";
            while( <$in> ) {
                s/{link_user}/{$link_asker}/g;
                s/{link_filename}/{$GENERATED_FORM_FILENAME}/g;
                s/{msg_too_long}/$text_strings{msg_too_long}/g;
                s/{msg_empty}/$text_strings{msg_empty}/g;
                s/{msg_form_char_limit}/$msg_form_char_limit/g;
                s/{link_web_title}/$text_strings{link_web_title}/g;
                s/{link_send_btn}/$text_strings{link_send_btn}/g;
                s/{type_msg_below}/$text_strings{type_msg_below}/g;
                print $out $_;
            }
            close $in or die;
            chmod(0755,$LINK_FILENAME) or die;
            close $out or die;

            $linkgen_notif = qq{<span style="color:green">$text_strings{link_generated_ok} $link_asker: </span><br><a href="$HREF_LINK">$HREF_LINK</a>};          
        }
        else{
            $mailisok_notif = qq{<span style="color:red">$text_strings{addr} $link_asker $text_strings{addr_nok}.</span>};
        }
    }
   

    opendir my $link_dir_handle, './l' or die "Can't open ./l: $!";
    while (readdir $link_dir_handle) {
        if ($_ ne '.' and $_ ne '..'){
            my $linkfile_fn = $_;
            my $link_asker = undef;
            if (open my $linkfile_handle , '<', "./l/$linkfile_fn"){
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
                    <td><a href="/cgi-bin/l/$linkfile_fn">ici</a></td>
                    <td><a href="mailto:$link_asker?subject=$text_strings{mailto_subject}&body=$text_strings{mailto_body} http://$HOSTNAME/cgi-bin/l/$linkfile_fn">$link_asker</a></td>
                    <td>
                        <form method="POST">
                            <input type="hidden" name="supprlien" value="$linkfile_fn">
                            <input type="hidden" name="password" value="$PASSWD">
                            <input type="submit" value="$text_strings{delete_link_btn_text}">
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
                <p>$text_strings{web_greet_msg}</p>
                <form method="POST">
                    <input type="hidden" name="password" value="0">
                    <input type="submit" value="$text_strings{disconnect_btn_text}">
                </form>
                <form method="POST">
                $hidden_pwfield
                   <input type="submit" value="$text_strings{refresh_btn_text}">
                </form>
                <hr>
                <br>
                <form method="POST">
                    $hidden_pwfield
                    Mail de la personne:<br>
                    <input tabindex="1" type="text" name="mail">
                    <input tabindex="2" type="submit" value="$text_strings{create_link_btn}">
                </form>},
                notif_if_defined($mailisok_notif),
                '<br>'
                notif_if_defined($linkgen_notif),
                qq{<hr>
                <form method="POST">
                    $hidden_pwfield
                    <input type="hidden" name="supprtout">
                     <input type="submit" value="$text_strings{delete_links_btn_text}">
                </form>},
                notif_if_defined($deletion_notif),
                qq{<table>
                    <tr>
                        <th>$text_strings{theader_link}</th>
                        <th>$text_strings{theader_for}</th>
                        <th>$text_strings{theader_deletion}</th>
                    </tr>
                    @created_links
                </table>
            </body>
        </html>};
}
else {
    print 'Location: /index.html', "\n\n";
}
