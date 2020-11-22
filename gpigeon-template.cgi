#! /usr/bin/perl -wT

use warnings;
use strict;
use Digest::SHA qw(sha256_hex);
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
}

delete @ENV{qw(IFS PATH CDPATH BASH_ENV)};
# execute  'printf "yourpassword" | sha256sum' on a terminal
# and copy the long string
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
my $PASSWD_HASH = q{password_hash_goes_here};
my $mymailaddr_escaped = escape_arobase($mymailaddr);
my $msg_form_char_limit = 3000; 
my @text_strings = ('Succesfull deletion!',
    'Address', 
    'is valid!', 
    'is not valid !',
    'Unknown', # displays on main page table when supposed sender isn't identified
    'Message length must be under$msg_form_char_limit chars.',
    'One time GPG messaging form', # title for generated links
    'Type your message below, ',
    'Send to me',
    'Generated a link for', #displays if link gen is successful
    'Link to your one time GPG messaging form', # mail subject when clicking a mailto: link in table
    'Your link is ', # message body when clicking a mailto: link in table
    'Delete', # text on button for deleting links
    'Damn! I cannot open ', # message when file opening fails
    'GPIGEON.CGI: generate one time GPG messaging links !', # main page title!
    'Hi and welcome.', # a greeting at the top of the main page.
    'Disconnect', # disconnect button text on main page
    'Refresh', # refresh button text
    'Generate link', #link generation button text
    "Generated links by you, <b>$mymailaddr</b>:", # label above links table
    'Delete all links', # delete all links button text
    'Link', # first table header, 'Link'
    'For', # second table header, 'For'
    'Deletion', # third table header, 'Delete'
    'Deletion failed and here is why : ',
    'Cannot send message : message length must be under ' .$msg_form_char_limit . ' characters.',
    'Cannot send message : message is empty. You can type up to ' . $msg_form_char_limit . ' characters.'
);
my $cgi_query_get = CGI->new;
my $PASSWD = $cgi_query_get->param('password');
my $psswd_formfield = '<input type="hidden" name="password" value="' . $cgi_query_get->param('password') . '">';
my ($notif_de_creation, $notif_mail_valide, $notif_suppression) = undef;
my @created_links = ();


