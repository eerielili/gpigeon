#! /usr/bin/perl -wT

use Digest::SHA qw(sha256_hex);
use warnings;
use strict;
use Email::Valid;
use String::Random;
use CGI qw(param);
#use CGI::Carp qw(fatalsToBrowser);

delete @ENV{qw(IFS PATH CDPATH BASH_ENV)};

sub escape_arobase {
    my $mailaddress = shift;
    my $arobase = '@';
    my $escarobase = q{\@};
    my $escapedmailaddress = $mailaddress;
    $escapedmailaddress =~ s/$arobase/$escarobase/;
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

# execute  'printf "yourpassword" | sha256sum' on a terminal
# and copy the long string
my $PASSWD_HASH = q{password_hash_goes_here};
my $cgi_query_get = CGI->new;
my $PASSWD = $cgi_query_get->param('password');

if ( sha256_hex($PASSWD) eq $PASSWD_HASH and $ENV{'REQUEST_METHOD'} eq 'POST'){
   
    $ENV{'PATH'}='/usr/bin';
    my $HTML_CONTENT_TYPE_HEADER    = 'Content-type: text/html';
    my $HTML_CHARSET = '<meta http-equiv="content-type" content="text/html;
charset=utf-8">',"\n",'<meta charset="UTF-8">',"\n";
    my $HTML_CSS = '<link rel="stylesheet" type="text/css"
href="/gpigeon.css">';
    my $mymailaddr = q{your_mail_address_goes_here};
    my $mymailaddr_password = q{your_mail_address_password_goes_here};
    my $mymail_smtp = q{smtp_domain_goes_here};
    my $mymail_smtport = q{smtp_port_goes_here};
    my $mymail_gpgid = q{gpgid_goes_here}; #0xlong keyid form
    my $myescapedmailaddr = escape_arobase($mymailaddr);
    my @text_strings = ('La suppression a r&eacute;ussi !',
    'L&apos;adresse', 
    'est valide !', 
    'n&apos;est pas valide !',
    'sed "s/Inconnu', # displays on main page table when supposed sender isn't identified
    'La longueur du message doit être inférieure à 10000 charactères.',
    'Formulaire d&apos;envoi de messages GPG', # title for generated links
    'Rentrez votre message ci-dessous, ',
    'M&apos;envoyer le message',
    'Lien g&eacute;n&eacute;r&eacute; pour', #displays if link gen is successful
    'lien formulaire gpg', # mail subject when clicking a mailto: link in table
    'Ton lien est', # message when clicking a mailto: link in table
    'Supprimer', # text on button for deleting links
    'Mince! Je ne peux pas ouvrir', # message when file opening fails
    'GPIGEON.CGI: mails GPG pour le non-initié.', # main page title!
    'Salut et bienvenue.', # a greeting at the top of the main page.
    'Se d&eacute;connecter', # disconnect button text on main page
    'Actualiser la page', # refresh button text
    'G&eacute;n&eacute;rer lien', #link generation button text
    "Liens g&eacute;n&eacute;r&eacute;s pour <b>$mymailaddr</b>:", # label above links table
    'Supprimer tous les liens', # delete all links button text
    'Lien', # first table header, 'Link'
    'Pour', # second table header, 'For'
    'Suppression', # third table header, 'Delete'
    'La suppression a &eacute;chou&eacute;. Voici la cause: '
    );
    my $psswd_formfield = '<input type="hidden" name="password" value="' . $cgi_query_get->param('password') . '">',"\n";
    my $SRV_NAME		         = $ENV{'SERVER_NAME'};	
    my ($notif_de_creation, $notif_mail_valide, $notif_suppression) = undef;
    my @table_des_liens_crees = ();

    if (defined $cgi_query_get->param('supprlien')){
        my $pending_deletion = $cgi_query_get->param('supprlien');
        my $relpath_todelete = "./l/$pending_deletion";
        if (unlink untaint_cgi_filename($relpath_todelete)){ 
            $notif_suppression='<span style="color:green">'.$text_strings[0].'</span>';
        }
        else {
            $notif_suppression='<span style="color:red">'.$text_string[24].
            $relpath_todelete.':'.$!.'</span>';
        }
    }

    if (defined $cgi_query_get->param('supprtout')){
        opendir my $dir_handle, './l' or die "Can't open ./l: $!";

        while (readdir $dir_handle) {
            if ($_ ne '.' and $_ ne '..'){
                my $relpath_todelete = "./l/$_";
                unlink untaint_cgi_filename($relpath_todelete) or die "$!";
                $notif_suppression='<span style="color:green">'.
                $text_strings[0] .'</span>';
            }
        }
        closedir $dir_handle;
    }

    if (defined $cgi_query_get->param('mail')){
        my $entered_mail_addr = scalar $cgi_query_get->param('mail');
        if ( Email::Valid->address($entered_mail_addr) ){
            $notif_mail_valide = "<span style='color:green'>$text_strings[1] 
            $entered_mail_addr $text_strings[2]</span>";
            my $escaped_entered_mail_addr = escape_arobase($entered_mail_addr);
            my $random_mailform_fn_str = String::Random->new;
            my @mailform_fn_str_buffer = ();
            for (1..5){
                push @mailform_fn_str_buffer,
                     $random_mailform_fn_str->randregex('\w{1,15}[0-9]{1,15}');
            }
            my $mailform_fn_str_buffer_nospace = join('',@mailform_fn_str_buffer);
            my $GENERATED_FORM_FILENAME =
            "$mailform_fn_str_buffer_nospace.cgi";
            my $MAILFORM_LINK   	 = "http://$SRV_NAME/cgi-bin/l/$GENERATED_FORM_FILENAME";
            my $MAILFORM_RELPATH 	 =  "./l/$GENERATED_FORM_FILENAME";
            if (open my $mailform_fh, ">", $MAILFORM_RELPATH){ 
                print $mailform_fh '#! /usr/bin/perl -wT',"\n\n",
                ' my $demandeur_du_lien = q{', $entered_mail_addr
            , '};', "\n",
		        'delete @ENV{qw(IFS PATH CDPATH BASH_ENV)};', "\n",
                '$ENV{\'PATH\'}="/usr/bin";',
                'use warnings;', "\n",
                'use strict;',"\n",
                'use GPG;',"\n",
                'use Net::SMTP;',"\n",
                'use Net::SMTPS;',"\n",
                'use CGI::Carp qw(fatalsToBrowser);',
                'use CGI qw(param cookie);', "\n",
		        'my $cgi_query_get = CGI->new;', "\n",
                'my $smtp = Net::SMTPS->new(\''. $mymail_smtp  .'\', Port =>
                \''. $mymail_smtport .'\',
                doSSL => \'ssl\', Debug_SSL => 0);', "\n", 
                'my ($msg, $enc_msg, $error_processing_msg)             = undef;', "\n",
                'if (defined $cgi_query_get->param(\'msg\') and $ENV{\'REQUEST_METHOD\'} eq \'POST\'){',"\n",
                '   $msg = $cgi_query_get->param(\'msg\');', "\n", 
                '   $msg =~ tr/\r//d;', "\n",
		'   if (length $msg gt 10000){', "\n",
		'       $error_processing_msg = q{<span style="color:red"><b>La longueur du message doit être inférieure à 10000 charactères.</b></span>};', "\n",
		'   }', "\n",
                '   my $gpg =  new GPG(gnupg_path => "/usr/bin", homedir =>
                "/usr/share/www-data/.gnupg/");', "\n",
                '   $enc_msg = $gpg->encrypt("De la part de " .
                $demandeur_du_lien . ":\n". $msg, \'0x'. $mymail_gpgid  .'\') or die
                $gpg->error();', "\n",
                '   $smtp->auth(\''. $mymailaddr .'\', \''.
                $mymailaddr_password  .'\')
                or die;', "\n",
                '   $smtp->mail(\''. $mymailaddr .'\') or die "Net::SMTP module has broke:
                $!.";', "\n",
                    'if ($smtp->to(\''. $mymailaddr .'\')){', "\n",
                        '$smtp->data();', "\n",
                        '$smtp->datasend("To: '. $myescapedmailaddr .'\n");', "\n",
                        '$smtp->datasend("\n");', "\n",
                        '$smtp->datasend("$enc_msg\n");', "\n",
                        '$smtp->dataend();', "\n",
                        'unlink "../' . $MAILFORM_RELPATH . '";', "\n",
                        'print "Location: /gpigeon/merci/index.html\n\n";', "\n", 
                    '}', "\n",
                    'else {', "\n",
                        'die $smtp->message();', "\n",
                    '}', "\n",
                '}', "\n",
                'print "Content-type: text/html", "\n\n";', "\n",
                'print qq{<!DOCTYPE html>', "\n",
                '<html>', "\n",
                '    <head>', "\n",
                '        <link rel="icon" sizes="48x48" ',"\n",
                'type="image/ico" href="/gpigeon/favicon.ico">', "\n",
                $HTML_CSS, "\n",
                $HTML_CHARSET, "\n",
		'<title>Formulaire ', "\n",
                'd\'envoi de message GPG</title>',"\n",
                '    </head>', "\n",
                '    <body>', "\n",
                '        <p>'. $text_strings[7] . '<b>'
                .$escaped_entered_mail_addr .'</b> :</p>', "\n",
                '            <form method="POST">', "\n",
                '                <textarea "', "\n",
                'wrap="off" cols="50" rows="30" name="msg"
                required></textarea>', "\n",
		'<br>', "\n",
		'$error_processing_msg', "\n",
		'<br>', "\n",
                '<input type="submit"
                value="'. $text_strings[8] .'">', "\n",
                '            </form>', "\n",
                '    </body>', "\n",
                '</html>};';
            close $mailform_fh;
            chmod(0755,$MAILFORM_RELPATH);
            
            $notif_de_creation="<span style=\'color:green\'>$text_strings[9] $entered_mail_addr</span><br><a href=\'$MAILFORM_LINK\'>$MAILFORM_LINK</a>";
          }
          else{
		close $mailform_fh and die "cant open $MAILFORM_RELPATH: $!";

          }
        }
        else{
            $notif_mail_valide = "<span style='color:red'>$text_strings[1]
            $entered_mail_addr $text_strings[3].</span>";
        }
    }
    
    # ici on ouvre le dossier /var/www/cgi/cgi-bin/l qui contient les
    # formulaires de contacts afin de lister son contenu
    opendir my $dir_handle, './l' or die "Can't open ./l: $!";

    while (readdir $dir_handle) {
        if ($_ ne '.' and $_ ne '..'){
            my $fichier_formu_mail = $_;
            my $demandeur_du_lien = undef;
            if (open my $fh_formu_mail , '<', "./l/$fichier_formu_mail"){
                # le demandeur du lien est sur la 4ième ligne, d'où le 1..4
                for (1..4){
                    $demandeur_du_lien = readline $fh_formu_mail;
                    $demandeur_du_lien =~ s/q\{(.*?)\}//i;
                    $demandeur_du_lien = $1;
                }
                close $fh_formu_mail;
                
                if (not defined $demandeur_du_lien){
                    $demandeur_du_lien = $text_strings[4];
                }
                
                push @table_des_liens_crees, '<tr>',"\n",
                "\t<td><a href='/cgi-bin/l/$fichier_formu_mail'>ici</a></td>", "\n",
                "\t<td><a
                href='mailto:$demandeur_du_lien?subject=$text_strings[10]",
                "gpg&body=$text_strings[11] http://$SRV_NAME/cgi-bin/l/$fichier_formu_mail'>$demandeur_du_lien</a></td>", "\n",
                '<td>
                <form method="POST">
                    <input type="hidden" name="supprlien"
                    value="'.$fichier_formu_mail.'">
                    <input type="hidden" name="password"
                    value="'.$cgi_query_get->param('password').'">
                    <input type="submit" value="'. $text_strings[12] .'">
                </form>
                </td>', "\n",
                '</tr>';

            }
            else {
                close $fh_formu_mail;
                die "Content-type: text/plain", "\n\n", 
                "$text_strings[13] $fichier_formu_mail: $!";
            }
            

        }
    }
    closedir $dir_handle;

    print $HTML_CONTENT_TYPE_HEADER,"\n\n",
    '<!DOCTYPE html>', "\n",
        '<html>', "\n",
            '<head>', "\n",
                '<link rel="icon" sizes="48x48" ',"\n",
                'type="image/ico" href="/gpigeon/favicon.ico">', "\n",
                $HTML_CSS, "\n",
                $HTML_CHARSET, "\n",
                '<title>'. $text_strings[14] .'</title>', "\n",
            '</head>', "\n",
            '<body>', "\n",
                '<p>'. $text_strings[15] .'</p>', "\n",
                '<form method="POST">', "\n",
                    '<input type="hidden" name="password" value="0">', "\n",
                    '<input type="submit" value="'. $text_strings[16] .'">', "\n",
                '</form>', "\n",
                '<form method="POST">', "\n",
                $psswd_formfield,
                '   <input type="submit" value="'. $text_strings[17]  .'">', "\n",
                '</form>', "\n",
                '<hr>', "\n",
                '<br>', "\n",
                '<form method="POST">', "\n",
                    $psswd_formfield,
                    'Mail de la personne:<br>', "\n",
                    '<input tabindex="1" type="text" name="mail" maxlength="120">', "\n",
                    '<input tabindex="2" type="submit" value="'.
                    $text_strings[18] .'">', "\n",
                '</form>', "\n",
                notif_if_defined($notif_mail_valide), '<br>', "\n",
                notif_if_defined($notif_de_creation), 
                '<hr>', "\n",
                '<p>'. $text_strings[19]  .'</p>', "\n",
                '<form method="POST">', "\n",
                    $psswd_formfield,
                    '<input type="hidden" name="supprtout">', "\n",
                    '<input type="submit" value="'. $text_strings[20] .'">', "\n",
                '</form>', "\n",
                notif_if_defined($notif_suppression),
                '<table>', "\n",
                    '<tr>', "\n",
                        '<th>'. $text_strings[21]  .'</th>', "\n",
                        '<th>'. $text_strings[22]  .'</th>', "\n",
                        '<th>'. $text_strings[23]  .'</th>', "\n",
                    '</tr>', "\n",
                    "@table_des_liens_crees", "\n",
                '</table>', "\n",
            '</body>', "\n",
    '</html>';
}
else {
    print 'Location: /gpigeon/index.html', "\n\n";
}
