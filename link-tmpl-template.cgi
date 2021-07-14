#! /usr/bin/perl -wT
my $linkuser = q{link_user};
# link-tmpl.cgi : self-destructing message form to send yourself GPG
# encrypted messages. Part of gpigeon.

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
use CGI qw(param);

delete @ENV{qw(IFS PATH CDPATH BASH_ENV)};
$ENV{'PATH'}="/usr/bin";
$ENV{TMPDIR} = q{tmp_dir_goes_here};

my $HAS_MAILSERVER = q{has_mailserver_goes_here};
my $msg_form_char_limit = q{msg_char_limit_goes_here};
my $mymailaddr = q{your_addr_goes_here};
my $mymail_gpgid = q{gpgid_goes_here}; #0xlong keyid form
my $mailsender = q{sender_addr_goes_here};
my $mailsender_smtp = q{smtp_domain_goes_here};
my $mailsender_port = q{smtp_port_goes_here};
my $mailsender_pw = q{sender_pw_goes_here};
my $GPG_HOMEDIR = q{gpg_homedir_goes_here};
my $cgi_query_get = CGI->new;
my $msg_form = $cgi_query_get->param('msg');
my $length_msg_form = length $msg_form;
my ($smtp, $enc_msg, $error_processing_msg) = undef;

if (defined $length_msg_form and $length_msg_form > $msg_form_char_limit){
    $error_processing_msg = qq{<span id="failure"><b>Cannot send message : message length must be under $msg_form_char_limit characters.</b></span>};
} 
elsif (defined $length_msg_form and $length_msg_form eq 0 ){
    $error_processing_msg = qq{<span id="failure"><b>Cannot send message : message is empty. You can type up to $msg_form_char_limit characters.</b></span>};
}
else {
    if (defined $length_msg_form and $ENV{REQUEST_METHOD} eq 'POST'){
        use MIME::Entity;
        use Mail::GPG;
        $msg_form =~ tr/\r//d;
        my $gpgmail  = Mail::GPG->new(
            default_key_id => $mymailaddr,
            gnupg_hash_init => {homedir => $GPG_HOMEDIR},
            debug => 0,
            no_strict_7bit_encoding => 1,
        );
        my $mimentity = MIME::Entity->build(
            From => $mailsender,
            To => $mailaddr,
            Subject => '.',
            Data => ["This is a message from $linkuser:\n\n$msg_form"],
            Charset => 'utf-8',
        );
        
        $enc_msg = $gpg->encrypt("$linkuser:\n\n$msg_form", $mymail_gpgid) or die $gpg->error();

        if (my $fh = $cgi_query_get->upload('file')){
            my $fullfn = $cgi_query_get->param('file');
            $fullfn =~ s/^[a-zA-Z_0-9\-\.]/_/g;
            $fullfn =~ s/__+/_/g;
            my $fpath = $cgi_query_get->tmpFileName( $fh );
            my $fsize = -s $fpath;
            $CGI::POST_MAX = 1024*1024*100; # 100Mo limit
            if ($fsize > $CGI::POST_MAX){
                die 'ERROR: File is too big (>100MB).';
            }
#           my $mimetype = $cgi_query_get->uploadInfo( $fh )->{'Content-Type'};
#           my $lengthf = $cgi_query_get->uploadInfo( $fh )->{'Content-Length'};
            if (not $mimetype =~ /^([\w]+)\/([\w]+)$/){
                die 'Unrecognized MIME type of uploaded file.';
            }
            $mimentity->attach(
                Type => $mimetype,
                Description => 'OpenPGP encrypted attachment',
                Encoding => 'base64',
                Path => $fpath,
            );

        }

        my $mimentity_encrypted = $gpgmail->mime_encrypt(
            entity => $mimentity,
        );

        my $puremime = $mimentity_encrypted->as_string;

        use Net::SMTP;
        use Net::SMTPS;
        if ($HAS_MAILSERVER){
            $smtp = Net::SMTP->new( Host => 'localhost', Debug => 0);
        }
        else {
            $smtp = Net::SMTPS->new($mailsender_smtp, Port => $mailsender_port, doSSL => 'ssl', Debug_SSL => 0);
            $smtp->auth($mailsender, $mailsender_pw) or die;
        }
        $smtp->mail($mailsender) or die "Net::SMTP module has broke: $!.";
        if ($smtp->to($mymailaddr)){
            $smtp->data($puremime);
            $smtp->dataend();
            $smtp->quit();
        }
        else {
            die $smtp->message();
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
               <label for="filechoice" id="msgbelow">
                    (Optional) file upload: 
                    <input id="filechoice" type="file" name="file">
               </label>
               <input id="sendbtn" type="submit" value="{link_send_btn}">
            </form>
    </body>
</html> };
