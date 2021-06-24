#! /usr/bin/perl -wT
my $linkuser = q{link_user};
my $linkfilename = q{link_filename};
use warnings;
use strict;
use GPG;
use CGI qw(param);

$ENV{'PATH'}="/usr/bin";
delete @ENV{qw(IFS PATH CDPATH BASH_ENV)};

sub EscapeArobase {
    my $escapedmailaddress = shift;
    $escapedmailaddress =~ s/@/\\@/;
    return $escapedmailaddress;
}

my $HAS_MAILSERVER = q{has_mailserver_goes_here};
my $msg_form_char_limit = q{msg_char_limit_goes_here};
my $mymailaddr = q{user_mailaddr_goes_here};
my $mymail_gpgid = q{gpgid_goes_here}; #0xlong keyid form
my $mailsender = q{sender_addr_goes_here};
my $mailsender_smtp = q{smtp_domain_goes_here};
my $mailsender_port = q{smtp_port_goes_here};
my $mailsender_pw = q{sender_pw_goes_here};
my $GPG_HOMEDIR = q{gpg_homedir_goes_here};
my $cgi_query_get = CGI->new;
my $msg_form = $cgi_query_get->param('msg');
my $length_msg_form = length $msg_form;
my ($enc_msg, $error_processing_msg) = undef;

if (defined $length_msg_form and $length_msg_form > $msg_form_char_limit){
    $error_processing_msg = qq{<span id="failure"><b>Cannot send message : message length must be under $msg_form_char_limit characters.</b></span>};
} 
elsif (defined $length_msg_form and $length_msg_form eq 0 ){
    $error_processing_msg = qq{<span id="failure"><b>Cannot send message : message is empty. You can type up to $msg_form_char_limit characters.</b></span>};
}
else {
    if (defined $length_msg_form and $ENV{REQUEST_METHOD} eq 'POST'){
        $msg_form =~ tr/\r//d; # if we dont do this,  ^M character in plain text mail
        my $gpg =  new GPG(gnupg_path => "/usr/bin", homedir => $GPG_HOMEDIR);
        $enc_msg = $gpg->encrypt("$linkuser:\n\n$msg_form", $mymail_gpgid) or die $gpg->error();

        if ($HAS_MAILSERVER){
            use Mail::Sendmail;
            my %mail = ( To => "$mymailaddr",
            From => "$mailsender",
            Subject => '.',
            Message => "$enc_msg\n"
            );
            sendmail(%mail) or die $Mail::Sendmail::error;
        }
        else {
            use Net::SMTP;
            use Net::SMTPS;
            my $smtp = Net::SMTPS->new($mailsender_smtp, Port => $mailsender_port, doSSL => 'ssl', Debug_SSL => 0); 
            my $mymailaddr_escaped = EscapeArobase($mymailaddr);
            my $mailsender_escaped = EscapeArobase($mailsender);

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
        }

        unlink $linkfilename;
        print "Location: /merci/index.html\n\n"; 
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
       <title>{link_web_title}</title>
    </head>
    <body>
        <p id="msgbelow">{type_msg_below}:</p>
            <form method="POST">
                <textarea id="msg" wrap="off" cols="50" rows="30" name="msg"></textarea><br>
};
if (defined $error_processing_msg){
    printf $error_processing_msg;
}
printf q{
                <br>
               <input id="sendbtn" type="submit" value="{link_send_btn}">
            </form>
    </body>
</html> };