if ( sha256_hex($PASSWD) eq $PASSWD_HASH and $ENV{'REQUEST_METHOD'} eq 'POST'){

    if (defined $cgi_query_get->param('supprlien')){
        my $pending_deletion = $cgi_query_get->param('supprlien');
        my $gpg_form_fn = "./l/$pending_deletion";
        if (unlink untaint_cgi_filename($gpg_form_fn)){ 
            $notif_suppression='<span style="color:green">'.$text_strings[0].'</span>';
        }
        else {
            $notif_suppression='<span style="color:red">'. $text_strings[24] . $gpg_form_fn.':'. $! .'</span>';
        }
    }

    if (defined $cgi_query_get->param('supprtout')){
        opendir my $link_dir_handle, './l' or die "Can't open ./l: $!";

        while (readdir $link_dir_handle) {
            if ($_ ne '.' and $_ ne '..'){
                my $gpg_form_fn = "./l/$_";
                unlink untaint_cgi_filename($gpg_form_fn) or die "$!";
                $notif_suppression='<span style="color:green">'. $text_strings[0] .'</span>';
            }
        }
        closedir $link_dir_handle;
    }

    if (defined $cgi_query_get->param('mail')){
        my $non_gpguser = scalar $cgi_query_get->param('mail');

        if ( Email::Valid->address($non_gpguser) ){
            $notif_mail_valide = '<span style="color:green">'. $text_strings[1] . ' '. $non_gpguser.' '. $text_strings[2] . '</span>';
            my $escaped_non_gpguser = escape_arobase($non_gpguser);
            my $random_mailform_fn_str = String::Random->new;
            my @mailform_fn_str_buffer = ();

            for (1..5){
                push @mailform_fn_str_buffer,
                     $random_mailform_fn_str->randregex('\w{1,15}[0-9]{1,15}');
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
                '    $error_processing_msg = q{<span style="color:red"><b>'. $text_strings[25] .'.</b></span>};', "\n",
                '} elsif (defined $length_msg_form and $length_msg_form eq 0 ){', "\n",
                '    $error_processing_msg = q{<span style="color:red"><b>'. $text_strings[26] . '.</b></span>};', "\n",
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
                                <input type="submit" value="'. $text_strings[8] .'">', "\n",
                '            </form>', "\n",
                '    </body>', "\n",
                '</html> };';
            close $gpg_form_fh;
            chmod(0755,$MAILFORM_RELPATH);
            $notif_de_creation='<span style="color:green">'. $text_strings[9] . $non_gpguser .'</span><br><a href="'. $MAILFORM_LINK .'">'. $MAILFORM_LINK .'</a>';
          }
          else{
		      close $gpg_form_fh and die "Can't open $MAILFORM_RELPATH: $!";
          }
        }
        else{
            $notif_mail_valide = "<span style='color:red'>$text_strings[1] $non_gpguser $text_strings[3].</span>";
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
                '<tr>
                    <td><a href="/cgi-bin/l/'. $gpg_form_fn .'">ici</a></td>
                    <td><a href="mailto:'. $non_gpguser .'?subject='. $text_strings[10] .'&body='. $text_strings[11] .'http://$SRV_NAME/cgi-bin/l/'. $gpg_form_fn .'">'.$non_gpguser.'</a></td>
                    <td>
                        <form method="POST">
                            <input type="hidden" name="supprlien" value="'. $gpg_form_fn .'">
                            <input type="hidden" name="password" value="'. $cgi_query_get->param('password') .'">
                            <input type="submit" value="'. $text_strings[12] .'">
                        </form>
                    </td>
                </tr>';

            }
            else {
                close $gpg_form_handle;
                die 'Content-type: text/plain', "\n\n", "$text_strings[13] $gpg_form_fn: $!";
            }
        }
    }
    closedir $link_dir_handle;

    print $HTML_CONTENT_TYPE_HEADER,"\n\n",
    '<!DOCTYPE html>
        <html> 
            <head> 
                <link rel="icon" sizes="48x48" type="image/ico" href="/favicon.ico">
                <link rel="stylesheet" type="text/css" href="'. $HTML_CSS .'">
                <meta http-equiv="content-type" content="text/html;charset='. $HTML_CHARSET .'">',"\n",'<meta charset="'. $HTML_CHARSET  .'">
                <title>'. $text_strings[14] .'</title>
            </head>
            <body>
                <p>'. $text_strings[15] .'</p>
                <form method="POST">
                    <input type="hidden" name="password" value="0">
                    <input type="submit" value="'. $text_strings[16] .'">
                </form>
                <form method="POST">',
                $psswd_formfield,
                   '<input type="submit" value="'. $text_strings[17]  .'">
                </form>
                <hr>
                <br>
                <form method="POST">', 
                    $psswd_formfield,
                    'Mail de la personne:<br>
                    <input tabindex="1" type="text" name="mail">
                    <input tabindex="2" type="submit" value="'. $text_strings[18] .'">
                </form>';
                print notif_if_defined($notif_mail_valide);
                print '<br>';
                print notif_if_defined($notif_de_creation);
                print '<hr>
                <p>'. $text_strings[19]  .'</p>',
                '<form method="POST">',
                    $psswd_formfield,
                    '<input type="hidden" name="supprtout">
                     <input type="submit" value="'. $text_strings[20] .'">
                </form>', 
                notif_if_defined($notif_suppression),
                '<table>
                    <tr>
                        <th>'. $text_strings[21]  .'</th>',
                        '<th>'. $text_strings[22]  .'</th>', 
                        '<th>'. $text_strings[23]  .'</th>', 
                    '</tr>',
                    "@created_links",
                '</table>
            </body>
        </html>';
}
else {
    print 'Location: /index.html', "\n\n";
}
