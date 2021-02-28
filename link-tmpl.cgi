#! /usr/bin/perl -wT
my $linkuser = q{link_user};
my $linkfilename = q{link_filename};

use warnings;
use strict;
use GPG;
use CGI qw(param);

$ENV{'PATH'}="/usr/bin";
delete @ENV{qw(IFS PATH CDPATH BASH_ENV)};

sub escape_arobase {
    my $escapedmailaddress = shift;
    $escapedmailaddress =~ s/@/\\@/;
    return $escapedmailaddress;
}

my $HAS_MAILSERVER = 0;
my $mymailaddr = q{your mail address goes here};
my $mymail_gpgid = q{your gpg id in the 0xlong form goes here}; #0xlong keyid form
my $mailsender = q{mail address sending encrypted text goes here. recommended to be different from $mymailaddr};
my $mailsender_smtp = q{your SMTP mail domain name goes here};
my $mailsender_port = q{your SMTP port goes here};
my $mailsender_pw = q{password for $mailsender address goes here};
my $GPG_HOMEDIR = '/usr/share/webapps/gpigeon/gnupg/';
my $cgi_query_get = CGI->new;
my $msg_form = $cgi_query_get->param('msg');
my $length_msg_form = length $msg_form;
my ($enc_msg, $error_processing_msg) = undef;

if (defined $length_msg_form and $length_msg_form > {msg_form_char_limit}){
    $error_processing_msg = q{<span style="color:red"><b>{msg_too_long}</b></span>};
} 
elsif (defined $length_msg_form and $length_msg_form eq 0 ){
    $error_processing_msg = q{<span style="color:red"><b>{msg_empty}</b></span>};
}
else {
    if (defined $length_msg_form and $ENV{REQUEST_METHOD} eq 'POST'){
       $msg_form =~ tr/\r//d;
       my $gpg =  new GPG(gnupg_path => "/usr/bin", homedir => $GPG_HOMEDIR);
       $enc_msg = $gpg->encrypt("$linkuser:\n\n$msg_form", $mymail_gpgid) or die $gpg->error();

       if ($HAS_MAILSERVER){
           undef $mymailaddr_escaped;
           use Mail::Sendmail;
           my %mail = ( To => "$mymailaddr"
                     From => "$mailsender"
                     Subject => '.'
                     Message => "$enc_msg\n" 
           );
           sendmail(%mail) or die $Mail::Sendmail::error;
       }
       else {
           use Net::SMTP;
           use Net::SMTPS;
           my $smtp = Net::SMTPS->new($mailsender_smtp, Port => $mailsender_port, doSSL => 'ssl', Debug_SSL => 0); 
           my $mymailaddr_escaped = escape_arobase{$mymailaddr};
           my $mailsender_escaped = escape_arobase($mailsender);

           $smtp->auth($mailsender, $mailsender_pw) or die;
           $smtp->mail($mailsender) or die "Net::SMTP module has broke: $!.";
           if ($smtp->to($mymailaddr)){
              $smtp->data();
              $smtp->datasend("From: $mailsender_escaped\n");
              $smtp->datasend("To: $mymailaddr_escaped\n");
              $smtp->datasend("Subject: .\n");
              $smtp->datasend("\n");
              $smtp->datasend("$enc_msg\n");
              $smtp->dataend();
           }
           else {
              die $smtp->message();
           }

           unlink "../l/$linkfilename";
           print "Location: /merci/index.html\n\n"; 
       }
   }
}
print "Content-type: text/html", "\n\n";
print qq{<!DOCTYPE html>
<html>
    <head>
       <link rel="icon" sizes="48x48" type="image/ico" href="/favicon.ico">
       <link rel="stylesheet" type="text/css" href="/styles.css">
       <meta http-equiv="Content-Type" content="text/html;charset=UTF-8">
       <meta charset="UTF-8">
       <title>Formulaire d'envoi de message GPG</title>
    </head>
    <body>
        <p>type_msg_below:</p>
            <form method="POST">
                <textarea wrap="off" cols="50" rows="30" name="msg"></textarea><br>
};
if (defined $error_processing_msg){
    printf $error_processing_msg;
}
printf q{
                <br>
               <input type="submit" value="{link_send_btn}">
            </form>
    </body>
</html> };
