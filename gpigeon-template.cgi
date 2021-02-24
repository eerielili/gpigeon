#! /usr/bin/perl -wT

use warnings;
use strict;
use Crypt::Argon2 qw(argon2id_verify);
use Email::Valid;
use String::Random;
use CGI qw(param);
#use CGI::Carp qw(fatalsToBrowser);

sub escape_arobase {
    my $mailaddress = shift;
    my $arobase = '@';
    my $espaced_arob = q{\@};
    my $escapedmailaddress = $mailaddress;
    $escapedmailaddress =~ s/$arobase/$espaced_arob/;
    return $escapedmailaddress;
}

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

delete @ENV{qw(IFS PATH CDPATH BASH_ENV)};
$ENV{'PATH'} = '/usr/bin';
my $HAS_MAILSERVER = 0;
my $SRV_NAME = $ENV{'SERVER_NAME'};	
my $HTML_CONTENT_TYPE_HEADER    = 'Content-type: text/html';
my $HTML_CHARSET = 'UTF-8';
my $HTML_CSS = '/gpigeon.css';
my $mymailaddr = q{your_mail_address_goes_here};
my $mymailaddr_pw = q{your_mail_address_password_goes_here};
my $mymail_smtp = q{smtp_domain_goes_here};
my $mymail_smtport = q{smtp_port_goes_here};
my $mymail_gpgid = q{gpgid_goes_here}; #0xlong keyid form
my $PASSWD_HASH = q{password_hash_goes_here}; #argon2id hash please
my $mymailaddr_escaped = escape_arobase($mymailaddr);
my $msg_form_char_limit = 3000; 
my %text_strings = (link_del_ok => 'Successful removal !',
    addr => 'Address', 
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
my ($notif_de_creation, $notif_mail_valide, $notif_suppression) = undef;
my @created_links = ();


if (argon2id_verify($PASSWD_HASH,$PASSWD)){

        my $psswd_formfield = '<input type="hidden" name="password" value="' . $cgi_query_get->param('password') . '">';
    if (defined $cgi_query_get->param('supprlien')){
        my $pending_deletion = $cgi_query_get->param('supprlien');
        my $gpg_form_fn = "./l/$pending_deletion";
        if (unlink untaint_cgi_filename($gpg_form_fn)){ 
            $notif_suppression=qq{<span style="color:green">$text_strings{link_del_ok}</span>};
        }
        else {
            $notif_suppression=qq{<span style="color:red">$text_strings{link_del_failed} $gpg_form_fn : $!</span>};
        }
    }

    if (defined $cgi_query_get->param('supprtout')){
        opendir my $link_dir_handle, './l' or die "Can't open ./l: $!";

        while (readdir $link_dir_handle) {
            if ($_ ne '.' and $_ ne '..'){
                my $gpg_form_fn = "./l/$_";
                unlink untaint_cgi_filename($gpg_form_fn) or die "$!";
                $notif_suppression=qq{<span style="color:green">$text_strings{link_del_ok}</span>};
            }
        }
        closedir $link_dir_handle;
    }

    if (defined $cgi_query_get->param('mail')){
        my $non_gpguser = scalar $cgi_query_get->param('mail');

        if ( Email::Valid->address($non_gpguser) ){
            $notif_mail_valide = qq{<span style="color:green">$text_strings{addr} $non_gpguser $text_strings{addr_ok}</span>};
            my $escaped_non_gpguser = escape_arobase($non_gpguser);
            my $random_mailform_fn_str = String::Random->new;
            my @mailform_fn_str_buffer = ();

            for (1..5){
                push @mailform_fn_str_buffer,
                     $random_mailform_fn_str->randregex('\w{64}');
            }

            my $mailform_fn_str_buffer_nospace = join('',@mailform_fn_str_buffer);
            my $GENERATED_FORM_FILENAME = "$mailform_fn_str_buffer_nospace.cgi";
            my $MAILFORM_LINK   	 = "http://$SRV_NAME/cgi-bin/l/$GENERATED_FORM_FILENAME";
            my $MAILFORM_RELPATH 	 =  "./l/$GENERATED_FORM_FILENAME";
            if (open my $gpg_form_fh, ">", $MAILFORM_RELPATH){ 
                print $gpg_form_fh '#! /usr/bin/perl -wT',"\n\n",
                ' my $non_gpguser = q{'. $non_gpguser .'};', "\n",
		        'delete @ENV{qw(IFS PATH CDPATH BASH_ENV)};', "\n",
                '$ENV{\'PATH\'}="/usr/bin";', "\n",
                'use warnings;', "\n",
                'use strict;',"\n",
                'use GPG;',"\n",
                '#use CGI::Carp qw(fatalsToBrowser);', "\n", 
                'use CGI qw(param);', "\n",
		        'my $cgi_query_get = CGI->new;', "\n",
                'my ($msg_form, $enc_msg, $error_processing_msg,$msg_form_char_limit) = undef;', "\n",
                '$msg_form_char_limit = '. $msg_form_char_limit . ' ;', "\n",
                '$msg_form = $cgi_query_get->param(\'msg\');', "\n",
                'my $length_msg_form = length $msg_form;', "\n",
               
                'if (defined $length_msg_form and $length_msg_form > $msg_form_char_limit){', "\n",
                '    $error_processing_msg = q{<span style="color:red"><b>'. $text_strings{msg_too_long} .'.</b></span>};', "\n",
                '} elsif (defined $length_msg_form and $length_msg_form eq 0 ){', "\n",
                '    $error_processing_msg = q{<span style="color:red"><b>'.  $text_strings{msg_empty} . '.</b></span>};', "\n",
                '} else {', "\n",
                '    if (defined $length_msg_form and $ENV{\'REQUEST_METHOD\'} eq \'POST\'){',"\n",
                '       $msg_form =~ tr/\r//d;', "\n",
                '       my $gpg =  new GPG(gnupg_path => "/usr/bin", homedir => "/usr/share/www-data/.gnupg/");', "\n",
                '       $enc_msg = $gpg->encrypt("De la part de " . $non_gpguser . ":\n". $msg_form, \''. $mymail_gpgid  .'\') or die $gpg->error();', "\n";
                if ($HAS_MAILSERVER){
                    undef $mymailaddr_escaped;
                    print $gpg_form_fh "\n",
                '        use Mail::Sendmail;', "\n",
                '        my %mail = ( To => \''.$mymailaddr.'\', ', "\n",
                '                  From => \''.$mymailaddr.'\',  ', "\n",
                '                  Subject => \'Gpigeon\', ', "\n",
                '                  Message => "$enc_msg\n" ', "\n",
                '        );', "\n",
                '        sendmail(%mail) or die $Mail::Sendmail::error;', "\n";
                }
                else {
                    print $gpg_form_fh "\n",
                '        use Net::SMTP;',"\n",
                '        use Net::SMTPS;',"\n",
                '        my $smtp = Net::SMTPS->new(\''. $mymail_smtp  .'\', Port => \''. $mymail_smtport .'\', doSSL => \'ssl\', Debug_SSL => 0);', "\n", 
                '        $smtp->auth(\''. $mymailaddr .'\', \''. $mymailaddr_pw  .'\') or die;', "\n",
                '        $smtp->mail(\''. $mymailaddr .'\') or die "Net::SMTP module has broke: $!.";', "\n",
                '        if ($smtp->to(\''. $mymailaddr .'\')){', "\n",
                '           $smtp->data();', "\n",
                '           $smtp->datasend("To: '. $mymailaddr_escaped .'\n");', "\n",
                '           $smtp->datasend("\n");', "\n",
                '           $smtp->datasend("$enc_msg\n");', "\n",
                '           $smtp->dataend();', "\n",
                '        }', "\n",
                '        else {', "\n",
                '           die $smtp->message();', "\n",
                '        }', "\n";
                }
                print $gpg_form_fh "\n",
                '        unlink "../' . $MAILFORM_RELPATH . '";', "\n",
                '        print "Location: /merci/index.html\n\n";', "\n", 
                '    }', "\n",
                '}', "\n",
                'print "Content-type: text/html", "\n\n";', "\n",
                'print q{<!DOCTYPE html>', "\n",
                '<html>', "\n",
                '    <head>', "\n",
                '       <link rel="icon" sizes="48x48" type="image/ico" href="/favicon.ico">', "\n",
                '       <link rel="stylesheet" type="text/css" href="'. $HTML_CSS .'">',
                '       <meta http-equiv="content-type" content="text/html;charset='. $HTML_CHARSET .'">',"\n",'<meta charset="'. $HTML_CHARSET .'">',"\n",
		        '       <title>Formulaire d\'envoi de message GPG</title>',"\n",
                '    </head>', "\n",
                '    <body>', "\n",
                '        <p>'. $text_strings[7] . '<b>' . $non_gpguser .'</b> :</p>', "\n",
                '            <form method="POST">', "\n",
                '                <textarea wrap="off" cols="50" rows="30" name="msg"></textarea><br>',
                '};', "\n",
                'if (defined $error_processing_msg){printf $error_processing_msg;}', "\n",
                'printf qq{     <br>
                                <input type="submit" value="'. $text_strings{link_send_btn} .'">', "\n",
                '            </form>', "\n",
                '    </body>', "\n",
                '</html> };';
            close $gpg_form_fh;
            chmod(0755,$MAILFORM_RELPATH);
            $notif_de_creation=qq{<span style="color:green">$text_strings{link_generated_ok} $non_gpguser: </span><br><a href="$MAILFORM_LINK">$MAILFORM_LINK</a>};          }
          else{
		      close $gpg_form_fh and die "Can't open $MAILFORM_RELPATH: $!";
          }
        }
        else{
            $notif_mail_valide = qq{<span style="color:red">$text_strings{addr} $non_gpguser $text_strings{addr_nok}.</span>};
        }
    }
    
    opendir my $link_dir_handle, './l' or die "Can't open ./l: $!";

    while (readdir $link_dir_handle) {
        if ($_ ne '.' and $_ ne '..'){
            my $gpg_form_fn = $_;
            my $non_gpguser = undef;
            if (open my $gpg_form_handle , '<', "./l/$gpg_form_fn"){
            
                for (1..3){
                    $non_gpguser = readline $gpg_form_handle;
                    $non_gpguser =~ s/q\{(.*?)\}//i;
                    $non_gpguser = $1;
                }
                close $gpg_form_handle;
                
                if (not defined $non_gpguser){
                    $non_gpguser = $text_strings[4];
                }
                
                #create links table html
                push @created_links,
                qq{<tr>
                    <td><a href="/cgi-bin/l/$gpg_form_fn">ici</a></td>
                    <td><a href="mailto:$non_gpguser?subject=$text_strings{mailto_subject}&body=$text_strings{mailto_body} http://$SRV_NAME/cgi-bin/l/$gpg_form_fn">$non_gpguser</a></td>
                    <td>
                        <form method="POST">
                            <input type="hidden" name="supprlien" value="$gpg_form_fn">
                            <input type="hidden" name="password" value="$cgi_query_get->param('password')">
                            <input type="submit" value="$text_strings{delete_link_btn}">
                        </form>
                    </td>
                </tr>};

            }
            else {
                close $gpg_form_handle;
                die 'Content-type: text/plain', "\n\n", "Error: Can't open $gpg_form_fn: $!";
            }
        }
    }
    closedir $link_dir_handle;

    print $HTML_CONTENT_TYPE_HEADER,"\n\n",
    qq{<!DOCTYPE html>
        <html> 
            <head> 
                <link rel="icon" sizes="48x48" type="image/ico" href="/favicon.ico">
                <link rel="stylesheet" type="text/css" href="$HTML_CSS">
                <meta http-equiv="content-type" content="text/html;charset=$HTML_CHARSET">
                <meta charset="$HTML_CHARSET">
                <title>$text_strings{web_title}</title>
            </head>
            <body>
                <p>$text_strings{web_greet_msg}</p>
                <form method="POST">
                    <input type="hidden" name="password" value="0">
                    <input type="submit" value="$text_strings{disconnect_btn_text}">
                </form>
                <form method="POST">
                $psswd_formfield
                   <input type="submit" value="$text_strings{refresh_btn_text}">
                </form>
                <hr>
                <br>
                <form method="POST">
                    $psswd_formfield
                    Mail de la personne:<br>
                    <input tabindex="1" type="text" name="mail">
                    <input tabindex="2" type="submit" value="$text_strings{create_link_btn}">
                </form>},
                notif_if_defined($notif_mail_valide),
                '<br>'
                notif_if_defined($notif_de_creation),
                qq{<hr>
                <form method="POST">
                    $psswd_formfield
                    <input type="hidden" name="supprtout">
                     <input type="submit" value="$text_strings{delete_links_btn_text}">
                </form>},
                notif_if_defined($notif_suppression),
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
